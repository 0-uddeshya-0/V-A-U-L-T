"""Quarantine review UI — approve/reject flagged knowledge units."""

QUARANTINE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>V.A.U.L.T — Quarantine Review</title>
  <style>
    :root { --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #e6edf3;
            --muted: #8b949e; --green: #3fb950; --red: #f85149; --accent: #58a6ff; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: var(--bg); color: var(--text); padding: 2rem; max-width: 960px; margin: 0 auto; }
    h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
    .subtitle { color: var(--muted); margin-bottom: 2rem; font-size: 0.9rem; }
    .stats { display: flex; gap: 1rem; margin-bottom: 2rem; }
    .stat { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
            padding: 1rem 1.5rem; flex: 1; text-align: center; }
    .stat .num { font-size: 2rem; font-weight: 700; color: var(--accent); }
    .stat .label { color: var(--muted); font-size: 0.8rem; margin-top: 0.25rem; }
    .unit { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
            padding: 1.25rem; margin-bottom: 1rem; }
    .unit-header { display: flex; justify-content: space-between; align-items: start; gap: 1rem; }
    .claim { font-size: 1rem; line-height: 1.5; flex: 1; }
    .badge { font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 4px;
             background: #1f2937; color: var(--muted); white-space: nowrap; }
    .meta { color: var(--muted); font-size: 0.8rem; margin: 0.75rem 0; }
    .failures { background: #1c1210; border: 1px solid #5c2018; border-radius: 6px;
                padding: 0.75rem; margin: 0.75rem 0; font-size: 0.85rem; color: #ffa198; }
    .failures li { margin-left: 1.25rem; margin-top: 0.25rem; }
    .source { font-size: 0.8rem; color: var(--muted); word-break: break-all; }
    .actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
    button { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid var(--border);
             cursor: pointer; font-size: 0.85rem; font-weight: 600; transition: opacity 0.15s; }
    button:hover { opacity: 0.85; }
    .approve { background: #0d3117; color: var(--green); border-color: #238636; }
    .reject { background: #2d1214; color: var(--red); border-color: #8b1a1a; }
    .empty { text-align: center; color: var(--muted); padding: 3rem; }
    .toast { position: fixed; bottom: 2rem; right: 2rem; background: var(--card);
             border: 1px solid var(--border); padding: 0.75rem 1.25rem; border-radius: 8px;
             display: none; }
  </style>
</head>
<body>
  <h1>Quarantine Review</h1>
  <p class="subtitle">Units that failed validation — approve to promote or reject to discard.</p>
  <div class="stats">
    <div class="stat"><div class="num" id="count">—</div><div class="label">Pending Review</div></div>
  </div>
  <div id="units"></div>
  <div class="toast" id="toast"></div>
  <script>
    async function load() {
      const res = await fetch('/api/quarantine');
      const units = await res.json();
      document.getElementById('count').textContent = units.length;
      const container = document.getElementById('units');
      if (!units.length) {
        container.innerHTML = '<div class="empty">No units in quarantine — all clear.</div>';
        return;
      }
      container.innerHTML = units.map(u => `
        <div class="unit" id="unit-${u.id}">
          <div class="unit-header">
            <div class="claim">${esc(u.claim)}</div>
            <span class="badge">${esc(u.type)} · ${(u.confidence * 100).toFixed(0)}%</span>
          </div>
          <div class="meta">${esc(u.domains?.join(', ') || '')} · ${esc(u.applicability || '')}</div>
          ${u.validation_failures?.length ? `<ul class="failures">${u.validation_failures.map(f => `<li>${esc(f)}</li>`).join('')}</ul>` : ''}
          <div class="source">${esc(u.source_url || '')}${u.source_span ? ' — "' + esc(u.source_span.slice(0,120)) + '"' : ''}</div>
          <div class="actions">
            <button class="approve" onclick="action('${u.id}', 'approve')">Approve</button>
            <button class="reject" onclick="action('${u.id}', 'reject')">Reject</button>
          </div>
        </div>
      `).join('');
    }
    async function action(id, op) {
      const res = await fetch(`/api/quarantine/${id}/${op}`, { method: 'POST' });
      const data = await res.json();
      if (data.ok) {
        document.getElementById('unit-' + id)?.remove();
        toast(op === 'approve' ? 'Unit promoted to validated' : 'Unit rejected and removed');
        const remaining = document.querySelectorAll('.unit').length;
        document.getElementById('count').textContent = remaining;
        if (!remaining) document.getElementById('units').innerHTML =
          '<div class="empty">No units in quarantine — all clear.</div>';
      } else {
        toast('Action failed: ' + (data.error || 'unknown error'));
      }
    }
    function toast(msg) {
      const el = document.getElementById('toast');
      el.textContent = msg; el.style.display = 'block';
      setTimeout(() => el.style.display = 'none', 3000);
    }
    function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    load();
  </script>
</body>
</html>"""


def register_quarantine_routes(app, graph_factory):
    """Register quarantine review routes on a FastAPI app."""

    @app.get("/quarantine")
    async def quarantine_page():
        from fastapi.responses import HTMLResponse

        return HTMLResponse(QUARANTINE_HTML)

    @app.get("/api/quarantine")
    async def list_quarantine():
        graph = graph_factory()
        try:
            return graph.list_quarantine()
        finally:
            graph.close()

    @app.post("/api/quarantine/{unit_id}/approve")
    async def approve(unit_id: str):
        graph = graph_factory()
        try:
            ok = graph.approve_unit(unit_id)
            return {"ok": ok, "error": None if ok else "Unit not found or not in quarantine"}
        finally:
            graph.close()

    @app.post("/api/quarantine/{unit_id}/reject")
    async def reject(unit_id: str):
        graph = graph_factory()
        try:
            ok = graph.reject_unit(unit_id)
            return {"ok": ok, "error": None if ok else "Unit not found or not in quarantine"}
        finally:
            graph.close()

    @app.get("/api/contradictions")
    async def contradictions(concept: str | None = None):
        graph = graph_factory()
        try:
            return graph.list_contradictions(concept)
        finally:
            graph.close()
