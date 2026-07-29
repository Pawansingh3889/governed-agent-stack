"""Load a schema-scout catalog into a normalised model, and diff two of them.

ADAPTER BOUNDARY
----------------
This is the only module that knows schema-scout's on-disk shape. If
``catalog.json`` changes, change ``load_catalog`` and nothing else.

The loader is deliberately tolerant about *where* fields live and strict
about *what* it ends up with: every column must resolve to a name and a
type string, or the load fails loudly. A gate that silently reads zero
columns would pass every check forever, which is the worst possible bug
in a tool like this — so ``load_catalog`` refuses an empty catalog.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .types import TypeChange, classify_type_change


class CatalogError(RuntimeError):
    """Raised when a catalog cannot be read or is structurally unusable."""


@dataclass(frozen=True)
class Column:
    table: str
    name: str
    type: str
    nullable: bool | None = None
    is_pii: bool = False

    @property
    def key(self) -> tuple[str, str]:
        return (self.table.lower(), self.name.lower())


@dataclass
class Catalog:
    source: Path | None
    columns: dict[tuple[str, str], Column] = field(default_factory=dict)
    primary_keys: dict[str, tuple[str, ...]] = field(default_factory=dict)
    row_counts: dict[str, int] = field(default_factory=dict)
    readiness: int | None = None

    @property
    def tables(self) -> set[str]:
        return {t for t, _ in self.columns}


def _as_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("yes", "true", "1", "y"):
        return True
    if s in ("no", "false", "0", "n"):
        return False
    return None


def _first(d: dict, *names: str, default=None):
    for n in names:
        if n in d and d[n] is not None:
            return d[n]
    return default


def _iter_table_blocks(raw: Any):
    """Yield (table_name, table_dict) from the shapes schema-scout emits."""
    if isinstance(raw, dict):
        tables = _first(raw, "tables", "Tables", default=None)
        if isinstance(tables, dict):
            for name, block in tables.items():
                yield str(name), block
            return
        if isinstance(tables, list):
            for block in tables:
                if not isinstance(block, dict):
                    continue
                schema = _first(block, "schema", "table_schema")
                name = _first(block, "name", "table_name", "table", default="")
                full = f"{schema}.{name}" if schema and "." not in str(name) else str(name)
                yield full, block
            return
    if isinstance(raw, list):
        for block in raw:
            if isinstance(block, dict):
                schema = _first(block, "schema", "table_schema")
                name = _first(block, "name", "table_name", "table", default="")
                full = f"{schema}.{name}" if schema and "." not in str(name) else str(name)
                yield full, block
        return
    raise CatalogError("Unrecognised catalog shape: expected a dict or a list of tables.")


def load_catalog(path: str | Path) -> Catalog:
    p = Path(path)
    if not p.exists():
        raise CatalogError(f"Catalog not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:  # pragma: no cover - message only
        raise CatalogError(f"Catalog is not valid JSON: {p}: {e}") from e

    cat = Catalog(source=p)

    if isinstance(raw, dict):
        score = _first(raw, "readiness_score", "agentic_readiness", "readiness")
        if isinstance(score, dict):
            score = _first(score, "score", "value")
        if isinstance(score, (int, float)):
            cat.readiness = int(score)

    for table_name, block in _iter_table_blocks(raw):
        if not isinstance(block, dict):
            continue

        rc = _first(block, "row_count", "rows", "approx_rows")
        if isinstance(rc, (int, float)):
            cat.row_counts[table_name.lower()] = int(rc)

        pk = _first(block, "primary_key", "pk", "primary_keys", default=None)
        if isinstance(pk, str):
            pk = [pk]
        if isinstance(pk, list) and pk:
            cat.primary_keys[table_name.lower()] = tuple(
                sorted(str(c).lower() for c in pk)
            )

        cols = _first(block, "columns", "Columns", default=[])
        if isinstance(cols, dict):
            cols = [{"name": k, **(v if isinstance(v, dict) else {"type": v})}
                    for k, v in cols.items()]
        if not isinstance(cols, list):
            continue

        for c in cols:
            if not isinstance(c, dict):
                continue
            cname = _first(c, "name", "column_name", "column")
            ctype = _first(c, "type", "data_type", "sql_type", "datatype")
            if cname is None or ctype is None:
                continue
            pii = _first(c, "is_pii", "pii", "pii_flag", default=False)
            col = Column(
                table=str(table_name),
                name=str(cname),
                type=str(ctype),
                nullable=_as_bool(_first(c, "nullable", "is_nullable")),
                is_pii=bool(pii) and str(pii).lower() not in ("no", "false", "0"),
            )
            cat.columns[col.key] = col

    if not cat.columns:
        raise CatalogError(
            f"Catalog {p} produced zero columns. Refusing to continue — a gate "
            f"reading an empty catalog would pass every check. Check that this "
            f"is a schema-scout catalog.json and see the ADAPTER BOUNDARY note "
            f"in drift_gate/catalog.py."
        )
    return cat


# --------------------------------------------------------------------------
# Diff
# --------------------------------------------------------------------------

# Change kinds. These strings are the vocabulary of drift-policy.yml, so
# they are API: renaming one is a breaking change.
TABLE_DROPPED = "table_dropped"
TABLE_ADDED = "table_added"
COLUMN_DROPPED = "column_dropped"
COLUMN_ADDED = "column_added"
NULLABLE_ADDED = "nullable_added"
NULLABLE_REMOVED = "nullable_removed"
PK_CHANGED = "pk_changed"
PII_ADDED = "pii_added"
ROW_COUNT_SHIFT = "row_count_shift"


@dataclass(frozen=True)
class Change:
    kind: str
    table: str
    column: str | None = None
    before: str | None = None
    after: str | None = None
    detail: str = ""

    @property
    def target(self) -> str:
        return f"{self.table}.{self.column}" if self.column else self.table


def diff_catalogs(baseline: Catalog, live: Catalog) -> list[Change]:
    """Compute every observable difference. Severity is decided later.

    Separating *detection* from *judgement* is the whole design: this
    function has no policy in it, so it can be tested exhaustively.
    """
    changes: list[Change] = []

    base_tables = {t for t, _ in baseline.columns}
    live_tables = {t for t, _ in live.columns}

    for t in sorted(base_tables - live_tables):
        changes.append(Change(kind=TABLE_DROPPED, table=t))
    for t in sorted(live_tables - base_tables):
        changes.append(Change(kind=TABLE_ADDED, table=t))

    common_tables = base_tables & live_tables

    for key in sorted(set(baseline.columns) - set(live.columns)):
        if key[0] in common_tables:
            col = baseline.columns[key]
            changes.append(
                Change(kind=COLUMN_DROPPED, table=col.table, column=col.name,
                       before=col.type)
            )
    for key in sorted(set(live.columns) - set(baseline.columns)):
        if key[0] in common_tables:
            col = live.columns[key]
            changes.append(
                Change(kind=COLUMN_ADDED, table=col.table, column=col.name,
                       after=col.type)
            )

    for key in sorted(set(baseline.columns) & set(live.columns)):
        b, lv = baseline.columns[key], live.columns[key]

        verdict = classify_type_change(b.type, lv.type)
        if verdict is not TypeChange.NONE:
            changes.append(
                Change(kind=verdict.value, table=b.table, column=b.name,
                       before=b.type, after=lv.type)
            )

        if b.nullable is False and lv.nullable is True:
            changes.append(
                Change(kind=NULLABLE_ADDED, table=b.table, column=b.name,
                       before="NOT NULL", after="NULL")
            )
        elif b.nullable is True and lv.nullable is False:
            changes.append(
                Change(kind=NULLABLE_REMOVED, table=b.table, column=b.name,
                       before="NULL", after="NOT NULL")
            )

        if lv.is_pii and not b.is_pii:
            changes.append(
                Change(kind=PII_ADDED, table=b.table, column=b.name,
                       detail="newly flagged as PII by schema-scout")
            )

    for t in sorted(common_tables):
        bpk = baseline.primary_keys.get(t)
        lpk = live.primary_keys.get(t)
        if bpk != lpk and (bpk or lpk):
            changes.append(
                Change(kind=PK_CHANGED, table=t,
                       before=", ".join(bpk) if bpk else "(none)",
                       after=", ".join(lpk) if lpk else "(none)")
            )

    for t in sorted(common_tables):
        b_rows = baseline.row_counts.get(t)
        l_rows = live.row_counts.get(t)
        if b_rows is None or l_rows is None:
            continue
        if b_rows == 0:
            if l_rows == 0:
                continue
            pct = 100.0
        else:
            pct = abs(l_rows - b_rows) / b_rows * 100.0
        if pct > 0:
            changes.append(
                Change(kind=ROW_COUNT_SHIFT, table=t, before=str(b_rows),
                       after=str(l_rows), detail=f"{pct:.1f}%")
            )

    return changes
