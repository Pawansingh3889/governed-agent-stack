# 1. LLM provider: OpenAI-compatible API

Status: Accepted (supersedes original Ollama decision)

## Context

FloorMind turns operator questions into SQL against factory production
data. That data — yields, waste, customer orders, batch traceability,
non-conformances — is commercially sensitive and, under BRC and the
major UK retailer codes of practice, must stay within the supplier's
control. A factory deploying FloorMind cannot send its production data,
or the questions operators ask about it, to a third-party API.

The original decision (ADR 0001) ran the LLM entirely on-premises via
Ollama with Gemma 3 12B. This served the on-prem requirement but
limited model quality to what a 12B local model could achieve.

## Decision

Use an OpenAI-compatible API for LLM inference. This supports:
- **OpenAI directly** (GPT-4o, GPT-4.1-mini) when data sensitivity allows
- **Local proxies** (LiteLLM, OpenAI-compatible servers) for on-prem deployments
- **Any OpenAI-compatible provider** (Azure OpenAI, etc.)

The model is configurable via `OPENAI_MODEL` (default: `gpt-4o`).
For on-prem, set `OPENAI_BASE_URL` to a local proxy endpoint.

## Consequences

- **Good:** access to frontier model quality (GPT-4o) for complex SQL generation.
- **Good:** single API interface works with any provider.
- **Good:** local proxy option preserves the on-prem guarantee when needed.
- **Good:** simpler infrastructure (no Ollama container to manage).
- **Bad:** direct OpenAI usage sends prompts off-site (use local proxy for regulated data).
- **Bad:** per-query API cost when using cloud providers.
- **Constraint:** `OPENAI_API_KEY` must be set; the app fails gracefully if missing.

## Migration notes

- `OLLAMA_MODEL` → `OPENAI_MODEL`
- `OLLAMA_BASE_URL` → `OPENAI_BASE_URL`
- `ollama` Python package → `openai` Python package
- Default model: `gemma3:12b` → `gpt-4o`
