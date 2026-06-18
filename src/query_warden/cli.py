"""Command-line check: query-warden check --policy p.yaml --role operator "SELECT ...".

Exit code 0 when the query is allowed, 1 when it is denied. Handy in CI or as a
guard step in a shell pipeline.
"""
from __future__ import annotations

import argparse

from .warden import Warden


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="query-warden", description="Role-based access control for SQL.")
    sub = parser.add_subparsers(dest="command", required=True)

    chk = sub.add_parser("check", help="Check whether a role may run a query.")
    chk.add_argument("sql", help="The SQL statement to check.")
    chk.add_argument("--policy", required=True, help="Path to the policy YAML file.")
    chk.add_argument("--role", help="Role to check as (defaults to the policy's default_role).")
    chk.add_argument("--dialect", help="sqlglot dialect, for example mssql or postgres.")

    args = parser.parse_args(argv)

    warden = Warden.from_yaml(args.policy)
    decision = warden.check(args.sql, role=args.role, dialect=args.dialect)
    if decision.allowed:
        print(f"ALLOW (role={decision.role})")
        return 0
    print(f"DENY (role={decision.role}): {decision.reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
