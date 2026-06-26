import { FormEvent, useState } from "react";
import { ingestUrl } from "../api";

export function IngestPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await ingestUrl(url.trim(), true);
      setResult(JSON.stringify(res, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h1 className="page-title">Ingest</h1>
      <p className="page-desc">YouTube, articles, Instagram reels, PDFs — normalized, extracted, validated, graphed.</p>

      <form className="card" onSubmit={onSubmit}>
        <label htmlFor="url">Source URL</label>
        <input id="url" type="url" required placeholder="https://..." value={url} onChange={(e) => setUrl(e.target.value)} />
        <div className="actions" style={{ marginTop: "1rem" }}>
          <button type="submit" className="btn btn-primary" disabled={loading || !url.trim()}>
            {loading ? "Processing…" : "Ingest"}
          </button>
        </div>
      </form>

      {error && <div className="alert alert-error">{error}</div>}
      {result && (
        <div className="card">
          <h3>Result</h3>
          <pre style={{ fontFamily: "var(--mono)", fontSize: "0.75rem", overflow: "auto", whiteSpace: "pre-wrap" }}>{result}</pre>
        </div>
      )}
    </>
  );
}
