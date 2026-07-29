# The control-tower registry

`tools.yaml` is the whole configuration of the stack's main environment: one entry per
component saying how to start it, how to tell whether it is up, and where to read the few
numbers worth putting on a page.

The principle the tower is built on is that **nothing is re-implemented here**. Every
metric points at output the tool already writes. If a number is not on the page, the fix
is to make the component record it, not to compute it in the tower.

## What is in this directory, and what is not

`tools.yaml` and this file are here. `app.py` and `static/` — the FastAPI app that reads
them, with `/status`, `/start/{id}`, `/stop/{id}`, keepalive supervision and PID-on-port
detection — still live in the standalone `control-tower` repository and are copied in
alongside. `make up` says so explicitly until they are.

This split is deliberate: the registry is the part that has to be correct *for this
checkout*, and it is the part that rots. It is validated on every PR by
`scripts/check_tools_registry.py`, so it cannot drift from the tree it describes even
while the app lives elsewhere.

`apps/control-tower` stays **outside** the uv workspace (`members` is `packages/*`) and
outside `stack.yaml`, the same as `apps/ollama-gatekeeper`. It is the environment, not a
governance component, and `policies/stack.rego` should not be asked to judge it.

## The schema

```yaml
version: 1
defaults:
  cwd: .            # every run.cmd executes from the repo root unless overridden
  env: {...}        # environment applied to every tool (see "One directory", below)
groups: [...]       # the sections of the page, in display order
tools: [...]
```

Every tool entry:

| field | required | meaning |
|---|---|---|
| `id` | yes | Stable key. `/start/{id}` and `/stop/{id}` take this. |
| `name` | yes | Display name. |
| `group` | yes | Must be one of the top-level `groups`. |
| `tier` | yes | `service` or `artifact`. See below. |
| `desc` | yes | One or two lines, in the component's own terms. |
| `port` | services | The port it listens on. Unique across the registry. |
| `check` | services | How to tell it is up. |
| `open` | no | Link to its own UI. Omitted when it has none. |
| `run.cmd` | yes | The command `/start/{id}` runs. |
| `run.cwd` | no | Working directory, relative to the repo root. Defaults to `.`. |
| `gateway` | no | Present when the tool speaks stdio MCP. See below. |
| `metrics` | yes | Possibly empty. Empty and absent must not look alike. |

### Two tiers

Only `apps/floormind` serves HTTP on its own. Everything else is a CLI or a **stdio** MCP
server, and the tower's checks are `http` and `tcp` only. So a component registers as one
of two things:

- **`service`** — has a port, so it gets a real liveness dot and, where it has a UI, an
  `open` link. The five MCP servers are services only because the gateway fronts them.
- **`artifact`** — produces output rather than serving it. No `port`, no `check`; the
  tower reads its `metrics` and nothing else. This is the tower's existing design, not a
  workaround for the MCP servers.

The validator enforces the split: an artifact declaring a `port` or a `check` is an error,
and so is a service without them.

### Checks

```yaml
check: { type: http, url: http://127.0.0.1:8501/_stcore/health, expect_status: [200] }
check: { type: tcp,  port: 9101 }
```

`tcp` for anything the gateway fronts — it is true regardless of whether the gateway ends
up being the in-repo shim or mcpo, so the registry does not have to change if that
decision does. `http` where there is a real health endpoint;
`/_stcore/health` is Streamlit's.

### Metrics

```yaml
- { label: audited calls, source: sqlite,    path: logs/steward.db, query: "SELECT COUNT(*) FROM entries", optional: true }
- { label: tables,        source: json_file, path: out/agent_context.json, key: summary.tables,            optional: true }
```

`sqlite` needs a `query`, `json_file` needs a dotted `key`. `path` is always relative to
the repo root and may not escape the tree. `optional: true` marks a file that only exists
after the tool has run once — without it, the validator requires the file to be there.

Almost every `sqlite` metric reads the same table. `agent_blackbox.Ledger`
(`packages/agent-blackbox/agent_blackbox/ledger.py`) creates exactly one:

```sql
entries(seq, ts, actor, action, target, payload, meta, outcome, prev_hash, hash)
```

`sql-steward`, `drift-gate`, `thread-recall` and `apps/floormind` all write through it, so
one query shape covers the whole Accountability tier, and `outcome` has a shared
vocabulary across components: `ok`, `refused`, `error`, `skipped`, `broken`.

### One directory, set by the registry

Six environment variables name what is structurally the same ledger, and several default
to nothing at all — `DRIFT_GATE_AUDIT_DB` and `SQL_EXPLORER_AUDIT_DB` mean "write no
ledger" when unset. Rather than let the tower guess where output landed, `defaults.env`
**sets** them, so the path a tool writes to and the path a metric reads from are the same
string in the same file:

