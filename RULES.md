# Rules

Seven invariants. Each one is enforced by a test, and the test is named here so
you can check the claim rather than take it on trust.

If a change breaks one of these, the change is wrong — not the rule. Changing a
rule is a deliberate act that needs an entry in `CHANGELOG.md` explaining what
guarantee was traded away and why.

```bash
pytest -q          # all seven, plus the rest
```

---

## Rule 1 — No model, no network, no autonomy

drift-gate never calls an LLM, never opens a socket, and never takes an action
on your behalf. It reads files and returns a verdict.

The generated HTML report has no `<script>`, no CDN link, no webfont, no
external image. It must render identically on an air-gapped machine with no
resolver.

*Enforced by:* `test_report_is_self_contained` — asserts the rendered HTML
contains no `http://`, `https://`, `//cdn`, or `<script>`.

*Why:* a verification aid that phones home is not a verification aid. And a
verdict produced by a model is not reproducible, which means it is not
evidence.

---

## Rule 2 — An unclassified change is an unreviewed change

A change kind that appears in neither `fail_on` nor `warn_on` is treated as
**FAIL**, not ignored.

*Enforced by:* `test_unclassified_kind_defaults_to_fail`.

*Why:* the alternative fails open. Add a new detection in a future version and
every existing policy would silently start ignoring it. Failing closed means a
new kind of drift announces itself the first time it occurs, which is exactly
when you want to hear about it.

You can override this with `default_severity: warn`. Doing so is a decision you
have written down in your own policy file, which is the point.

---

## Rule 3 — The watch list beats everything

Any change to a target in `watch:` fails, overriding `warn_on` and overriding
`ignore`. There is no way to suppress a watched target except by removing it
from the watch list.

*Enforced by:* `test_watch_list_overrides_warn`, `test_watch_list_overrides_ignore`.

*Why:* the watch list is where you declare the columns your export actually
reads. If a wildcard elsewhere in the file could silence one of them, the watch
list would be advisory — and the one thing it must not be is advisory.

Corollary: keep it short. A watch list covering half the schema produces noise,
noise gets ignored, and an ignored gate is decoration.

---

## Rule 4 — Optional never means silently absent

> Not configured → do nothing, say nothing.
> Configured → work, or refuse to run.

If `DRIFT_GATE_AUDIT_DB` is set and `agent-blackbox` is not installed,
drift-gate exits `2` with an install hint. It does not continue unaudited.

*Enforced by:* `test_audit_requested_but_unavailable_refuses_to_run`.

*Why:* an operator who set that variable believes there is a tamper-evident
record of every run. If there is not, they will discover it during an audit,
which is the worst possible moment. "No-op when the dependency is missing" is
correct only when nobody asked for the feature.

---

## Rule 5 — "I cannot tell" is not "nothing changed"

A broken seal, an unsealed baseline, an unreadable catalog, a malformed policy
and an unavailable ledger all exit `2`. Only actual policy-breaking drift exits
`1`.

*Enforced by:* `test_broken_seal_exits_two_not_one`,
`test_unsealed_baseline_exits_two`.

*Why:* a wrapper script that treats every non-zero code as drift will retry,
get the same failure, and eventually grow an `|| true`. Distinct codes let the
caller halt on `1` and escalate on `2`, which are genuinely different responses.

---

## Rule 6 — An empty catalog is an error, never a pass

If a catalog file parses but yields zero columns, drift-gate refuses to run.

*Enforced by:* `test_load_rejects_empty_catalog`.

*Why:* this is the worst bug this tool could have. A loader that silently reads
nothing would compare nothing to nothing, report CLEAN, and do so *forever* —
while appearing to work perfectly. Every schema change would sail through a
green gate. Refusing an empty catalog is the single highest-value assertion in
the codebase.

---

## Rule 7 — When a type change is ambiguous, call it breaking

Type classification is biased in one direction, on purpose:

- A type we do not recognise → `type_changed_unknown`, never "safe".
- A cross-family change → `type_family_changed`, never analysed further.
- `nvarchar(50)` → `varchar(50)` → **narrowed**, despite identical length,
  because non-ASCII is lost.
- `decimal(10,2)` → `decimal(10,4)` → **narrowed**, despite equal precision,
  because integral capacity drops from 8 digits to 6.

*Enforced by:* the `TestNarrowing` class in `tests/test_types.py`.

*Why:* the costs are asymmetric. A false *narrowed* costs one review. A false
*widened* costs a silently truncated yield figure on a signed export that has
already gone to a regulated system on a USB stick. Bias toward the cheap error.

---

## The rule about the rules

drift-gate detects and refuses. It does **not** fix, suggest, or decide.

There is no `--auto-update-baseline` and there will not be one. Re-baselining is
a human act: capture, read, seal, and record the new digest somewhere the tool
cannot reach. A gate that can re-bless itself is not a gate — it is a log
message.

The HTML report follows the same rule. It never says "proceed". It states what
changed and closes with what *you* must decide.
