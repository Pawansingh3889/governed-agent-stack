package main

import rego.v1

# Governance rules for the stack, enforced against stack.yaml with conftest.
# Each rule fails the check (a "deny") when a component breaks the stack's own bar.

# The set of licenses the stack allows. Free and open by principle.
allowed_licenses := {"MIT", "Apache-2.0"}

# The governance concerns a component is allowed to declare. Keeps roles meaningful
# and single-purpose rather than a free-text grab bag.
allowed_roles := {
	"schema-discovery",
	"read-only-access",
	"sql-linting",
	"access-control",
	"pii-masking",
	"audit",
	"governed-query-gateway",
	"reasoning-application",
}

# Every component must declare a license.
deny contains msg if {
	some c in input.components
	not c.license
	msg := sprintf("component %q declares no license", [c.name])
}

# The license must be one the stack allows.
deny contains msg if {
	some c in input.components
	c.license
	not allowed_licenses[c.license]
	msg := sprintf("component %q uses license %q, which is not in the allowed set %v", [c.name, c.license, allowed_licenses])
}

# On-prem is the whole point: every component must run on the user's own hardware.
deny contains msg if {
	some c in input.components
	c.on_prem != true
	msg := sprintf("component %q must set on_prem: true", [c.name])
}

# Every component must name the single governance concern it covers.
deny contains msg if {
	some c in input.components
	not c.role
	msg := sprintf("component %q declares no governance role", [c.name])
}

deny contains msg if {
	some c in input.components
	c.role
	not allowed_roles[c.role]
	msg := sprintf("component %q has role %q, which is not a recognised governance concern", [c.name, c.role])
}

# Every component must point at a source repository.
deny contains msg if {
	some c in input.components
	not c.repo
	msg := sprintf("component %q has no repo", [c.name])
}
