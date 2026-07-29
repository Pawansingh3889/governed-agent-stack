# Contributing

Small, friendly codebase. Three modules do the real work and none of them
touches a database, so you can be productive without any infrastructure.

## Setup

```bash
git clone https://github.com/Pawansingh3889/drift-gate
cd drift-gate
pip install -e ".[dev]"
pytest -q
ruff check .
```

No database, no Docker, no fixtures to seed. Every test runs from JSON literals
in `tmp_path`.

## Layout

| File | What lives there |
|---|---|
| `types.py` | SQL type parsing and narrowing classification. Pure functions. |
| `catalog.py` | The only place that knows schema-scout's file shape. Detection, no policy. |
| `policy.py` | All judgement. If you are adding an opinion, it goes here. |
| `manifest.py` | Sealing and verification. |
| `ledger.py` | agent-blackbox adapter. |
| `report.py` | HTML rendering. |
| `cli.py` | Argument parsing and exit codes. |

The separation between `catalog.py` (what changed) and `policy.py` (does it
matter) is load-bearing — see [ARCHITECTURE.md](ARCHITECTURE.md#2). PRs that
put severity logic in `catalog.py` will be asked to move it.

## Good first issues

The easiest wins, in rough order of difficulty:

1. **A new type mapping** — one line in `_FAMILIES` plus a test. Postgres,
   MySQL and DuckDB spellings are all welcome.
2. **A narrowing case we get wrong** — open an issue with the two type strings
   and what data is lost. These are the most valuable reports the project gets.
3. **A new change kind** — see [ARCHITECTURE.md](ARCHITECTURE.md#11) for the
   four steps, in order.
4. **A catalog shape we fail to read** — attach a redacted snippet.

Browse the `good first issue` label.

## Writing tests

Name them after the data loss, not the return value:

```python
def test_unicode_loss_narrows_even_at_equal_length():   # yes
def test_classify_returns_narrowed_for_case_7():        # no
```

The test names in `tests/test_types.py` are the specification for what counts
as narrowing. Someone reading only the names should be able to argue with the
tool's judgement, which is the whole design.

Every PR that changes behaviour needs a test. Every PR that touches one of the
seven invariants in [RULES.md](RULES.md) needs the enforcing test updated in
the same commit — never deleted.

## Conventions

- `ruff check .` must pass. Line length 100.
- Changelog entry under `## [Unreleased]` for anything user-visible; `pr-sop`
  enforces this in CI.
- Error messages tell the reader what to do next, not just what went wrong.
  Compare: `"Policy file not found: x.yml"` versus `"No MANIFEST.sha256 in
  ./baseline. This baseline has never been sealed — run drift-gate seal ..."`.
  Aim for the second.

## Behaviour

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Be kind; assume good faith.
