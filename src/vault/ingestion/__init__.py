"""Ingestion layer — normalize all source types to NormalizedDocument."""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from vault.models import DocumentMetadata, DocumentSegment, NormalizedDocument, SourceType


def detect_source_type(url: str) -> SourceType:
    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return SourceType.YOUTUBE
    if "instagram.com" in host:
        return SourceType.INSTAGRAM
    if url.lower().endswith(".pdf"):
        return SourceType.PAPER
    return SourceType.ARTICLE


class IngestionAdapter(ABC):
    @abstractmethod
    async def ingest(self, url: str) -> NormalizedDocument:
        ...


class YouTubeAdapter(IngestionAdapter):
    """Extract timestamped transcript via youtube-transcript-api / yt-dlp fallback."""

    async def ingest(self, url: str) -> NormalizedDocument:
        video_id = _extract_youtube_id(url)
        segments = _fetch_youtube_transcript(video_id)
        full_text = " ".join(s.text for s in segments)

        return NormalizedDocument(
            source_type=SourceType.YOUTUBE,
            source_url=url,
            segments=segments,
            metadata=DocumentMetadata(title=video_id, density_score=_estimate_density(segments)),
            raw_hash=_hash(full_text),
        )


def _fetch_youtube_transcript(video_id: str) -> list[DocumentSegment]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript = YouTubeTranscriptApi().fetch(video_id)
        segments: list[DocumentSegment] = []
        offset = 0
        for i, entry in enumerate(transcript):
            text = entry.text.strip()
            if not text:
                continue
            segments.append(
                DocumentSegment(
                    index=i,
                    text=text,
                    start_offset=offset,
                    end_offset=offset + len(text),
                    timestamp_start=entry.start,
                    timestamp_end=entry.start + entry.duration,
                )
            )
            offset += len(text) + 1
        if segments:
            return segments
    except Exception:
        pass

    # Fallback: yt-dlp subtitle extraction
    import json
    import tempfile

    import yt_dlp

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "quiet": True,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts["outtmpl"] = f"{tmpdir}/%(id)s"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            subtitles = info.get("subtitles") or info.get("automatic_captions") or {}
            en_subs = subtitles.get("en") or subtitles.get("en-US") or []
            if not en_subs:
                raise ValueError(f"No subtitles available for YouTube video: {video_id}")
            sub_url = en_subs[0]["url"]
            import urllib.request

            raw = urllib.request.urlopen(sub_url).read().decode()
            # VTT or json3 — try json lines first
            segments = []
            if raw.strip().startswith("{"):
                data = json.loads(raw)
                events = data.get("events", [])
                offset = 0
                for i, ev in enumerate(events):
                    segs = ev.get("segs") or []
                    text = "".join(s.get("utf8", "") for s in segs).strip()
                    if not text:
                        continue
                    start = ev.get("tStartMs", 0) / 1000
                    dur = ev.get("dDurationMs", 0) / 1000
                    segments.append(
                        DocumentSegment(
                            index=i,
                            text=text,
                            start_offset=offset,
                            end_offset=offset + len(text),
                            timestamp_start=start,
                            timestamp_end=start + dur,
                        )
                    )
                    offset += len(text) + 1
            else:
                raise ValueError(f"Unsupported subtitle format for video: {video_id}")
            return segments


class ArticleAdapter(IngestionAdapter):
    """Extract clean article text via trafilatura."""

    async def ingest(self, url: str) -> NormalizedDocument:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ValueError(f"Failed to fetch URL: {url}")

        text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        if not text:
            raise ValueError(f"No extractable content at: {url}")

        meta = trafilatura.extract_metadata(downloaded)
        segments = _split_by_headings(text)

        return NormalizedDocument(
            source_type=SourceType.ARTICLE,
            source_url=url,
            segments=segments,
            metadata=DocumentMetadata(
                author=meta.author if meta else None,
                title=meta.title if meta else None,
                density_score=_estimate_density(segments),
            ),
            raw_hash=_hash(text),
        )


