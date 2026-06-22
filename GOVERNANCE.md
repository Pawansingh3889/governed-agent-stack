# Governance

This stack is about governing what an AI agent can do to a real database, so it
should hold itself to the same bar. This file says what the bar is and how it's
enforced.

## Goals

- Make the stack's own rules explicit, in one place, for contributors and auditors.
- Keep those rules machine-checkable rather than aspirational prose.
- Stay honest about what is and isn't covered.

## Principles every component holds to

- **On-prem by default.** A component runs on the user's own hardware; nothing has to
  leave the machine for it to work.
- **Open and free.** MIT, or Apache-2.0 where a patent grant is warranted.
- **Single responsibility.** Each component does one governance job and is usable alone.
- **Auditable.** Where a component acts on data, that action can be recorded.

## Policy-as-code

The principles above aren't just a list here — they're enforced as code. The stack's
components are declared in [`stack.yaml`](stack.yaml), and the policies in
[`policies/`](policies/) assert that every component meets the bar (declares a license,
runs on-prem, names the governance concern it covers). New components have to pass the
same check.

Run it locally:

```bash
scripts/check_policies.sh      # runs conftest against stack.yaml if conftest is installed
```

See [`policies/README.md`](policies/README.md) for how the policies work and how to add one.

## Roles

This is currently maintained by [@Pawansingh3889](https://github.com/Pawansingh3889).
There's no pretence of a wider maintainer team yet; that's added when there are
contributors to add, not before.

## Changing the rules

Changes to the principles or the policies go through a normal PR and a passing policy
check. If a change relaxes a rule, the PR should say why in plain terms.
