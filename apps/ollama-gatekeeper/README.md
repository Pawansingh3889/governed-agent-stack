# llm-gatekeeper

A governance gateway in front of an OpenAI-compatible LLM.

The model can *say* anything. This gateway sits between the model and the
database and decides what is allowed to run:

```
you --(natural language)--> gateway --> LLM (OpenAI API)
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

No data leaves your machine when used with a local proxy. Every decision
leaves a receipt you can verify.

## Quick start

Requires an OpenAI API key or a local proxy:

```bash
export OPENAI_API_KEY=sk-...
python gateway.py show me total sales by customer
```

Or use with a local proxy (e.g. LiteLLM):

```bash
export OPENAI_BASE_URL=http://localhost:4000
export OPENAI_API_KEY=placeholder
python gateway.py show me total sales by customer
```

## How it works

1. **You ask a question** in natural language.
2. **The model generates SQL** (single statement).
3. **The gate checks the SQL** against a simple policy: only SELECT is allowed.
4. **The decision is logged** in a hash-chained, tamper-evident ledger.

## Features

- **SQL guard** -- blocks INSERT, UPDATE, DELETE, DDL, and GRANT statements.
- **Tamper-evident ledger** -- every entry is SHA-256 hashed with the previous entry's hash.
- **Ledger verification** -- `verify_ledger()` recomputes the chain and detects any edits.
- **Model-agnostic** -- works with any OpenAI-compatible API (GPT-4o, local proxies, etc.).
