import { FormEvent, useState } from "react";
import { getApiBase, setApiBase } from "../api";

export function SettingsPage() {
  const [apiUrl, setApiUrl] = useState(getApiBase() || "http://localhost:8400");
  const [saved, setSaved] = useState(false);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setApiBase(apiUrl.trim());
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <>
      <h1 className="page-title">Settings</h1>
      <p className="page-desc">The web UI talks to your V.A.U.L.T API. GitHub Pages hosts this frontend only — run the backend locally or on your server.</p>

      <form className="card" onSubmit={onSubmit}>
        <label htmlFor="api">API base URL</label>
        <input id="api" type="url" required value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} placeholder="http://localhost:8400" />
        <div className="actions" style={{ marginTop: "1rem" }}>
          <button type="submit" className="btn btn-primary">Save</button>
          {saved && <span className="badge badge-ok">Saved</span>}
        </div>
      </form>

      <div className="card">
        <h3>Deploy stack</h3>
        <pre style={{ fontFamily: "var(--mono)", fontSize: "0.75rem", color: "var(--muted)", whiteSpace: "pre-wrap" }}>
{`docker compose up -d
pip install -e ".[full]"
vault-api          # :8400
vault-worker       # Temporal
vault serve-mcp    # Cursor`}
        </pre>
      </div>
    </>
  );
}
