"""Decide whether a role may run a SQL query, before it touches the database."""
from __future__ import annotations

from dataclasses import dataclass, field

from .extract import extract_refs
from .policy import Policy


@dataclass
class Decision:
    """The outcome of a check: allowed or not, with the reasons it was blocked."""

    allowed: bool
    role: str
    violations: list[str] = field(default_factory=list)

    @property
    def reason(self) -> str | None:
        return "; ".join(self.violations) if self.violations else None

    def __bool__(self) -> bool:
        return self.allowed


class Warden:
    """Checks SQL against an access policy. Read-only, no database connection needed."""

    def __init__(self, policy: Policy):
        self.policy = policy

    @classmethod
    def from_yaml(cls, path: str) -> "Warden":
        return cls(Policy.from_yaml(path))

    @classmethod
    def from_dict(cls, data: dict) -> "Warden":
        return cls(Policy.from_dict(data))

    def check(self, sql: str, role: str | None = None, dialect: str | None = None) -> Decision:
        """Return a Decision for running ``sql`` as ``role``.

        Falls back to the policy's ``default_role`` when ``role`` is None. An
        unknown role, an unparseable query, a table outside the role's allow-list,
        a denied column, or a bare ``SELECT *`` when columns are denied all block.
        """
        role = role or self.policy.default_role
        if role is None or role not in self.policy.roles:
            return Decision(allowed=False, role=str(role), violations=[f"unknown role '{role}'"])

        r = self.policy.roles[role]
        try:
            refs = extract_refs(sql, dialect=dialect)
        except Exception as e:
            return Decision(allowed=False, role=role, violations=[f"could not parse SQL: {e}"])

        violations: list[str] = []

        allowed = self.policy.allowed_tables(r)
        if allowed is not None:
            for table in sorted(refs.tables):
                if table.lower() not in allowed:
                    violations.append(f"role '{role}' may not query table '{table}'")

        denied = {c.lower() for c in r.deny_columns}
        if denied:
            for column in sorted(refs.columns):
                if column.lower() in denied:
                    violations.append(f"role '{role}' may not access column '{column}'")
            if refs.select_star:
                violations.append(
                    f"role '{role}' may not use SELECT * (it could expose restricted columns: "
                    + ", ".join(sorted(denied))
                    + ")"
                )

        return Decision(allowed=not violations, role=role, violations=violations)
