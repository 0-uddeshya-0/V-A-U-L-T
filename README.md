# V.A.U.L.T

**Versatile Archive of Unified Learning & Thought** — ingest learning content, extract validated knowledge units, store them in a living graph, deliver to AI agents.

| Layer | Stack |
|-------|-------|
| Pipeline | Python · Instructor · Temporal · Neo4j |
| API | FastAPI · MCP |
| Web UI | React · Vite (GitHub Pages) |

**Live UI:** https://0-uddeshya-0.github.io/V-A-U-L-T/

## Architecture

```
URL → ingest → extract → validate → graph → MCP / REST / Web UI
```

Five components: **Ingestion** · **Extraction** · **Validation** · **Graph** · **Delivery**

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/TOOLSTACK.md](docs/TOOLSTACK.md).

## Quick start

```bash
docker compose up -d
cp .env.example .env   # OPENAI_API_KEY required
pip install -e ".[full]"

vault-api              # API :8400
vault-worker           # Temporal worker
cd web && npm install && npm run dev   # UI :5173
```

## Web UI

GitHub Pages hosts the **frontend only**. Point Settings → API URL at your running backend (`http://localhost:8400` locally).

Pages: Overview · Ingest · Query · Quarantine · Gaps · Settings

## CLI

```bash
vault ingest "https://youtube.com/watch?v=..." --wait
vault query "API rate limiting tradeoffs"
vault serve-mcp        # Cursor MCP
```

### Cursor MCP (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "vault": {
      "command": "vault-mcp",
      "env": { "OPENAI_API_KEY": "...", "VAULT_NEO4J_PASSWORD": "vault-dev-password" }
    }
  }
}
```

## Docker

```bash
docker build -t vault-api .
docker run -p 8400:8400 --env-file .env vault-api
```

## CI / Deploy

- **CI:** `.github/workflows/ci.yml` — ruff, pytest, web build
- **Pages:** `.github/workflows/deploy-pages.yml` — deploys `web/` on push to `main`

Enable Pages: repo **Settings → Pages → Source: GitHub Actions**.

## License

MIT © Uddeshya Singh
