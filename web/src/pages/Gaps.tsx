import { useEffect, useState } from "react";
import type { Contradiction, Gap } from "../types";
import { listContradictions, listGaps } from "../api";

export function GapsPage() {
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [contradictions, setContradictions] = useState<Contradiction[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setGaps(await listGaps());
        setContradictions(await listContradictions());
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      }
    })();
  }, []);

  return (
    <>
      <h1 className="page-title">Gaps &amp; Contradictions</h1>
      <p className="page-desc">Concepts referenced but under-learned, and conflicting validated claims.</p>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <h3>Learning gaps</h3>
        {gaps.length === 0 ? <p className="empty">No gaps detected.</p> : (
          <ul style={{ listStyle: "none" }}>
            {gaps.map((g) => (
              <li key={g.concept} style={{ padding: "0.5rem 0", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between" }}>
                <span>{g.concept}</span>
                <span className="badge">{g.reference_count} refs</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h3>Contradictions</h3>
        {contradictions.length === 0 ? <p className="empty">None flagged.</p> : contradictions.map((c) => (
          <div key={`${c.a_id}-${c.b_id}`} style={{ padding: "0.75rem 0", borderBottom: "1px solid var(--border)" }}>
            <p className="unit-claim" style={{ fontSize: "0.85rem" }}>{c.a_claim}</p>
            <p style={{ textAlign: "center", color: "var(--red)", fontSize: "0.75rem", margin: "0.25rem 0" }}>contradicts</p>
            <p className="unit-claim" style={{ fontSize: "0.85rem" }}>{c.b_claim}</p>
          </div>
        ))}
      </div>
    </>
  );
}
