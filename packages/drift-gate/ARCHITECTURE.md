# Architecture

How drift-gate is built, why it is built that way, and where it sits in a
governed agent system.

---

## 1. The problem it exists for

A schema is a contract that nobody signed. It changes without notice, and the
tools reading it fail in two very different ways:

- **Loudly** — a dropped column, a renamed table. The query errors, you find out
  immediately, nothing bad ships.
- **Silently** — `DECIMAL(10,2)` becomes `INT`. Every yield figure loses its
  fraction. No exception. The CSV looks right. You sign the log.

Only the second kind is dangerous, and it is the kind ordinary testing does not
catch, because the code is fine. The data is wrong.

drift-gate exists to turn the second failure mode into the first.

---

## 2. The one architectural decision that matters

**Detection is separated from judgement.**

```
catalog.json (baseline)  ─┐
                          ├─► diff_catalogs() ──► [Change]  ◄── no opinions
catalog.json (live)      ─┘                          │
                                                     ▼
                             drift-policy.yml ──► evaluate() ──► [Verdict]
                                                     │
                                            ▼                 ▼
                                       exit code          HTML report
```

`catalog.py` observes differences. It knows nothing about severity — it cannot
tell you whether a change matters, only that it happened. `policy.py` decides.
Everything arguable lives in one YAML file and one evaluation function.

This buys three things:

1. **The diff is exhaustively testable** with no policy in the way.
2. **The verdict is arguable.** When drift-gate fails your export, you can point
   at the line in `drift-policy.yml` that caused it and disagree with it. A gate
   whose reasoning you cannot inspect gets disabled the first time it is wrong.
3. **Policy changes need no code changes.** New rule, no release.

---

## 3. Module map

| Module | Responsibility | Depends on |
|---|---|---|
| `types.py` | Parse SQL types; classify a transition as widened / narrowed / family-changed / unknown. **Pure.** | nothing |
| `catalog.py` | The only module that knows schema-scout's file shape. Normalise, then diff. **No policy.** | `types` |
| `policy.py` | Load `drift-policy.yml`; turn changes into verdicts. **All judgement lives here.** | `catalog` |
| `manifest.py` | Seal a baseline directory; verify the seal. `sha256sum -c` compatible. | nothing |
| `ledger.py` | Optional agent-blackbox adapter. Refuses to no-op silently. | agent-blackbox *(optional)* |
| `report.py` | Render verdicts as one self-contained HTML file. | `policy` |
| `cli.py` | Wire it together; own the exit codes. | everything |

The dependency graph is a DAG with no cycles, and the three most important
modules (`types`, `catalog`, `manifest`) have no third-party dependencies at
all. That is deliberate: the parts that decide whether your export runs should
not be able to break because a transitive dependency shipped a bad release.

---

## 4. Control flow of `check`

```
  1. verify baseline seal ────────────── broken? ──► exit 2
         │                                            (not 1 — see §5)
         ▼
  2. load baseline + live catalogs ───── unreadable? ──► exit 2
         │                               empty? ──────► exit 2
         ▼
  3. diff  ──► [Change]          (no policy applied yet)
         ▼
  4. evaluate against policy ──► [Verdict]
         ▼
  5. record verdict to ledger    (if configured; otherwise skipped)
         ▼
  6. render HTML report          (if --report)
         ▼
  7. exit 1 on FAIL, 0 otherwise
```

Step 1 comes first for a reason. Every later step reads files from the baseline
directory. Checking their integrity *after* reading them would be theatre.

---

## 5. Exit codes are the API

| Code | Meaning |
|---|---|
| `0` | CLEAN, or WARN without `--strict` |
| `1` | FAIL — drift the policy classifies as breaking |
| `2` | The gate could not run |

The `1` / `2` split is the most-considered decision in the CLI.

*"The schema changed"* and *"I cannot tell you whether the schema changed"* are
different facts. A caller that collapses them will eventually treat an
unreadable catalog or a broken seal as drift, retry, get the same result, and
add `|| true`. Keeping them distinct means the wrapper script can do the right
thing with each: halt on `1`, page a human on `2`.

Everything printed is presentation. The exit code is the contract.

---

## 6. Trust model of the seal

`drift-gate seal` writes `MANIFEST.sha256` **inside** the directory it protects.
On its own that detects accident, not adversary: anyone who can rewrite
`catalog.json` can rewrite the manifest.

The digest closes that gap. `seal` prints one hash standing for the whole
baseline, and `--expect` (or `DRIFT_GATE_EXPECT_DIGEST`) compares against it.

