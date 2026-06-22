# Roadmap

A short, honest view of where the stack is going. Dates are intentions, not promises.

## Now

- All eight components public and usable; `sql-steward` (the flagship) at v0.2.0.
- `sql-sop` and `sql-sop-mcp` published on PyPI.
- Governance is enforced as policy-as-code in this repo (see [GOVERNANCE.md](GOVERNANCE.md)).

## Next (roughly the next three months)

- **Publish the rest to PyPI** — `query-warden`, `pii-veil`, `agent-blackbox`, and
  `sql-steward`, so the optional extras install without git.
- **List the MCP servers in the official MCP registry** (`sql-steward`,
  `sql-explorer-mcp`, `sql-sop-mcp`).
- **Per-role query and cost budgets in `sql-steward`** — currently only `max_rows`.
- **Prompt-injection guard on the natural-language input** — the architecture already
  removes the text-to-SQL path, but the NL surface is worth hardening.

## Later

- **`thread-recall`** (governed agent memory) public release.
- Broader SQL dialect coverage across the stack.

## Out of scope

- Cloud-hosted or paid-SaaS versions. The stack stays free and on-prem by design.
