import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { checkHealth, listGaps, listQuarantine } from "../api";

export function Dashboard() {
  const [health, setHealth] = useState<string>("checking");
  const [quarantineCount, setQuarantineCount] = useState<number | null>(null);
  const [gapCount, setGapCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const h = await checkHealth();
        setHealth(h.neo4j ? `${h.status} · ${h.neo4j}` : h.status);
        const q = await listQuarantine();
        setQuarantineCount(q.length);
        const g = await listGaps();
        setGapCount(g.length);
        setError(null);
      } catch (e) {
        setHealth("offline");
        setError(e instanceof Error ? e.message : "API unreachable — set endpoint in Settings");
      }
    })();
  }, []);

  return (
    <>
      <h1 className="page-title">Overview</h1>
      <p className="page-desc">Personal knowledge distillation pipeline — ingest, validate, graph, deliver to agents.</p>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="grid-2">
        <div className="card">
          <h3>API Status</h3>
          <span className={`badge ${health === "ok" || health.startsWith("ok") ? "badge-ok" : "badge-err"}`}>{health}</span>
        </div>
        <div className="card">
          <h3>Quarantine</h3>
          <p style={{ fontSize: "1.75rem", fontWeight: 600 }}>{quarantineCount ?? "—"}</p>
          <Link to="/quarantine">Review queue →</Link>
        </div>
        <div className="card">
          <h3>Learning gaps</h3>
          <p style={{ fontSize: "1.75rem", fontWeight: 600 }}>{gapCount ?? "—"}</p>
          <Link to="/gaps">View gaps →</Link>
        </div>
        <div className="card">
          <h3>Quick start</h3>
          <ol style={{ paddingLeft: "1.2rem", color: "var(--muted)", fontSize: "0.85rem" }}>
            <li>Configure API URL in Settings</li>
            <li>Run backend: <code style={{ fontFamily: "var(--mono)" }}>vault-api</code></li>
            <li>Ingest a URL, query from Cursor via MCP</li>
          </ol>
        </div>
      </div>
    </>
  );
}
