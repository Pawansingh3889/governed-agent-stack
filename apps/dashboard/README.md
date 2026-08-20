# Governed Agent Stack Dashboard

A Next.js management console for the Governed Agent Stack. Shows the end-to-end multi-agent flow across every component with live status, per-component pages, the audit ledger, and configuration.

## Pages

| Page | What it shows |
|------|---------------|
| `/` | Overview with component health and status cards |
| `/flow` | The end-to-end pipeline: question to query to audited result |
| `/schema-scout` | Discovered tables, PII flags, drift-gate status |
| `/sql-steward` | Semantic layer entities and live query linting |
| `/surveys` | Published elenchus surveys with run counts |
| `/audit` | agent-blackbox hash-chained audit ledger |
| `/config` | Environment wiring and docker-compose reference |

## Run

```bash
pnpm install
pnpm dev
```

Open http://localhost:3000.

## Configure

Copy `.env.example` to `.env.local` and point each variable at a running
component backend. All are optional; the defaults assume localhost.

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_SCOUT_URL` | schema-scout backend |
| `NEXT_PUBLIC_SQL_STEWARD_URL` | sql-steward server |
| `NEXT_PUBLIC_ELENCHUS_URL` | elenchus backend |
| `NEXT_PUBLIC_BLACKBOX_URL` | agent-blackbox ledger |

When a backend is not running, the page shows a fallback banner instead of
crashing.

## Quality

```bash
pnpm exec tsc --noEmit   # typecheck
pnpm exec eslint src     # lint
pnpm build               # production build
```