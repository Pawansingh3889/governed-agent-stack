# drift-gate

**Refuse to run against a schema you have not verified.**

[![CI](https://github.com/Pawansingh3889/drift-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/Pawansingh3889/drift-gate/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> Part of the [Governed Agent Stack](https://github.com/Pawansingh3889/governed-agent-stack): free, on-prem building blocks for an AI agent you can point at a real database and audit.

A DBA changes `YieldKg` from `DECIMAL(10,2)` to `INT` on a Tuesday evening. Nobody tells you. Your exporter runs on Wednesday morning, truncates every yield figure, writes a clean-looking CSV, and you sign the log and carry it to the regulated system on a USB stick.

Nothing errored. That is the problem.

drift-gate is the check that runs before any of that. It compares a live schema against a sealed baseline you verified by hand, applies a policy you wrote, and exits non-zero when something breaking has moved. Silent when nothing has.

**No model. No network. No autonomy.** It reads two JSON files and a YAML policy, and returns a verdict you can reproduce.

---

## Install

```bash
pip install drift-gate                 # compare two existing catalogs
pip install "drift-gate[scout]"        # + capture a live catalog from SQL Server
pip install "drift-gate[audit]"        # + tamper-evident ledger via agent-blackbox
```

Not on PyPI yet — until it is, install from a clone with `pip install -e ".[scout,audit]"`.

Extras are declared, not implied. If you set `DRIFT_GATE_AUDIT_DB` without installing `[audit]`, drift-gate **refuses to run** rather than silently skipping the audit. See [RULES.md](RULES.md#rule-4).

---

## Use it

```bash
# once — capture a baseline, check it yourself, then seal it
schema-scout run --server BUSINESS-SQL --database SI --out ./baseline/
bat ./baseline/catalog.md                      # read it with your own eyes
drift-gate seal --baseline ./baseline/
# -> 9f2c...  record this digest somewhere outside ./baseline/

cp drift-policy.example.yml drift-policy.yml   # then edit it
drift-gate explain-policy                       # confirm it says what you meant

# before every run that touches the database
schema-scout run --server BUSINESS-SQL --database SI --out ./live/
drift-gate check --baseline ./baseline/ --live ./live/ \
                 --expect 9f2c... --report drift.html
```

```
FAIL  type_family_changed    dbo.ProductionRuns.YieldKg  decimal(10,2) -> int   [WATCHED]
WARN  column_added           dbo.ProductionRuns.ShiftRef

FAIL — 1 breaking change(s). Nothing downstream should run.
```

Exit codes are the contract:

| Code | Meaning |
|---|---|
| `0` | CLEAN, or WARN without `--strict` |
| `1` | FAIL — drift your policy classifies as breaking |
| `2` | **The gate could not run** — unsealed baseline, broken seal, bad policy, unreadable catalog, audit requested but unavailable |

`2` is deliberately not `1`. *"The schema changed"* and *"I cannot tell you whether the schema changed"* are different facts, and a caller that conflates them will eventually ship on the second one.

---

## Wire it into an export

```python
import subprocess, sys

def gate(baseline: str, live: str) -> str:
    """Returns the baseline digest to stamp on the signed log. Never returns on drift."""
    r = subprocess.run(
        ["drift-gate", "check", "-b", baseline, "-l", live, "--json"],
        capture_output=True, text=True,
    )
    if r.returncode == 2:
        sys.exit(f"Gate could not run — nothing was checked.\n{r.stderr}")
    if r.returncode == 1:
        sys.exit(f"SCHEMA DRIFT — refusing to export.\n{r.stdout}")
    return json.loads(r.stdout)["baseline_digest"]
```

Stamp that digest into the signed `.txt` log next to the CSV. Then a file that reached the USB stick can be tied back to the exact schema snapshot it was produced against — which is the difference between an audit trail and a pile of files.

---

## The policy

One YAML document, readable in a minute, because a verdict you cannot argue with is a verdict you cannot trust. Full annotated example: [`drift-policy.example.yml`](drift-policy.example.yml).

```yaml
fail_on:  [column_dropped, type_narrowed, type_family_changed, pk_changed, pii_added]
warn_on:  [column_added, type_widened, nullable_added, {row_count_shift: 40%}]
ignore:   {tables: ["staging_*"], columns: ["modifieddate"]}

watch:                          # ANY change here fails, overriding everything above
  ProductionRuns: [RunID, YieldKg, QCStatus]
```

Two properties worth knowing before you rely on it:

- **Unclassified change kinds default to FAIL.** An unclassified change is an unreviewed change. Set `default_severity: warn` to loosen it, and know that you did.
- **`watch` beats `ignore`.** A wildcard elsewhere can never silence a column you declared load-bearing.

Run `drift-gate explain-policy` to print exactly how each change kind will be treated.

---

## What counts as narrowing

The interesting judgement is which type changes lose data. Widening is a warning; narrowing corrupts silently. drift-gate is biased one way on purpose — a false *narrowed* costs you one review, a false *widened* costs you a truncated yield figure on a signed export.

| Change | Verdict | Why |
|---|---|---|
| `decimal(10,2)` → `int` | `type_family_changed` | the fraction is gone |
| `decimal(10,2)` → `decimal(10,4)` | **narrowed** | integral capacity drops 8 → 6 |
| `decimal(10,2)` → `decimal(12,2)` | widened | |
| `bigint` → `int` | narrowed | |
| `nvarchar(max)` → `nvarchar(4000)` | narrowed | |
| `nvarchar(50)` → `varchar(50)` | **narrowed** | same length, loses non-ASCII |
| `datetime2` → `date` | narrowed | time component gone |
| `geography` → `geometry` | `type_changed_unknown` | not understood, so not blessed |

---

## What it is not

It **detects and refuses**; it does not fix, suggest, or decide. There is no `--auto-update-baseline`, and there will not be — a gate that can re-bless itself is not a gate.

It also does not tell you your data is *correct*. A CLEAN verdict means the shape has not moved since a snapshot you personally verified. That is all it means, and the report says so.

For the layer above it — governed query access, PII refusal at compile time, role checks, masking — see [sql-steward](https://github.com/Pawansingh3889/sql-steward). For the ledger, [agent-blackbox](https://github.com/Pawansingh3889/agent-blackbox). For producing the catalogs, [schema-scout](https://github.com/Pawansingh3889/schema-scout).

---

## Limits, plainly

| Area | Reality |
|---|---|
| Dialects | Baseline capture is via schema-scout, which is **SQL Server only** today. Comparison itself is dialect-agnostic — any tool that emits the catalog shape works. |
| Row counts | Only compared when the catalog carries them. schema-scout reads partition statistics, so they are approximate by design. |
| Renames | A rename reads as a drop plus an add. Correct and deliberate: to the exporter, that is exactly what happened. |
| Catalog format | One adapter, in `drift_gate/catalog.py`. If schema-scout's output shifts, that is the only file to change. |
| Trust | The manifest lives beside the files it protects. Without `--expect`, it proves consistency, not authenticity. |

---

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — how the pieces fit, and where agency is and is not allowed
- [RULES.md](RULES.md) — the seven invariants, each with the test that enforces it
- [GOVERNANCE.md](GOVERNANCE.md) — scope lines and how decisions get made
- [SECURITY.md](SECURITY.md) — threat model and reporting
- [CONTRIBUTING.md](CONTRIBUTING.md) — setup, tests, how to add a change kind

## Develop

```bash
git clone https://github.com/Pawansingh3889/drift-gate
cd drift-gate
pip install -e ".[dev]"
pytest -q
```

## License

[MIT](LICENSE).
