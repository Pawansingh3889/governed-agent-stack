"""SQL type parsing and narrowing/widening classification.

Pure functions, no I/O, no database. Every decision here is testable
without a connection, which is the point: the gate's verdict must be
reproducible from two catalog files alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_TYPE_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z_][A-Za-z0-9_ ]*?)\s*"
    r"(?:\(\s*(?P<args>[^)]*)\s*\))?\s*$"
)


class Family(str, Enum):
    """Broad type family. Changes across families are almost always breaking."""

    INTEGER = "integer"
    DECIMAL = "decimal"  # exact numeric
    FLOAT = "float"  # approximate numeric
    STRING = "string"
    BINARY = "binary"
    TEMPORAL = "temporal"
    BOOLEAN = "boolean"
    UUID = "uuid"
    JSON = "json"
    OTHER = "other"


# Deliberately explicit rather than clever. A type we do not recognise
# falls to OTHER and is treated conservatively (any change is breaking).
_FAMILIES: dict[str, Family] = {
    # integers
    "tinyint": Family.INTEGER,
    "smallint": Family.INTEGER,
    "int": Family.INTEGER,
    "integer": Family.INTEGER,
    "bigint": Family.INTEGER,
    "serial": Family.INTEGER,
    "bigserial": Family.INTEGER,
    # exact numerics
    "decimal": Family.DECIMAL,
    "numeric": Family.DECIMAL,
    "money": Family.DECIMAL,
    "smallmoney": Family.DECIMAL,
    # approximate numerics
    "float": Family.FLOAT,
    "real": Family.FLOAT,
    "double": Family.FLOAT,
    "double precision": Family.FLOAT,
    # strings
    "char": Family.STRING,
    "nchar": Family.STRING,
    "varchar": Family.STRING,
    "nvarchar": Family.STRING,
    "text": Family.STRING,
    "ntext": Family.STRING,
    "character varying": Family.STRING,
    "character": Family.STRING,
    # binary
    "binary": Family.BINARY,
    "varbinary": Family.BINARY,
    "image": Family.BINARY,
    "bytea": Family.BINARY,
    # temporal
    "date": Family.TEMPORAL,
    "time": Family.TEMPORAL,
    "datetime": Family.TEMPORAL,
    "datetime2": Family.TEMPORAL,
    "smalldatetime": Family.TEMPORAL,
    "datetimeoffset": Family.TEMPORAL,
    "timestamp": Family.TEMPORAL,
    "timestamptz": Family.TEMPORAL,
    "timestamp with time zone": Family.TEMPORAL,
    # misc
    "bit": Family.BOOLEAN,
    "boolean": Family.BOOLEAN,
    "bool": Family.BOOLEAN,
    "uniqueidentifier": Family.UUID,
    "uuid": Family.UUID,
    "json": Family.JSON,
    "jsonb": Family.JSON,
    "xml": Family.JSON,
}

# Integer widths in bytes, used to detect narrowing within the family.
_INT_WIDTH = {
    "tinyint": 1,
    "smallint": 2,
    "int": 4,
    "integer": 4,
    "serial": 4,
    "bigint": 8,
    "bigserial": 8,
}

_FLOAT_WIDTH = {"real": 4, "float": 8, "double": 8, "double precision": 8}

# MAX / unbounded length sentinel.
UNBOUNDED = -1


@dataclass(frozen=True)
class SqlType:
    """A parsed SQL type. `raw` is always preserved for display."""

    raw: str
    name: str
    family: Family
    length: int | None = None  # character/byte length; UNBOUNDED for MAX
    precision: int | None = None  # total digits
    scale: int | None = None  # digits right of the point

    @property
    def is_unbounded(self) -> bool:
        return self.length == UNBOUNDED


def parse_type(raw: str) -> SqlType:
    """Parse a type string such as ``decimal(10,2)`` or ``nvarchar(max)``.

    Unknown types are returned with ``Family.OTHER`` rather than raising:
    a gate that crashes on an unfamiliar type is a gate that gets disabled.
    """
    if raw is None:
        raw = ""
    text = str(raw).strip()
    m = _TYPE_RE.match(text)
    if not m:
        return SqlType(raw=text, name=text.lower(), family=Family.OTHER)

    name = " ".join(m.group("name").lower().split())
    args_raw = m.group("args")
    family = _FAMILIES.get(name, Family.OTHER)

    length = precision = scale = None
    if args_raw:
        parts = [p.strip().lower() for p in args_raw.split(",") if p.strip()]
        nums: list[int] = []
        for p in parts:
            if p in ("max", "-1"):
                nums.append(UNBOUNDED)
            elif p.isdigit():
                nums.append(int(p))
        if family in (Family.DECIMAL,):
            if nums:
                precision = nums[0]
            if len(nums) > 1:
                scale = nums[1]
        elif family in (Family.STRING, Family.BINARY):
            if nums:
                length = nums[0]
        elif family is Family.FLOAT:
            if nums:
                precision = nums[0]
        # temporal fractional-seconds precision is not load-bearing here

    # text/ntext/bytea etc. carry no explicit length but are unbounded
    if (family in (Family.STRING, Family.BINARY) and length is None
            and name in ("text", "ntext", "bytea", "image")):
        length = UNBOUNDED

    return SqlType(
        raw=text,
        name=name,
        family=family,
        length=length,
        precision=precision,
        scale=scale,
    )


class TypeChange(str, Enum):
    """Verdict for a single column type transition."""

    NONE = "none"
    WIDENED = "type_widened"
    NARROWED = "type_narrowed"
    FAMILY_CHANGED = "type_family_changed"
    UNKNOWN = "type_changed_unknown"


def _int_width(t: SqlType) -> int:
    return _INT_WIDTH.get(t.name, 4)


def _float_width(t: SqlType) -> int:
    if t.precision is not None:
        return 4 if t.precision <= 24 else 8
    return _FLOAT_WIDTH.get(t.name, 8)


def _cmp_lengths(old: int | None, new: int | None) -> TypeChange:
    """Compare two lengths where -1 means unbounded."""
    if old == new:
        return TypeChange.NONE
    if old is None or new is None:
        return TypeChange.UNKNOWN
    if new == UNBOUNDED:
        return TypeChange.WIDENED
    if old == UNBOUNDED:
        return TypeChange.NARROWED
    return TypeChange.WIDENED if new > old else TypeChange.NARROWED


def classify_type_change(old_raw: str, new_raw: str) -> TypeChange:
    """Classify a column type transition.

    The bias is deliberate and one-directional: when in doubt, report the
    change as breaking. A false NARROWED costs you one review. A false
    WIDENED costs you a silently truncated yield figure on a signed export.
    """
    old = parse_type(old_raw)
    new = parse_type(new_raw)

    if old.raw.strip().lower() == new.raw.strip().lower():
        return TypeChange.NONE

    if old.family is not new.family:
        return TypeChange.FAMILY_CHANGED

    fam = old.family

    if fam is Family.OTHER:
        # We do not understand it, so we do not bless it.
        return TypeChange.UNKNOWN

    if fam is Family.INTEGER:
        ow, nw = _int_width(old), _int_width(new)
        if ow == nw:
            return TypeChange.NONE
        return TypeChange.WIDENED if nw > ow else TypeChange.NARROWED

    if fam is Family.FLOAT:
        ow, nw = _float_width(old), _float_width(new)
        if ow == nw:
            return TypeChange.NONE
        return TypeChange.WIDENED if nw > ow else TypeChange.NARROWED

    if fam is Family.DECIMAL:
        op, np_ = old.precision, new.precision
        os_, ns = old.scale or 0, new.scale or 0
        if op is None or np_ is None:
            return TypeChange.UNKNOWN
        # Integral capacity is precision - scale. Losing either loses data.
        old_int, new_int = op - os_, np_ - ns
        if new_int < old_int or ns < os_:
            return TypeChange.NARROWED
        if new_int > old_int or ns > os_:
            return TypeChange.WIDENED
        return TypeChange.NONE

    if fam in (Family.STRING, Family.BINARY):
        # nvarchar -> varchar can lose non-ASCII even at equal length.
        old_unicode = old.name.startswith("n")
        new_unicode = new.name.startswith("n")
        if old_unicode and not new_unicode:
            return TypeChange.NARROWED
        return _cmp_lengths(old.length, new.length)

    if fam is Family.TEMPORAL:
        # datetime2 -> date loses time; treat any name change as narrowing
        # unless it is a known widening.
        widenings = {
            ("smalldatetime", "datetime"),
            ("smalldatetime", "datetime2"),
            ("datetime", "datetime2"),
            ("date", "datetime"),
            ("date", "datetime2"),
            ("time", "datetime2"),
            ("datetime2", "datetimeoffset"),
            ("timestamp", "timestamptz"),
        }
        if (old.name, new.name) in widenings:
            return TypeChange.WIDENED
        if old.name == new.name:
            return TypeChange.NONE
        return TypeChange.NARROWED

    return TypeChange.UNKNOWN if old.name != new.name else TypeChange.NONE
