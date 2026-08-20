<div align="center">

# Governed Agent Stack

**Free, on-prem building blocks for an AI agent you can point at a real database and actually audit.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://github.com/govern-agents/governed-agent-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/govern-agents/governed-agent-stack/actions)
[![GitHub Stars](https://img.shields.io/github/stars/govern-agents/governed-agent-stack?style=social)](https://github.com/govern-agents/governed-agent-stack)

</div>

---

Every 2026 agentic-AI report lands on the same two blockers, and neither of them is the model. The first is the data underneath it: nobody mapped the database, so the agent is working blind. The second is governance around it: nothing constrains what the agent can touch, and there is no trustworthy record of what it did. Pilots stall there, not on model quality.

This is a reference stack of small tools that each solve one of those problems, run entirely on your own hardware, and cost nothing. Each one stands on its own. Put together, they make up an agent you can place in front of a regulated database without losing sleep.

**Nobody packages this free and on-prem. That is the whole point.**

## Quick start

```bash
git clone https://github.com/govern-agents/governed-agent-stack
cd governed-agent-stack
uv sync --all-packages --all-extras
```

Point schema-scout at your database, then ask FloorMind a question:

```bash
uv run --directory apps/floormind python scripts/seed_demo_db.py
uv run --directory apps/floormind streamlit run app.py
```

## The layers

<table>
<tr>
<td width="120" align="center"><b>Layer</b></td>
<td width="180" align="center"><b>Tool</b></td>
<td><b>What it does</b></td>
</tr>
<tr>
<td align="center">Foundations</td>
<td><a href="https://github.com/govern-agents/schema-scout">schema-scout</a> + <a href="https://github.com/govern-agents/drift-gate">drift-gate</a></td>
<td>Map the database, recover undeclared relationships, flag PII, score agent-readiness, then refuse to run once the schema moves without review.</td>
</tr>
<tr>
<td align="center">Scoped access</td>
<td><a href="https://github.com/govern-agents/sql-explorer-mcp">sql-explorer-mcp</a> + <a href="https://github.com/govern-agents/sql-sop">sql-sop</a> + <a href="https://github.com/govern-agents/query-warden">query-warden</a></td>
<td>Give the agent read-only SQL access: every query is parsed, linted, and checked against role-based access rules before it runs.</td>
</tr>
<tr>
<td align="center">Reasoning</td>
<td><a href="https://github.com/govern-agents/governed-agent-stack/tree/main/apps/floormind">FloorMind</a></td>
<td>Turn a plain-English question into a checked query and a plain-English answer.</td>
</tr>
<tr>
<td align="center">Result masking</td>
<td><a href="https://github.com/govern-agents/pii-veil">pii-veil</a></td>
<td>Mask any PII that survives into result rows before they reach the model.</td>
</tr>
<tr>
<td align="center">Accountability</td>
<td><a href="https://github.com/govern-agents/agent-blackbox">agent-blackbox</a></td>
<td>Record every step in a tamper-evident, hash-chained log you can verify later.</td>
</tr>
<tr>
<td align="center">Memory</td>
<td><a href="https://github.com/govern-agents/thread-recall">thread-recall</a></td>
<td>Carry context between turns without carrying PII with it, masked on write.</td>
</tr>
<tr>
<td align="center">Surveys</td>
<td><a href="https://github.com/govern-agents/elenchus">elenchus</a> + <a href="https://github.com/govern-agents/governed-agent-stack/tree/main/packages/elenchus-mcp">elenchus-mcp</a></td>
<td>Governed survey authoring and conducting. Create, publish, and analyse surveys with an LLM-driven conversational engine that keeps the model on rails.</td>
</tr>
</table>

## Flagship: sql-steward

<a href="https://github.com/govern-agents/sql-steward"><b>sql-steward</b></a> bundles scoped access, masking, and accountability into one Model Context Protocol server behind a stronger guarantee: **the agent never writes SQL at all.**

Instead of validating SQL the model wrote, sql-steward compiles every query from a semantic layer you control (entities, joins, metrics, PII tags), so there is no `run_sql` tool to misuse. Blocked PII is refused before the query runs, every call can land in the agent-blackbox ledger, and the same tools work across SQL Server, Postgres, and SQLite.

Use it as the all-in-one entry point, or compose the individual pieces yourself. They are the same building blocks either way.

## How a question flows through it

```
  Question in plain English
         |
         v
  +-----------------+     +------------------+     +------------------+
  | schema-scout    |---->| FloorMind        |---->| sql-sop          |
  | (map, context)  |     | (NL -> SQL)      |     | (lint)           |
  +-----------------+     +------------------+     +------------------+
                                                         |
                                                         v
  +-----------------+     +------------------+     +------------------+
  | agent-blackbox  |<----| pii-veil         |<----| query-warden     |
  | (audit log)     |     | (mask PII)       |     | (role check)     |
  +-----------------+     +------------------+     +------------------+
         ^                                                |
         |                                                v
  +-----------------+                             +------------------+
  | thread-recall   |                             | Your database    |
  | (memory)        |                             | (stays on-prem)  |
  +-----------------+                             +------------------+
```

## Why on-prem, why free

<table>
<tr>
<td width="32" align="center">🔒</td>
<td><b>Nothing leaves the building.</b> The database, the LLM, and the logs all stay on your hardware. That is the whole reason this exists for regulated or privacy-sensitive data.</td>
</tr>
<tr>
<td align="center">🛡️</td>
<td><b>Read-only by enforcement, not by trust.</b> Three layers have to agree before a query runs, so a misconfigured login is not your only protection.</td>
</tr>
<tr>
<td align="center">📋</td>
<td><b>Auditable by design.</b> The log is tamper-evident, so "what did the agent do" has a real, checkable answer.</td>
</tr>
<tr>
<td align="center">💰</td>
<td><b>No licence cost, no per-seat fee, no vendor lock-in.</b> Clone the pieces you need and run them.</td>
</tr>
</table>

## The pieces

Each tool is its own repo with its own docs. Start with whichever problem is most urgent. Usually that is schema-scout, because everything downstream depends on knowing the data first.

<table>
<tr>
<td><a href="https://github.com/govern-agents/sql-steward"><b>sql-steward</b></a></td>
<td>Flagship. One governed MCP server where the agent never writes SQL. Queries are compiled from a semantic layer you control, multi-dialect (SQL Server, Postgres, SQLite), with optional role checks, masking, and audit wired in.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/schema-scout"><b>schema-scout</b></a></td>
<td>Maps a SQL Server database, recovers hidden foreign keys, flags PII, scores agent-readiness, and serves the catalog to an agent over MCP.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/drift-gate"><b>drift-gate</b></a></td>
<td>Compares the live schema against a baseline you sealed by hand and exits non-zero when something breaking has moved. No model, no network.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/sql-explorer-mcp"><b>sql-explorer-mcp</b></a></td>
<td>Read-only Model Context Protocol server for SQL Server, Postgres, and SQLite, with three layers of safety.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/sql-sop"><b>sql-sop</b></a></td>
<td>A fast rule-based SQL linter that catches dangerous and slow patterns before a query runs. Available on <a href="https://pypi.org/project/sql-sop/">PyPI</a>.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/query-warden"><b>query-warden</b></a></td>
<td>Role-based access control for SQL. Decides whether the asker's role may touch the tables and columns a query references, before it runs.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/pii-veil"><b>pii-veil</b></a></td>
<td>Masks PII in query results (Microsoft Presidio when installed, regex fallback otherwise) before they reach the model.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/governed-agent-stack/tree/main/apps/floormind"><b>FloorMind</b></a></td>
<td>An on-prem natural-language query tool for manufacturing data, eval-measured rather than vibes-based.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/governed-agent-stack/tree/main/apps/dashboard"><b>dashboard</b></a></td>
<td>A Next.js management console: overview, agent flow, per-component status pages, audit log, and configuration.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/agent-blackbox"><b>agent-blackbox</b></a></td>
<td>An append-only, hash-chained ledger that gives agent actions a tamper-evident audit trail.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/sql-sop-mcp"><b>sql-sop-mcp</b></a></td>
<td>The sql-sop linter as MCP tools, so a model checks its own SQL before proposing it.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/thread-recall"><b>thread-recall</b></a></td>
<td>Governed agent memory, per-thread history and semantic recall, masked on write and namespaced per actor.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/elenchus"><b>elenchus</b></a></td>
<td>Standalone, embeddable survey service. Authors build surveys (by natural language or builder UI); respondents complete them through a conversational, LLM-driven runner that keeps the model on rails.</td>
</tr>
<tr>
<td><a href="https://github.com/govern-agents/governed-agent-stack/tree/main/packages/elenchus-mcp"><b>elenchus-mcp</b></a></td>
<td>Model Context Protocol bridge for Elenchus. Lets an LLM create, publish, conduct, and analyse surveys through a running Elenchus instance.</td>
</tr>
</table>

## Repository layout

```
governed-agent-stack/
  packages/              twelve publishable libraries
    agent-blackbox/      drift-gate/         elenchus-mcp/
    pii-veil/            query-warden/       schema-scout/
    sql-explorer-mcp/    sql-sop/            sql-sop-mcp/
    sql-steward/         thread-recall/
  apps/                  not packages, outside the workspace
    floormind/           the Streamlit + FastAPI + Next.js application
    dashboard/           the Next.js management console
    ollama-gatekeeper/   a governance gateway in front of a local model
    control-tower/       the registry that runs the stack
  policies/              governance rules, checked against stack.yaml
  stack.yaml             the components, as machine-readable data
```

## Contributing

We welcome contributions of all levels. See the [Contributing Guide](CONTRIBUTING.md) to get started.

1. Find an issue tagged `good first issue` or `help wanted`
2. Fork, branch, code, test (`make test`, `make lint`)
3. Open a PR with a conventional commit prefix (`feat:`, `fix:`, `docs:`, `chore:`)

Security issues do **not** go in a public GitHub issue. See [SECURITY.md](SECURITY.md).

## Community

- [GitHub Issues](https://github.com/govern-agents/governed-agent-stack/issues) -- bug reports and feature requests
- [GitHub Discussions](https://github.com/govern-agents/governed-agent-stack/discussions) -- questions and ideas

## License

[MIT](LICENSE) -- each component carries the same MIT licence individually.
