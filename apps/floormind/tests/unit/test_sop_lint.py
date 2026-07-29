"""Tests for the sql-sop lint layer (modules/sop_lint.py) and its wiring into
the validator. Skipped if sql-sop (the ``sql_guard`` package) is not installed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

pytest.importorskip("sql_guard")  # sql-sop ships the sql_guard package

from modules import sop_lint  # noqa: E402
from modules.sql_validator import validate_sql  # noqa: E402


def test_lint_returns_advisory_warnings() -> None:
    result = sop_lint.lint("SELECT name FROM products")
    assert result.errors == []
    assert any("sql-sop" in w for w in result.warnings)


def test_lint_disabled_via_env(monkeypatch) -> None:
    monkeypatch.setenv("FLOORMIND_SOP_LINT", "0")
    result = sop_lint.lint("SELECT name FROM products")
    assert result.errors == []
    assert result.warnings == []


def test_lint_empty_sql_is_safe() -> None:
    result = sop_lint.lint("")
    assert result.errors == []
    assert result.warnings == []


def test_validator_keeps_lint_out_of_user_warnings() -> None:
    # sql-sop advisories must land in lint_warnings, not the user-facing
    # warnings, so the validator's existing warning contract is unchanged.
    result = validate_sql("SELECT 1")
    assert result.is_valid, result.errors
    assert result.warnings == []
    assert any("sql-sop" in w for w in result.lint_warnings)
