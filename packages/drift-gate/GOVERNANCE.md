# Governance

## Scope lines

Four things this project will not do, whatever the request:

1. **No model, no network.** If a feature needs an LLM or an outbound call, it
   belongs in a different repo. The verdict must be reproducible from two files
   and a policy.
2. **No self-blessing.** No `--auto-update-baseline`, no "accept all drift", no
   flag that lets a run rewrite the baseline it just checked.
3. **No database connection.** Capture is schema-scout's job. drift-gate reads
   files, which is why it can run on an air-gapped box.
4. **No advice.** It reports what changed and refuses. It does not suggest a
   fix, because suggesting a fix implies knowing intent, and it cannot.

A PR that crosses one of these gets closed with a pointer here, not a debate.

## Roles

Solo-maintained, open door. Issues and PRs from anyone.

- **Maintainer** — Pawan Singh Kapkoti. Merges, releases, decides scope.
- **Contributor** — anyone with a merged PR. Listed in the README.

## Response times

Best-effort, stated so you can plan rather than guess:

| | Target |
|---|---|
| Issue triaged | 7 days |
| PR first review | 7 days |
| Security report acknowledged | 48 hours (see [SECURITY.md](SECURITY.md)) |

If a PR gets no response in 14 days, ping the issue. Silence is a backlog, not
a rejection.

## Changing a rule

The seven invariants in [RULES.md](RULES.md) are the product. Changing one
requires:

1. An issue explaining which guarantee is being traded away, and for what.
2. A `CHANGELOG.md` entry under Unreleased naming the trade.
3. The enforcing test updated in the same PR, never deleted.

Removing a rule's test without removing the rule is not accepted.

## Releases

SemVer. Before 1.0, minor versions may change the policy schema — the
`CHANGELOG` will say so. The change-kind strings (`column_dropped`,
`type_narrowed`, …) are API: they are the vocabulary of everyone's policy
files, so renaming one is a breaking change.

`pr-sop` enforces the changelog and version-consistency checks in CI.