```yaml
SQL_STEWARD_AUDIT_DB:  logs/steward.db
SQL_STEWARD_BUDGET_DB: logs/steward-budget.db
SQL_EXPLORER_AUDIT_DB: logs/explorer.db
DRIFT_GATE_AUDIT_DB:   logs/drift-gate.db
THREAD_RECALL_DB:      logs/recall-mem.db
FLOORMIND_LOG_DIR:     ../../logs      # floormind runs from apps/floormind
FLOORMIND_BLACKBOX_DB: ../../logs/blackbox.db
```

`logs/` and `out/` are gitignored. `make clean` removes both.

## Fronting the stdio servers

All five MCP servers call a bare `mcp.run()`, which is stdio. Something has to give them
an HTTP surface before a `tcp` check means anything. Each service entry carries the data
that fronting needs, so the choice of *what* does the fronting stays open:

```yaml
gateway:
  flavor: fastmcp              # or mcp-sdk
  module: sql_steward.server
  attr: mcp
  requires: out/catalog.json   # optional prerequisite
```

`apps/control-tower/mcp_gate.py` reads these and runs one subprocess per entry. It is not
written yet; `make gate` says so. Three things it has to handle:

- **Two different `FastMCP` classes.** `sql-steward`, `sql-explorer-mcp`, `sql-sop-mcp`
  and `thread-recall` use the `fastmcp` package — `mcp.run(transport="http", port=N)`.
  `schema-scout` uses the official SDK's `mcp.server.fastmcp.FastMCP`, whose equivalent is
  `transport="streamable-http"` with the port set on the constructor. `flavor` says which.
- **`schema-scout-mcp` has no module-level object.** It builds its `FastMCP` inside
  `main()` (`packages/schema-scout/schema_scout/mcp_server.py`), which is why its `attr`
  is `null`. It needs a `build_server(catalog) -> FastMCP` factory extracted before the
  gateway can import it.
- **`schema-scout-mcp` needs a catalog to start at all** — hence `requires`. Run
  `schema-scout` first or its dot is dead by construction on a fresh checkout.

Neither `fastmcp` nor `mcp` is a new dependency: `fastmcp 3.4.5` and `mcp 2.0.0` are
already resolved in `uv.lock`, so the shim costs one file.

**When mcpo is worth the extra dependency instead.** Raw HTTP transport gives a checkable
endpoint but no human UI, which is why every MCP service entry here omits `open`.
[mcpo](https://github.com/open-webui/mcpo) (MIT) proxies stdio MCP to REST *and* generates
a Swagger UI per server — which is what the previous registry used it for. If a real
`open` link per MCP server matters more than keeping the dependency list short, use mcpo
and fill in `open`; the rest of the registry is unchanged either way.

## Known gaps

These are recorded here rather than papered over in `tools.yaml`, because an entry that
points at a file which will never appear is worse than an honest empty list.

**Components with nothing to read.** `query-warden` and `pii-veil` are pure
stdin→stdout CLIs. They write nothing persistent, so both carry `metrics: []`. The fix is
the ledger the rest of the stack already has: `packages/drift-gate/src/drift_gate/ledger.py`
is a ~40-line wrapper that stays a no-op unless its env var is set, with `agent-blackbox`
as an optional `[audit]` extra so the dependency stays opt-in. Copy it into each, add
`QUERY_WARDEN_AUDIT_DB` and `PII_VEIL_AUDIT_DB`, and record one entry per decision. Then
"how many queries did the policy layer refuse this week" becomes answerable, which today
it is not.

**Output the schema cannot read yet.** `apps/ollama-gatekeeper` writes `ledger.jsonl` and
`apps/floormind` writes `logs/audit.jsonl`. `json_file` parses a JSON document and cannot
read JSONL. floormind is covered because it also writes an `agent-blackbox` ledger at
`logs/blackbox.db`; the gatekeeper is not, and carries `metrics: []`. Either add a
`jsonl_file` source to the app (count lines, read the last record) or leave it.

**Side products.** `pay-warden`, `viewops-survey-service`,
`manufacturing-compliance-dashboard` and `warden-lm` live in their own repositories. The
`Side products` group exists and is empty: their paths cannot be confirmed from this
checkout, and the validator would reject a guess. Add them where the paths are real:

```yaml
  - id: pay-warden
    name: pay-warden
    group: Side products
    tier: service
    desc: >-
      Policy firewall with budgets, velocity limits and approval thresholds.
    port: 92xx
    check: { type: http, url: "http://127.0.0.1:92xx/health", expect_status: [200] }
    open: http://127.0.0.1:92xx
    run:
      cwd: ../pay-warden        # will fail validation until the path is real
      cmd: ...
    metrics: []
```

Note that `run.cwd` must resolve inside this tree, so a sibling checkout needs either a
symlink or a relaxation of that rule in `scripts/check_tools_registry.py` — decide which
when the paths are in front of you rather than now.

## Changing the registry

`make registry` (or `python3 scripts/check_tools_registry.py`) checks it, and CI runs the
same thing on every PR. It catches what a YAML parser cannot: paths from another operating
system, `run.cmd` naming a console script no package declares, duplicate ports, unknown
groups, a metric source the tower cannot read, and a non-optional path that is not there.
