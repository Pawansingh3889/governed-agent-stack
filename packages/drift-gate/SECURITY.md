# Security

## Reporting

Report privately via GitHub Security Advisories on this repository
("Report a vulnerability"). Not a public issue.

Acknowledgement within 48 hours; a fix or a stated position within 14 days.

## Threat model

drift-gate is a **detection** tool. It reads two JSON catalogs and a YAML
policy, and returns a verdict. It never connects to a database, never opens a
socket, and never executes SQL.

### What it defends against

- **Accidental schema change** reaching a downstream export unnoticed. This is
  the main case.
- **Silent data loss** from type narrowing that raises no error —
  `DECIMAL(10,2)` to `INT` being the motivating example.
- **Accidental baseline corruption** — an edited or truncated catalog file, via
  `MANIFEST.sha256`.
- **Deliberate baseline tampering**, but *only* when `--expect` (or
  `DRIFT_GATE_EXPECT_DIGEST`) supplies a digest held outside the baseline
  directory. See below.

### What it does not defend against

- **A manifest rewritten alongside the files.** The manifest lives in the
  directory it protects. Without `--expect`, it proves internal consistency,
  not authenticity. Store the digest from `drift-gate seal` somewhere the
  attacker cannot reach and pass it back on every run.
- **A compromised catalog capture.** If schema-scout is fed a false database or
  its output is altered before sealing, drift-gate seals the lie. Capture on a
  host you trust, and read the catalog yourself before sealing it.
- **Row-level data integrity.** drift-gate checks shape. Whether the values are
  correct is a different question and a different tool.
- **Anything at runtime.** It is a command that exits. There is no daemon, no
  port, no persistent state beyond files you pass it.

### Inputs are untrusted data

Catalog and policy files are parsed as data, never evaluated:

- JSON via `json.loads`, YAML via `yaml.safe_load` — no object construction,
  no `!!python/` tags.
- All values reaching the HTML report pass through `html.escape`. A table named
  `<script>alert(1)</script>` renders as text.
- Unknown SQL types never raise; they classify as `type_changed_unknown`, which
  fails by default. A malformed type string cannot crash the gate, and cannot
  sneak past it either.

### Secrets

drift-gate handles none. It takes no connection string and no credentials.
`AGENT_BLACKBOX_KEY`, if set, is read by agent-blackbox rather than by this
tool; supply it from a secret store, not a checked-in file.

Note that a policy file names the tables and columns you care about, which is a
partial map of your schema. `drift-policy.yml` is gitignored by default for
that reason. Commit the example, not yours.
