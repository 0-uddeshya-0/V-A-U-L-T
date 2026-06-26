import { useEffect, useRef, useState } from "react";
import "./landing.css";

const STEPS = [
  "Ingest URL or file",
  "Extract knowledge units",
  "Validate (3 checks)",
  "Graph integration",
  "Deliver via MCP / REST",
];

const REPO = "https://github.com/0-uddeshya-0/V-A-U-L-T";

export function LandingPage() {
  const [activeStep, setActiveStep] = useState(0);
  const orbRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((s) => (s + 1) % STEPS.length);
    }, 2400);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!orbRef.current) return;
      orbRef.current.style.transform = `translate(${e.clientX * 0.04}px, ${e.clientY * 0.04}px)`;
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  useEffect(() => {
    const els = document.querySelectorAll(".landing-reveal");
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("visible");
        });
      },
      { threshold: 0.15 },
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  return (
    <div className="landing">
      <div className="landing-noise" aria-hidden />
      <div className="landing-orb" ref={orbRef} aria-hidden style={{ top: "10%", left: "55%" }} />

      <nav className="landing-nav">
        <span className="landing-nav-brand">V.A.U.L.T</span>
        <div className="landing-nav-links">
          <a href="#pipeline">Pipeline</a>
          <a href="#agents">Agents</a>
          <a href={REPO} target="_blank" rel="noreferrer">
            GitHub
          </a>
          <a className="landing-btn landing-btn-primary" href={REPO}>
            Get the code
          </a>
        </div>
      </nav>

      <header className="landing-hero">
        <div className="landing-reveal">
          <h1>
            Learn once. <em>Apply forever</em> in every agent.
          </h1>
          <p className="landing-hero-lead">
            V.A.U.L.T ingests what you watch and read, distills validated knowledge units, stores them in a
            living graph, and delivers them to Cursor, Claude, or any MCP client.
          </p>
          <div className="landing-hero-actions">
            <a className="landing-btn landing-btn-primary" href={REPO}>
              Clone repository
            </a>
            <a className="landing-btn landing-btn-ghost" href={`${REPO}#quick-start`}>
              Run locally
            </a>
          </div>
        </div>

        <div className="landing-glass-panel landing-reveal" style={{ transitionDelay: "80ms" }}>
          <p style={{ fontFamily: "var(--mono)", fontSize: "0.7rem", color: "#5c6378", marginBottom: "1rem" }}>
            LIVE PIPELINE
          </p>
          <div className="landing-pipeline">
            {STEPS.map((label, i) => (
              <div key={label} className={`landing-pipeline-step${i === activeStep ? " active" : ""}`}>
                <span className="landing-pipeline-num">{String(i + 1).padStart(2, "0")}</span>
                {label}
              </div>
            ))}
          </div>
        </div>
      </header>

      <section className="landing-section landing-reveal" id="pipeline">
        <h2>Five layers, one pipeline</h2>
        <p className="landing-section-desc">
          Not RAG chunks. Not conversation memory. Structured claims with source attribution, validation gates,
          and graph relationships agents can traverse.
        </p>
        <div className="landing-bento">
          <div className="landing-glass-panel wide">
            <h3>Precision over recall</h3>
            <p>
              Every unit passes source grounding, consistency checks, and comprehension verification. Failed
              extractions go to quarantine, not your agents.
            </p>
          </div>
          <div className="landing-glass-panel">
            <h3>Ingestion</h3>
            <p>YouTube, articles, reels, papers. One normalized format regardless of source.</p>
          </div>
          <div className="landing-glass-panel">
            <h3>Living graph</h3>
            <p>Contradictions flagged. Gaps surfaced. Dependencies linked explicitly.</p>
          </div>
        </div>
      </section>

      <section className="landing-section landing-reveal" id="agents">
        <h2>Built for agents first</h2>
        <p className="landing-section-desc">
          MCP server and REST API return structured knowledge units, not walls of text. Run the stack on your
          machine; the console is local-only.
        </p>
        <div className="landing-glass-panel">
          <pre className="landing-code">
            <span className="kw">query_knowledge</span>({"{"}
            {"\n"}  <span className="str">"task"</span>: <span className="str">"designing API rate limits"</span>
            {"\n}"})
            {"\n\n"}→ claim, type, applicability, confidence, source, related units
          </pre>
        </div>
      </section>

      <section className="landing-section landing-reveal">
        <h2>Run it yourself</h2>
        <p className="landing-section-desc">
          GitHub Pages hosts this landing page. The Knowledge OS runs on your hardware with Neo4j, Temporal, and
          your LLM key.
        </p>
        <div className="landing-glass-panel">
          <pre className="landing-code">
            docker compose up -d{"\n"}pip install -e &quot;.[full]&quot;{"\n"}vault-api{"\n"}cd web && npm run dev
            {"\n\n"}Open <span className="str">http://localhost:5173/app</span>
          </pre>
        </div>
      </section>

      <footer className="landing-footer">
        V.A.U.L.T · Versatile Archive of Unified Learning &amp; Thought · MIT · Uddeshya Singh
      </footer>
    </div>
  );
}