```
  seal        → per-file hashes + one aggregate digest
  manifest    → lives beside the files   → detects accidental change
  digest      → lives somewhere else     → detects deliberate change
```

Where "somewhere else" means a signed note, a password manager, a GPG-signed
commit, a printed sheet in a folder. The tool cannot help you with that step,
and says so in the output rather than pretending otherwise.

The manifest format is plain `sha256sum -c` output on purpose. If you never
trust drift-gate again, you can still verify the baseline with coreutils.

---

## 7. Optional dependencies, and the one rule about them

drift-gate has three install profiles. The rule governing all of them:

> **Not configured → do nothing, say nothing.
> Configured → work, or refuse to run.**

`DRIFT_GATE_AUDIT_DB` set without `[audit]` installed exits `2` with an install
hint. It does **not** carry on unaudited.

This is a direct response to a real failure pattern: a README documents
`pip install "tool[audit]"`, the extra was never declared in the package, pip
warns and continues, the operator sets the env var, and the audit chain that
everyone believes exists has never written a row. Silence about a missing
safety layer is worse than not offering the layer.

---

## 8. Where drift-gate sits in the stack

```
      ┌──────────────────────────────────────────────┐
      │ Foundations                                  │
      │   schema-scout   maps the database           │
      │   drift-gate     proves the map still holds  │  ◄── this repo
      └───────────────────────┬──────────────────────┘
                              │ must pass before anything below runs
      ┌───────────────────────▼──────────────────────┐
      │ Scoped access                                │
      │   sql-steward / sql-explorer-mcp             │
      │   query-warden  → pii-veil                   │
      └───────────────────────┬──────────────────────┘
                              ▼
      ┌──────────────────────────────────────────────┐
      │ Accountability                               │
      │   agent-blackbox — hash-chained ledger       │
      └──────────────────────────────────────────────┘
```

schema-scout answers *"what is in there?"*. drift-gate answers *"is it still
what you checked?"*. Everything above assumes the answer is yes, so drift-gate
runs first or the rest is built on an assumption nobody tested.

---

## 9. Using it in front of an agent

If a planning agent sits above this stack, drift-gate is what decides whether
that agent is allowed to start.

```
  drift-gate check ── FAIL ──► agent never wakes up; refusal recorded
         │
        PASS
         ▼
  supervisor agent  ◄─ non-deterministic: plans, picks tools, decides when done
         │
         ▼
  ┌─────────────────────────────────────────────────┐
  │ DETERMINISTIC FROM HERE DOWN — no model in path  │
  │ sql-steward (compiled SQL, no run_sql)           │
  │ query-warden → pii-veil → read-only database     │
  │ agent-blackbox records every call and refusal    │
  └─────────────────────────────────────────────────┘
         │
         ▼
  a report for a human. Never an action.
```

The split is the point: **agency in planning, determinism in enforcement**. The
agent can plan freely precisely because it cannot act. drift-gate is the bottom
of the deterministic half — it does not make the agent safe, it makes the ground
the agent stands on verified.

drift-gate itself contains no model, makes no network call, and has no
autonomy. It is not an agent and does not claim to be one.

---

## 10. Deliberate non-goals

| Not built | Why |
|---|---|
| `--auto-update-baseline` | A gate that can re-bless itself is not a gate. Re-baselining is a human decision with a new digest recorded out of band. |
| Fix suggestions | Suggesting a fix implies knowing intent. drift-gate cannot know whether a DBA's change was correct. |
| An LLM anywhere | The verdict must be reproducible from two files and a policy. A model makes it unreproducible and unauditable. |
| Database connections | drift-gate never opens one. Capture is schema-scout's job, and keeping the gate offline means it can run anywhere, including on an air-gapped box holding two exported files. |
| Data quality checks | Row-level validation is a different tool (`sql-sop --contract`). This one checks shape. |
| A daemon or service | It is a command that exits. Nothing to keep running, nothing listening on a port. |

---

## 11. Extending it

Adding a change kind is four steps, in this order:

1. Add the constant to `catalog.py` and emit it from `diff_catalogs`.
2. Add a detection test — assert it is produced, with no policy involved.
3. Add it to `drift-policy.example.yml` under `fail_on` or `warn_on`, with a
   comment saying what data loss it represents.
4. Add a policy test asserting the severity, including watch-list interaction.

Do not add it to `policy.py`. Policy has no per-kind logic and should not grow
any — a kind not listed in the policy already defaults to FAIL, which is the
correct behaviour for something nobody has classified yet.

Type-classification changes go in `types.py` and need a case in
`tests/test_types.py` written as *"this transition loses this data"*, not as
*"this returns this enum"*. The test names are the specification.
