import { FormEvent, useState } from "react";
import type { QueryResult } from "../types";
import { queryKnowledge } from "../api";

export function QueryPage() {
  const [task, setTask] = useState("");
  const [results, setResults] = useState<QueryResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setResults(await queryKnowledge(task.trim(), 12));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h1 className="page-title">Query</h1>
      <p className="page-desc">Hybrid vector + graph retrieval over validated knowledge units.</p>

      <form className="card" onSubmit={onSubmit}>
        <label htmlFor="task">Task context</label>
        <textarea id="task" required placeholder="e.g. designing API rate limits for high concurrency" value={task} onChange={(e) => setTask(e.target.value)} />
        <div className="actions" style={{ marginTop: "1rem" }}>
          <button type="submit" className="btn btn-primary" disabled={loading || !task.trim()}>
            {loading ? "Searching…" : "Query"}
          </button>
        </div>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {results.length === 0 && !loading && !error && <p className="empty">No results yet.</p>}

      {results.map((r) => (
        <div className="card" key={r.unit_id}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", marginBottom: "0.5rem" }}>
            <span className="badge">{r.type}</span>
            <span className="score">{(r.relevance_score * 100).toFixed(0)}% · conf {(r.confidence * 100).toFixed(0)}%</span>
          </div>
          <p className="unit-claim">{r.claim}</p>
          <p className="unit-meta">{r.applicability}</p>
          <p className="unit-source">
            {r.source.url}
            {r.source.timestamp_or_section != null && ` · ${r.source.timestamp_or_section}`}
          </p>
        </div>
      ))}
    </>
  );
}
