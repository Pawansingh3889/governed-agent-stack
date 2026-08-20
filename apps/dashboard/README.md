# Governed Agent Stack Dashboard

The merged Next.js console for the Governed Agent Stack: FloorMind's factory
querying and Elenchus's governed surveys in one UI, alongside the management
surfaces. Every backend is proxied server-side, so the browser never handles
CORS or auth headers.

## Pages

| Page | What it shows |
|------|---------------|
| `/` | Overview with component health and status cards |
| `/flow` | The end-to-end pipeline: question to query to audited result |
| `/chat` | FloorMind natural-language queries (SSE streaming) |
| `/factory` | Production KPIs and alerts |
| `/compliance` | Compliance scores, batch traceability, temperature, allergens |
| `/waste` | Yield and waste analysis, waste predictor |
| `/documents` | Document search and upload |
| `/schema-scout` | Discovered tables, PII flags, drift-gate status |
| `/sql-steward` | Semantic layer entities and live query linting |
| `/surveys` | Published elenchus surveys with run counts |
| `/audit` | agent-blackbox hash-chained audit ledger |
| `/config` | Environment wiring and docker-compose reference |
| `/login` | Sign-in, auto-skipped in dev mode |

## Run

```bash
pnpm install
pnpm dev --port 3002
```

Open http://localhost:3002. Point `FLOORMIND_API_URL` at the FloorMind backend
(default http://localhost:8001) and `NEXT_PUBLIC_ELENCHUS_URL` at elenchus
(default http://localhost:8000). All other variables are optional; the defaults
assume localhost.

| Variable | Purpose |
|----------|---------|
| `FLOORMIND_API_URL` | FloorMind FastAPI backend (server-side proxy) |
| `NEXT_PUBLIC_SCOUT_URL` | schema-scout backend |
| `NEXT_PUBLIC_SQL_STEWARD_URL` | sql-steward server |
| `NEXT_PUBLIC_ELENCHUS_URL` | elenchus backend (server-side proxy) |
| `NEXT_PUBLIC_BLACKBOX_URL` | agent-blackbox ledger |

When a backend is not running, the page shows a fallback banner instead of
crashing.

## Quality

```bash
pnpm exec tsc --noEmit   # typecheck
pnpm exec eslint src     # lint
pnpm build               # production build
```