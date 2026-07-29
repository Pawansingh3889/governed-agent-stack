"""agent-blackbox adapter — optional, but never silently optional.

The rule this module exists to enforce:

    Not configured        -> do nothing, say nothing.
    Configured + missing  -> refuse to run.

"No-op when the dependency isn't installed" is correct when the operator
never asked for auditing. It is a security defect when they did: the
operator believes there is a tamper-evident record and there is not.
"""

from __future__ import annotations

import os
from typing import Any

ENV_DB = "DRIFT_GATE_AUDIT_DB"
ENV_KEY = "AGENT_BLACKBOX_KEY"

_INSTALL_HINT = (
    f"{ENV_DB} is set, so this run is expected to be recorded in a "
    f"tamper-evident ledger — but agent-blackbox is not installed.\n"
    f"  Install it:  pip install 'drift-gate[audit]'\n"
    f"  Or unset {ENV_DB} to run without an audit trail (and know that you did)."
)


class LedgerUnavailable(RuntimeError):
    """Auditing was requested but cannot be provided."""


class Ledger:
    """Thin wrapper so the rest of the codebase never imports agent_blackbox."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path if db_path is not None else os.environ.get(ENV_DB)
        self._led: Any = None

        if not self.db_path:
            return

        try:
            from agent_blackbox import Ledger as _Led  # type: ignore
        except ImportError as e:
            raise LedgerUnavailable(_INSTALL_HINT) from e

        self._led = _Led(self.db_path)

    @property
    def enabled(self) -> bool:
        return self._led is not None

    @property
    def hmac_chained(self) -> bool:
        return bool(os.environ.get(ENV_KEY))

    def record(
        self,
        action: str,
        target: str,
        payload: Any = None,
        meta: dict | None = None,
        outcome: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._led.record(
            actor="drift-gate",
            action=action,
            target=target,
            payload=payload,
            meta=meta or {},
            outcome=outcome,
        )

    def verify(self) -> tuple[bool, int]:
        if not self.enabled:
            return (True, 0)
        r = self._led.verify()
        return (bool(r.ok), int(getattr(r, "verified", 0)))
