import { useCallback, useEffect, useState } from "react";
import type { QuarantineUnit } from "../types";
import { approveUnit, listQuarantine, rejectUnit } from "../api";

export function QuarantinePage() {
  const [units, setUnits] = useState<QuarantineUnit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setUnits(await listQuarantine());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load quarantine");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function act(id: string, op: "approve" | "reject") {
    setBusy(id);
    try {
      const fn = op === "approve" ? approveUnit : rejectUnit;
      const res = await fn(id);
      if (res.ok) setUnits((u) => u.filter((x) => x.id !== id));
      else setError(`${op} failed`);
    } catch (e) {
      setError(e instanceof Error ? e.message : `${op} failed`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <h1 className="page-title">Quarantine</h1>
      <p className="page-desc">Failed validation — approve to promote or reject to discard. Agents never see these.</p>

      {error && <div className="alert alert-error">{error}</div>}
      {units.length === 0 && !error && <p className="empty">Queue empty.</p>}

      {units.map((u) => (
        <div className="card" key={u.id}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
            <span className="badge badge-warn">{u.type}</span>
            <span className="score">{(u.confidence * 100).toFixed(0)}%</span>
          </div>
          <p className="unit-claim">{u.claim}</p>
          <p className="unit-meta">{u.domains?.join(", ")} · {u.applicability}</p>
          {u.validation_failures && u.validation_failures.length > 0 && (
            <ul style={{ fontSize: "0.8rem", color: "#faa", margin: "0.5rem 0 0.5rem 1.2rem" }}>
              {u.validation_failures.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}
          <p className="unit-source">{u.source_url}{u.source_span ? ` — "${u.source_span.slice(0, 100)}"` : ""}</p>
          <div className="actions">
            <button className="btn btn-primary btn-sm" disabled={busy === u.id} onClick={() => act(u.id, "approve")}>Approve</button>
            <button className="btn btn-danger btn-sm" disabled={busy === u.id} onClick={() => act(u.id, "reject")}>Reject</button>
          </div>
        </div>
      ))}
    </>
  );
}
