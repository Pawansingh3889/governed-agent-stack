"""sql-sop linting layer for FloorMind.

Runs the sql-sop linter (pip install sql-sop) as a static-safety pass over
generated SQL, the same layer sql-explorer-mcp uses. Error-severity findings
block the query; warnings are advisory. A no-op when sql-sop is not installed
or when FLOORMIND_SOP_LINT is set to 0.

Part of the Governed Agent Stack: sql-sop is the static SQL safety layer that
sits between SQL generation and execution.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

_OFF = {"0", "false", "no", "off"}


@dataclass
class SopResult:
    """Findings from the sql-sop pass, split into blocking and advisory."""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def enabled() -> bool:
    """True unless FLOORMIND_SOP_LINT is explicitly turned off."""
    return os.getenv("FLOORMIND_SOP_LINT", "1").strip().lower() not in _OFF


def lint(sql: str) -> SopResult:
    """Lint SQL with sql-sop.

    Returns blocking errors (error-severity findings) and advisory warnings.
    Never raises: a linter problem must not break the agent. Returns an empty
    result when sql-sop is unavailable, disabled, or the SQL is empty.
    """
    if not sql or not sql.strip() or not enabled():
        return SopResult()
    try:
        from sql_guard.fluent import SqlGuard
    except ImportError:
        return SopResult()
    try:
        findings = SqlGuard().scan(sql).findings
    except Exception:
        return SopResult()

    errors: List[str] = []
    warnings: List[str] = []
    for f in findings:
        rule = getattr(f, "rule_id", "?")
        message = getattr(f, "message", "")
        line = getattr(f, "line", None)
        where = f" (line {line})" if line else ""
        text = f"sql-sop {rule}: {message}{where}"
        if getattr(f, "severity", "warning") == "error":
            errors.append(text)
        else:
            warnings.append(text)
    return SopResult(errors=errors, warnings=warnings)
