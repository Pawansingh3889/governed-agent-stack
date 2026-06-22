# Policies

Policy-as-code for the stack's own governance rules. The components are declared in
[`../stack.yaml`](../stack.yaml); the policies here assert that every one of them meets
the bar set in [`../GOVERNANCE.md`](../GOVERNANCE.md). This is the stack governing
itself with the same kind of policy it helps you apply to an agent.

## What's enforced

[`stack.rego`](stack.rego) fails the check if any component:

- declares no license, or a license outside the allowed set (MIT / Apache-2.0)
- does not set `on_prem: true`
- declares no governance role, or a role that isn't a recognised concern
- points at no source repo

## Run it

```bash
# from the repo root
scripts/check_policies.sh
# or directly, if you have conftest:
conftest test stack.yaml --policy policies/
```

[conftest](https://www.conftest.dev/) wraps Open Policy Agent's Rego engine for testing
config files. If it isn't installed, `check_policies.sh` says so and exits cleanly rather
than failing.

## Extend it

Add a rule by writing another `deny` block in `stack.rego`. For example, to require a
maintained-since date:

```rego
deny contains msg if {
	some c in input.components
	not c.maintained
	msg := sprintf("component %q has no maintained flag", [c.name])
}
```

Then add the field to each component in `stack.yaml` and re-run the check. New components
have to satisfy every rule before they're considered part of the stack.
