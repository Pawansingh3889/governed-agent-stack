# Roadmap

A short, honest view of where the stack is going. Dates are intentions, not promises.

## Now

- All eleven components public and usable; `sql-steward` (the flagship) at v0.4.1.
- Seven of the ten packages are on PyPI: `sql-sop`, `sql-sop-mcp`, `sql-steward`,
  `sql-explorer-mcp`, `query-warden`, `pii-veil`, and `thread-recall`.
- `thread-recall` (governed agent memory) released and in the workspace.
- Per-role query budgets ship in `sql-steward` — a persistent lifetime cap by default,
  or a sliding-window rate limit, stored in SQLite so reconnecting does not reset it.
- Governance is enforced as policy-as-code in this repo (see [GOVERNANCE.md](GOVERNANCE.md)).

## Next (roughly the next three months)

- **Publish the remaining three to PyPI** — `agent-blackbox`, `drift-gate`, and
  `schema-scout`, so the optional extras install without git.
- **List the MCP servers in the official MCP registry** (`sql-steward`,
  `sql-explorer-mcp`, `sql-sop-mcp`).
- **Cost budgets in `sql-steward`** — query counts are governed; the spend a role can
  drive (rows scanned, engine time) is not.
- **Prompt-injection guard on the natural-language input** — the architecture already
  removes the text-to-SQL path, but the NL surface is worth hardening.
- **One environment to run the stack from** — `apps/control-tower` holds the registry
  (`tools.yaml`) that describes every component's liveness check, headline metrics and
  UI link. See [`apps/control-tower/REGISTRY.md`](apps/control-tower/REGISTRY.md).

## Later

- Broader SQL dialect coverage across the stack.

## Out of scope

- Cloud-hosted or paid-SaaS versions. The stack stays free and on-prem by design.
