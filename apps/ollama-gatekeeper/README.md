# ollama-gatekeeper

A governance gateway in front of a local LLM. The model runs on your
machine, generates SQL from a natural-language request, and the gateway
decides what is allowed to reach the database. Reads pass, writes and DDL
die at the door, and every decision is written to a tamper-evident ledger.

No cloud, no API keys, no data leaving the machine.

## The idea

An "agentic harness" is everything wrapped around an LLM to turn it into
an agent: the tools, the loop, and the logic that evaluates its output.
Most of that infrastructure is built to make the agent *more capable*.
This is the part that makes it *safe to run*.

```
you --(natural language)--> gateway --> Ollama (local model)
                               |                |
                               |          (model writes SQL)
                               v                |
                        sql_guard policy <------+
                               |
                    allow (SELECT) / refuse (writes, DDL)
                               |
                               v
                    append-only, hash-chained ledger
```

The model can *say* anything. It can write `DROP TABLE customers` all day.
The gateway is the one identity between the model and the data, and it
refuses the statement before it ever runs. The append-only ledger means
"what did the agent try to do?" always has a provable answer.

## Run it

Requires [Ollama](https://ollama.com) running locally with at least one
model pulled (`ollama pull phi3:mini`). Then:

```bash
python3 gateway.py                              # runs the built-in demo
python3 gateway.py "delete every order from 2020"   # one request
```

The demo sends one safe request and two dangerous ones, and prints the
model's SQL, the gateway's verdict, and the ledger hash for each.

## What each part is

- **The model** — served by Ollama on `localhost:11434`, entirely on-prem.
- **`sql_guard`** — the same policy shape as the browser demo and the
  Terraform OPA container: `verb(statement)` is parsed, `SELECT` passes,
  a blocklist of write/DDL verbs is refused, unknown verbs fail closed.
- **The ledger** — each record hashes the previous record's hash plus its
  own contents. Editing any past entry breaks the chain from that point,
  which `verify_ledger()` detects.

## Limits (read before trusting)

- This governs the model's SQL *output*. It is not a substitute for a
  read-only database connection, which makes writes physically impossible
  at the driver level. Run both: the connection is the hard floor, the
  gateway adds policy nuance (PII scope, audit) a connection can't.
- SQL extraction from a small model's free text is best-effort. In a real
  deployment the model emits a structured tool call, not prose, and the
  gateway parses that.
- The policy here is deliberately minimal (verb allowlist). Real
  enforcement adds schema scoping, row limits, and PII redaction — see the
  design notes in schema-scout.