class InstagramAdapter(IngestionAdapter):
    """Download reel + transcribe via yt-dlp + Whisper (optional dependency)."""

    async def ingest(self, url: str) -> NormalizedDocument:
        try:
            import whisper
            import yt_dlp
        except ImportError as e:
            raise ImportError(
                "Instagram ingestion requires: pip install vault[transcribe]"
            ) from e

        from vault.config import settings

        ydl_opts: dict = {"format": "bestaudio/best", "outtmpl": "/tmp/vault_%(id)s.%(ext)s"}
        if settings.instagram_cookies_from_browser:
            ydl_opts["cookiesfrombrowser"] = (settings.instagram_cookies_from_browser,)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = ydl.prepare_filename(info)

        model = whisper.load_model("base")
        result = model.transcribe(audio_path)

        segments: list[DocumentSegment] = []
        offset = 0
        for i, seg in enumerate(result.get("segments", [])):
            text = seg["text"].strip()
            segments.append(
                DocumentSegment(
                    index=i,
                    text=text,
                    start_offset=offset,
                    end_offset=offset + len(text),
                    timestamp_start=seg.get("start"),
                    timestamp_end=seg.get("end"),
                )
            )
            offset += len(text) + 1

        full_text = result.get("text", "")
        return NormalizedDocument(
            source_type=SourceType.INSTAGRAM,
            source_url=url,
            segments=segments,
            metadata=DocumentMetadata(density_score=_estimate_density(segments)),
            raw_hash=_hash(full_text),
        )


class PaperAdapter(IngestionAdapter):
    """PDF/paper ingestion via markitdown (optional dependency)."""

    async def ingest(self, url: str) -> NormalizedDocument:
        try:
            from markitdown import MarkItDown
        except ImportError as e:
            raise ImportError("Paper ingestion requires: pip install vault[papers]") from e

        md = MarkItDown()
        result = md.convert(url)
        text = result.text_content
        segments = _split_paper_sections(text)

        return NormalizedDocument(
            source_type=SourceType.PAPER,
            source_url=url,
            segments=segments,
            metadata=DocumentMetadata(density_score=_estimate_density(segments)),
            raw_hash=_hash(text),
        )


ADAPTERS: dict[SourceType, type[IngestionAdapter]] = {
    SourceType.YOUTUBE: YouTubeAdapter,
    SourceType.ARTICLE: ArticleAdapter,
    SourceType.INSTAGRAM: InstagramAdapter,
    SourceType.PAPER: PaperAdapter,
}


async def ingest_url(url: str, source_type: SourceType | None = None) -> NormalizedDocument:
    st = source_type or detect_source_type(url)
    adapter = ADAPTERS[st]()
    return await adapter.ingest(url)


def _extract_youtube_id(url: str) -> str:
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract YouTube video ID from: {url}")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _estimate_density(segments: list[DocumentSegment]) -> float:
    if not segments:
        return 0.0
    total_words = sum(len(s.text.split()) for s in segments)
    return min(1.0, total_words / max(len(segments), 1) / 50)


def _split_by_headings(text: str) -> list[DocumentSegment]:
    parts = re.split(r"\n(?=#{1,3}\s)", text)
    segments: list[DocumentSegment] = []
    offset = 0
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        heading = None
        if part.startswith("#"):
            lines = part.split("\n", 1)
            heading = lines[0].lstrip("#").strip()
            body = lines[1] if len(lines) > 1 else ""
        else:
            body = part
        segments.append(
            DocumentSegment(
                index=i,
                text=body or part,
                start_offset=offset,
                end_offset=offset + len(body or part),
                heading=heading,
            )
        )
        offset += len(part) + 1
    return segments or [
        DocumentSegment(index=0, text=text, start_offset=0, end_offset=len(text))
    ]


_PAPER_SECTIONS = {
    "abstract": r"(?i)^#?\s*abstract",
    "introduction": r"(?i)^#?\s*introduction",
    "methods": r"(?i)^#?\s*(methods|methodology|approach)",
    "results": r"(?i)^#?\s*results",
    "conclusion": r"(?i)^#?\s*(conclusion|discussion)",
}


def _split_paper_sections(text: str) -> list[DocumentSegment]:
    lines = text.split("\n")
    segments: list[DocumentSegment] = []
    current_section = "body"
    buffer: list[str] = []
    offset = 0

    def flush(section: str, buf: list[str], idx: int) -> None:
        nonlocal offset
        body = "\n".join(buf).strip()
        if body:
            segments.append(
                DocumentSegment(
                    index=idx,
                    text=body,
                    start_offset=offset,
                    end_offset=offset + len(body),
                    section_type=section,
                )
            )
            offset += len(body) + 1

    for line in lines:
        matched = False
        for section, pattern in _PAPER_SECTIONS.items():
            if re.match(pattern, line.strip()):
                flush(current_section, buffer, len(segments))
                buffer = []
                current_section = section
                matched = True
                break
        if not matched:
            buffer.append(line)

    flush(current_section, buffer, len(segments))
    return segments or [
        DocumentSegment(index=0, text=text, start_offset=0, end_offset=len(text))
    ]
