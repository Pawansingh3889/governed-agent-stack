"""The access policy: roles, the tables or domains each may read, and denied columns."""
from __future__ import annotations

from dataclasses import dataclass, field

import yaml

WILDCARD = "*"


@dataclass
class Role:
    """What one role is allowed to touch."""

    name: str
    allow_tables: list[str] = field(default_factory=list)
    allow_domains: list[str] = field(default_factory=list)
    deny_columns: list[str] = field(default_factory=list)


@dataclass
class Policy:
    """A set of roles, an optional domain-to-tables map, and a default role."""

    roles: dict[str, Role]
    domains: dict[str, list[str]] = field(default_factory=dict)
    default_role: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Policy":
        domains = {k: list(v or []) for k, v in (data.get("domains") or {}).items()}
        roles: dict[str, Role] = {}
        for name, spec in (data.get("roles") or {}).items():
            spec = spec or {}
            roles[name] = Role(
                name=name,
                allow_tables=list(spec.get("allow_tables") or []),
                allow_domains=list(spec.get("allow_domains") or []),
                deny_columns=list(spec.get("deny_columns") or []),
            )
        return cls(roles=roles, domains=domains, default_role=data.get("default_role"))

    @classmethod
    def from_yaml(cls, path: str) -> "Policy":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh) or {})

    def allowed_tables(self, role: Role) -> set[str] | None:
        """Lower-cased set of tables the role may read, or None when unrestricted.

        A ``*`` in either ``allow_tables`` or ``allow_domains`` means no table
        restriction (None). Otherwise the set is the union of the role's explicit
        tables and the tables behind each allowed domain.
        """
        if WILDCARD in role.allow_tables or WILDCARD in role.allow_domains:
            return None
        names: set[str] = {t.lower() for t in role.allow_tables}
        for domain in role.allow_domains:
            names.update(t.lower() for t in self.domains.get(domain, []))
        return names
