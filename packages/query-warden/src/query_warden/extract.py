"""Pull the tables and columns a SQL statement references, using sqlglot."""
from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp


@dataclass
class Refs:
    """Tables and columns a statement touches, plus whether it uses a bare SELECT *."""

    tables: set[str] = field(default_factory=set)
    columns: set[str] = field(default_factory=set)
    select_star: bool = False


def extract_refs(sql: str, dialect: str | None = None) -> Refs:
    """Return the tables, columns, and bare-`SELECT *` flag for a query.

    Raises ``sqlglot.errors.ParseError`` if the SQL cannot be parsed. A bare
    ``SELECT *`` (or ``t.*``) is reported separately from ``COUNT(*)``, which
    does not expose columns.
    """
    tree = sqlglot.parse_one(sql, read=dialect)
    refs = Refs()

    for table in tree.find_all(exp.Table):
        if table.name:
            refs.tables.add(table.name)

    for column in tree.find_all(exp.Column):
        if column.name:
            refs.columns.add(column.name)

    for select in tree.find_all(exp.Select):
        for projection in select.expressions:
            if isinstance(projection, exp.Star) or (
                isinstance(projection, exp.Column) and isinstance(projection.this, exp.Star)
            ):
                refs.select_star = True

    return refs
