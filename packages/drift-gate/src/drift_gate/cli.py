"""drift-gate command line.

Exit codes are the contract — everything else is presentation:

    0  CLEAN (or WARN, unless --strict)
    1  FAIL  — drift the policy classifies as breaking
    2  the gate itself could not run (unsealed baseline, bad policy,
       unreadable catalog, audit requested but unavailable)

2 is separate from 1 on purpose. "The schema changed" and "I could not
tell you whether the schema changed" are different facts, and a caller
that treats them the same will eventually ship on the second one.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer

from . import __version__
from .catalog import CatalogError, diff_catalogs, load_catalog
from .ledger import Ledger, LedgerUnavailable
from .manifest import SealError
from .manifest import seal as do_seal
from .manifest import verify as do_verify
from .policy import Policy, PolicyError, Severity, overall, summarise
from .report import render, write

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Refuse to run against a schema you have not verified.",
)

EXIT_OK, EXIT_DRIFT, EXIT_ERROR = 0, 1, 2

CATALOG_NAME = "catalog.json"
ENV_EXPECT = "DRIFT_GATE_EXPECT_DIGEST"


def _err(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)


def _warn(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.YELLOW, err=True)


def _ok(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.GREEN, err=True)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _open_ledger() -> Ledger:
    try:
        return Ledger()
    except LedgerUnavailable as e:
        _err(f"AUDIT UNAVAILABLE\n{e}")
        raise typer.Exit(EXIT_ERROR) from None


def _version_cb(value: bool):
    if value:
        typer.echo(f"drift-gate {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False, "--version", callback=_version_cb, is_eager=True,
        help="Show version and exit."
    ),
):
    """drift-gate — a deterministic schema gate. No model, no network, no autonomy."""


# ---------------------------------------------------------------- seal

@app.command()
def seal(
    baseline: Path = typer.Option(..., "--baseline", "-b",
                                  help="Directory holding the trusted catalog."),
):
    """Hash every file in the baseline and write MANIFEST.sha256."""
    try:
        s = do_seal(baseline)
    except SealError as e:
        _err(str(e))
        raise typer.Exit(EXIT_ERROR) from None

    _ok(f"Sealed {len(s.entries)} file(s) in {baseline}")
    typer.echo(s.digest)
    _warn(
        "\nRecord that digest somewhere outside this directory — a signed note, "
        f"your password manager, or {ENV_EXPECT}. The manifest sits next to the "
        "files it protects, so on its own it proves nothing against someone who "
        "can write to that directory."
    )


# -------------------------------------------------------------- verify

@app.command()
def verify(
    baseline: Path = typer.Option(..., "--baseline", "-b"),
    expect: str = typer.Option(
        None, "--expect",
        help=f"Expected baseline digest. Falls back to ${ENV_EXPECT}.",
    ),
):
    """Re-hash the baseline and compare it against its manifest."""
    expect = expect or os.environ.get(ENV_EXPECT)
    try:
        result = do_verify(baseline, expect)
    except SealError as e:
        _err(str(e))
        raise typer.Exit(EXIT_ERROR) from None

    if not result.ok:
        _err(f"BASELINE SEAL BROKEN — {result.describe()}")
        _err("Do not run anything against this baseline. Re-capture it from the "
             "database and re-seal, or restore the sealed copy you trust.")
        raise typer.Exit(EXIT_ERROR) from None

    _ok(result.describe())
    if not expect:
        _warn(f"No expected digest supplied — set --expect or ${ENV_EXPECT} to make "
              f"this check meaningful against directory tampering.")
    typer.echo(result.seal.digest)


# --------------------------------------------------------------- check

@app.command()
def check(
    baseline: Path = typer.Option(..., "--baseline", "-b",
                                  help=f"Sealed directory containing {CATALOG_NAME}."),
    live: Path = typer.Option(..., "--live", "-l",
                              help=f"Freshly captured {CATALOG_NAME} (file or directory)."),
    policy: Path = typer.Option("drift-policy.yml", "--policy", "-p"),
    expect: str = typer.Option(None, "--expect"),
    report_path: Path = typer.Option(None, "--report",
                                     help="Write a self-contained HTML report here."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable verdict on stdout."),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as failures."),
    skip_seal: bool = typer.Option(
        False, "--skip-seal-check",
        help="Skip baseline verification. Recorded in the ledger as an unverified run.",
    ),
):
    """Compare a live catalog against the sealed baseline and apply the policy."""
    ledger = _open_ledger()
    expect = expect or os.environ.get(ENV_EXPECT)

    # 1. the baseline must be trustworthy before anything else happens
    digest = "unverified"
    if skip_seal:
        _warn("Baseline seal check skipped (--skip-seal-check).")
        ledger.record("seal_check", str(baseline), meta={"skipped": True},
                      outcome="skipped")
    else:
        try:
            vr = do_verify(baseline, expect)
        except SealError as e:
            _err(str(e))
            ledger.record("seal_check", str(baseline), payload=str(e), outcome="error")
            raise typer.Exit(EXIT_ERROR) from None
        if not vr.ok:
            _err(f"BASELINE SEAL BROKEN — {vr.describe()}")
            ledger.record("seal_check", str(baseline), payload=vr.describe(),
                          outcome="broken")
            raise typer.Exit(EXIT_ERROR) from None
        digest = vr.seal.digest

    # 2. load both catalogs and the policy
    base_file = baseline / CATALOG_NAME if baseline.is_dir() else baseline
    live_file = live / CATALOG_NAME if live.is_dir() else live
    try:
        base_cat = load_catalog(base_file)
        live_cat = load_catalog(live_file)
        pol = Policy.from_file(policy)
    except (CatalogError, PolicyError) as e:
        _err(str(e))
        ledger.record("check", str(live_file), payload=str(e), outcome="error")
        raise typer.Exit(EXIT_ERROR) from None

    # 3. detect, then judge — two separate steps, deliberately
    changes = diff_catalogs(base_cat, live_cat)
    verdicts = pol.evaluate(changes)
    counts = summarise(verdicts)
    status = overall(verdicts)
    if strict and status == "WARN":
        status = "FAIL"

    ledger.record(
        "check",
        target=str(live_file),
        payload={"baseline_digest": digest, "status": status},
        meta={"changes": len(changes), **counts,
              "policy": str(policy), "strict": strict},
        outcome=status.lower(),
    )

    if report_path:
        note = (
            f"audit: {ledger.db_path}"
            + (" (HMAC-chained)" if ledger.hmac_chained else " (SHA-256 chain)")
            if ledger.enabled
            else "audit: not enabled for this run"
        )
        html = render(
            verdicts,
            baseline_digest=digest,
            baseline_path=str(base_file),
            live_path=str(live_file),
            generated_at=_now(),
            ledger_note=note,
        )
        write(report_path, html)
        _warn(f"Report written to {report_path} — open it and read it yourself.")

    if json_out:
        typer.echo(json.dumps({
            "status": status,
            "baseline_digest": digest,
            "counts": counts,
            "changes": [
                {
                    "kind": v.change.kind,
                    "target": v.change.target,
                    "before": v.change.before,
                    "after": v.change.after,
                    "detail": v.change.detail,
                    "severity": v.severity.value,
                    "watched": v.watched,
                    "reason": v.reason,
                }
                for v in verdicts if v.severity is not Severity.IGNORE
            ],
        }, indent=2))
    else:
        for v in verdicts:
            if v.severity is Severity.IGNORE:
                continue
            line = f"{v.severity.value.upper():5} {v.change.kind:22} {v.change.target}"
            if v.change.before or v.change.after:
                line += f"  {v.change.before or ''} -> {v.change.after or ''}"
            if v.watched:
                line += "   [WATCHED]"
            (typer.secho(line, fg=typer.colors.RED) if v.severity is Severity.FAIL
             else typer.secho(line, fg=typer.colors.YELLOW))

    if status == "FAIL":
        _err(f"\nFAIL — {counts['fail']} breaking change(s). Nothing downstream should run.")
        raise typer.Exit(EXIT_DRIFT)
    if status == "WARN":
        _warn(f"\nWARN — {counts['warn']} change(s) to review. Exit 0; use --strict to fail.")
        raise typer.Exit(EXIT_OK)

    # Silence on success is the design. Nothing to say means nothing moved.
    raise typer.Exit(EXIT_OK)


# ------------------------------------------------------- explain-policy

@app.command("explain-policy")
def explain_policy(
    policy: Path = typer.Option("drift-policy.yml", "--policy", "-p"),
):
    """Print how each change kind will be treated. Read this before trusting a run."""
    try:
        pol = Policy.from_file(policy)
    except PolicyError as e:
        _err(str(e))
        raise typer.Exit(EXIT_ERROR) from None

    from .catalog import (
        COLUMN_ADDED,
        COLUMN_DROPPED,
        NULLABLE_ADDED,
        NULLABLE_REMOVED,
        PII_ADDED,
        PK_CHANGED,
        ROW_COUNT_SHIFT,
        TABLE_ADDED,
        TABLE_DROPPED,
    )
    from .types import TypeChange

    kinds = [TABLE_DROPPED, TABLE_ADDED, COLUMN_DROPPED, COLUMN_ADDED,
             TypeChange.NARROWED.value, TypeChange.WIDENED.value,
             TypeChange.FAMILY_CHANGED.value, TypeChange.UNKNOWN.value,
             NULLABLE_ADDED, NULLABLE_REMOVED, PK_CHANGED, PII_ADDED,
             ROW_COUNT_SHIFT]

    typer.echo(f"policy: {policy}\n")
    for k in kinds:
        if k in pol.fail_on:
            sev, why = "FAIL ", "fail_on"
        elif k in pol.warn_on:
            sev, why = "WARN ", "warn_on"
        else:
            sev, why = pol.default_severity.value.upper().ljust(5), "unclassified default"
        typer.echo(f"  {sev}  {k:24} ({why})")

    if pol.row_count_threshold is not None:
        typer.echo(f"\n  row-count shifts below {pol.row_count_threshold:g}% are ignored")
    if pol.ignore_tables or pol.ignore_columns:
        typer.echo(f"  ignoring tables: {pol.ignore_tables or '-'}")
        typer.echo(f"  ignoring columns: {pol.ignore_columns or '-'}")
    if pol.watch:
        typer.echo("\n  watch list — ANY change to these fails, overriding everything above:")
        for t, cols in sorted(pol.watch.items()):
            typer.echo(f"    {t}: {', '.join(cols) if cols else '(entire table)'}")
    else:
        typer.echo("\n  watch list is empty — nothing is specially protected.")


def main() -> None:  # pragma: no cover
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":  # pragma: no cover
    main()
