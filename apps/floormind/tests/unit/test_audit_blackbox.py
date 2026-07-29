"""Tests for agent-blackbox wiring in the audit log (modules/audit_log.py).
Skipped if agent-blackbox is not installed.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

pytest.importorskip("agent_blackbox")


def test_events_recorded_to_tamper_evident_ledger(tmp_path, monkeypatch) -> None:
    db = tmp_path / "blackbox.db"
    monkeypatch.setenv("FLOORMIND_BLACKBOX_DB", str(db))
    from modules import audit_log
    importlib.reload(audit_log)  # reset cached ledger, pick up the env path

    audit_log.log_question("what was yesterday's yield?")
    audit_log.log_execution("SELECT 1", row_count=3, duration_ms=10.0)

    from agent_blackbox import Ledger
    led = Ledger(str(db))
    entries = list(led.entries())
    assert len(entries) >= 2
    assert led.verify().ok  # hash chain intact


def test_disabled_when_flag_off(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FLOORMIND_BLACKBOX_DB", raising=False)
    monkeypatch.setenv("FLOORMIND_BLACKBOX", "0")
    from modules import audit_log
    importlib.reload(audit_log)

    # Must not raise and must not open a default ledger.
    audit_log.log_execution("SELECT 1", row_count=1, duration_ms=1.0)
    assert audit_log._get_ledger() is None
