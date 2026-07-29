"""drift-policy.yml: turn observed changes into a verdict.

Detection lives in catalog.py and has no opinions. All judgement lives
here, in one file, driven by one YAML document that a reviewer can read
in under a minute. That separation is what makes the verdict arguable
rather than magic.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from .catalog import ROW_COUNT_SHIFT, Change


class Severity(str, Enum):
    FAIL = "fail"
    WARN = "warn"
    IGNORE = "ignore"


# Used when a change kind appears in neither fail_on nor warn_on.
# FAIL, not IGNORE: an unclassified change is an unreviewed change.
DEFAULT_SEVERITY = Severity.FAIL


class PolicyError(RuntimeError):
    pass


@dataclass
class Verdict:
    change: Change
    severity: Severity
    reason: str
    watched: bool = False


@dataclass
class Policy:
    fail_on: set[str]
    warn_on: set[str]
    row_count_threshold: float | None
    ignore_tables: list[str]
    ignore_columns: list[str]
    watch: dict[str, list[str]]
    default_severity: Severity = DEFAULT_SEVERITY

    # ---- loading ---------------------------------------------------------

    @classmethod
    def from_file(cls, path: str | Path) -> Policy:
        p = Path(path)
        if not p.exists():
            raise PolicyError(f"Policy file not found: {p}")
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            raise PolicyError(f"Policy file is not valid YAML: {p}: {e}") from e
        if not isinstance(raw, dict):
            raise PolicyError(f"Policy file must be a mapping at the top level: {p}")
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Policy:
        fail_on: set[str] = set()
        warn_on: set[str] = set()
        threshold: float | None = None

        def _collect(entries: Any, into: set[str]) -> None:
            nonlocal threshold
            for item in entries or []:
                if isinstance(item, str):
                    into.add(item)
                elif isinstance(item, dict):
                    for k, v in item.items():
                        into.add(k)
                        if k == ROW_COUNT_SHIFT:
                            threshold = _parse_pct(v)
                else:
                    raise PolicyError(f"Unsupported policy entry: {item!r}")

        _collect(raw.get("fail_on"), fail_on)
        _collect(raw.get("warn_on"), warn_on)

        overlap = fail_on & warn_on
        if overlap:
            raise PolicyError(
                "These change kinds appear in both fail_on and warn_on, which is "
                f"ambiguous: {', '.join(sorted(overlap))}"
            )

        ignore = raw.get("ignore") or {}
        if isinstance(ignore, list):  # tolerate the list-of-mappings form
            merged: dict[str, Any] = {}
            for item in ignore:
                if isinstance(item, dict):
                    merged.update(item)
            ignore = merged
        if not isinstance(ignore, dict):
            raise PolicyError("`ignore` must be a mapping of tables/columns.")

        watch_raw = raw.get("watch") or {}
        if not isinstance(watch_raw, dict):
            raise PolicyError("`watch` must be a mapping of table -> [columns].")
        watch = {
            str(t).lower(): [str(c).lower() for c in (cols or [])]
            for t, cols in watch_raw.items()
        }

        default = raw.get("default_severity")
        default_sev = Severity(default) if default else DEFAULT_SEVERITY

        return cls(
            fail_on=fail_on,
            warn_on=warn_on,
            row_count_threshold=threshold,
            ignore_tables=[str(x).lower() for x in (ignore.get("tables") or [])],
            ignore_columns=[str(x).lower() for x in (ignore.get("columns") or [])],
            watch=watch,
            default_severity=default_sev,
        )

    # ---- evaluation ------------------------------------------------------

    def _is_watched(self, change: Change) -> bool:
        cols = self.watch.get(change.table.lower())
        if cols is None:
            # also match on unqualified table name (dbo.X vs X)
            short = change.table.split(".")[-1].lower()
            cols = self.watch.get(short)
        if cols is None:
            return False
        if not cols:  # empty list = whole table is watched
            return True
        return change.column is not None and change.column.lower() in cols

    def _is_ignored(self, change: Change) -> bool:
        t = change.table.lower()
        short = t.split(".")[-1]
        for pat in self.ignore_tables:
            if fnmatch.fnmatch(t, pat) or fnmatch.fnmatch(short, pat):
                return True
        if change.column:
            c = change.column.lower()
            for pat in self.ignore_columns:
                if fnmatch.fnmatch(c, pat):
                    return True
        return False

    def evaluate(self, changes: list[Change]) -> list[Verdict]:
        out: list[Verdict] = []
        for ch in changes:
            watched = self._is_watched(ch)

            # A watched target overrides ignore rules. If you listed a column
            # as load-bearing, a wildcard elsewhere must not silence it.
            if not watched and self._is_ignored(ch):
                out.append(Verdict(ch, Severity.IGNORE, "matched an ignore rule"))
                continue

            if ch.kind == ROW_COUNT_SHIFT and self.row_count_threshold is not None:
                pct = _parse_pct(ch.detail)
                if pct is not None and pct < self.row_count_threshold:
                    out.append(
                        Verdict(ch, Severity.IGNORE,
                                f"row-count shift {ch.detail} below "
                                f"{self.row_count_threshold:g}% threshold",
                                watched)
                    )
                    continue

            if watched:
                out.append(
                    Verdict(ch, Severity.FAIL,
                            "target is on the watch list; any change fails", True)
                )
                continue

            if ch.kind in self.fail_on:
                out.append(Verdict(ch, Severity.FAIL, "listed in fail_on"))
            elif ch.kind in self.warn_on:
                out.append(Verdict(ch, Severity.WARN, "listed in warn_on"))
            else:
                out.append(
                    Verdict(ch, self.default_severity,
                            f"change kind '{ch.kind}' is not classified in the "
                            f"policy; defaulting to {self.default_severity.value}")
                )
        return out


def _parse_pct(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().rstrip("%").strip()
    try:
        return float(s)
    except ValueError:
        return None


def summarise(verdicts: list[Verdict]) -> dict[str, int]:
    counts = {s.value: 0 for s in Severity}
    for v in verdicts:
        counts[v.severity.value] += 1
    return counts


def overall(verdicts: list[Verdict]) -> str:
    counts = summarise(verdicts)
    if counts[Severity.FAIL.value]:
        return "FAIL"
    if counts[Severity.WARN.value]:
        return "WARN"
    return "CLEAN"
