"""Core checker — orchestrates file discovery, scanning, and rule execution."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path

from sql_guard.contracts import Contract
from sql_guard.dbt import DbtProject
from sql_guard.rules import get_rules
from sql_guard.rules.base import Finding, Rule
from sql_guard.rules.python_rules import PYTHON_RULES
from sql_guard import python_scanner
from sql_guard.inline_disable import DisableMap, parse as parse_disables


@dataclass
class CheckResult:
    """Aggregated result of checking one or more files."""

    findings: list[Finding] = field(default_factory=list)
    files_checked: int = 0
    files_with_issues: int = 0
    duration_seconds: float = 0.0

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


SKIP_PATTERNS = {"*.min.sql", "*.bak"}
PYTHON_SKIP_DIRS = {".venv", "venv", "__pycache__", "build", "dist", ".tox", ".mypy_cache"}


def discover_files(
    paths: list[str],
    ignore: list[str] | None = None,
    include_python: bool = False,
) -> list[Path]:
    """Find SQL (and optionally Python) files in the given paths."""
    collected: list[Path] = []
    ignore_set = set(ignore or [])
    extensions: tuple[str, ...] = (".sql",)
    if include_python:
        extensions = (".sql", ".py")

    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix in extensions:
            collected.append(path)
        elif path.is_dir():
            for ext in extensions:
                for f in path.rglob(f"*{ext}"):
                    rel = str(f.relative_to(path))
                    if any(f.match(pat) for pat in SKIP_PATTERNS):
                        continue
                    if any(part in rel for part in ignore_set):
                        continue
                    if ext == ".py" and any(skip in f.parts for skip in PYTHON_SKIP_DIRS):
                        continue
                    collected.append(f)

    return sorted(set(collected))


def _split_statements(content: str) -> list[tuple[int, str]]:
    """Split SQL content into statements with their starting line numbers.

    Splits on every real statement-terminating ``;`` -- including several
    statements written on a single line -- while ignoring ``;`` inside
    string literals, line comments, and block comments. A run of blank
    or comment-only lines before a statement is skipped, matching the
    line number of the first real token. Returns list of
    (start_line, statement_text).
    """
    statements: list[tuple[int, str]] = []
    buf: list[str] = []
    line_no = 1
    start_line: int | None = None
    in_string = False
    in_line_comment = False
    in_block_comment = False

    def emit(ch: str) -> None:
        if start_line is not None:
            buf.append(ch)

    i = 0
    n = len(content)
    while i < n:
        ch = content[i]
        nxt = content[i + 1] if i + 1 < n else ""

        if in_line_comment:
            emit(ch)
            if ch == "\n":
                in_line_comment = False
                line_no += 1
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                emit(ch)
                emit(nxt)
                i += 2
                continue
            emit(ch)
            if ch == "\n":
                line_no += 1
            i += 1
            continue

        if in_string:
            if ch == "'" and nxt == "'":
                emit(ch)
                emit(nxt)
                i += 2
                continue
            emit(ch)
            if ch == "'":
                in_string = False
            elif ch == "\n":
                line_no += 1
            i += 1
            continue

        if ch == "-" and nxt == "-":
            in_line_comment = True
            emit(ch)
            i += 1
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            emit(ch)
            i += 1
            continue

        if ch == "'":
            in_string = True
            if start_line is None:
                start_line = line_no
            buf.append(ch)
            i += 1
            continue

        if ch == ";":
            if start_line is not None:
                buf.append(ch)
                statements.append((start_line, "".join(buf)))
                buf = []
                start_line = None
            i += 1
            continue

        if ch == "\n":
            emit(ch)
            line_no += 1
            i += 1
            continue

        if ch.strip():
            if start_line is None:
                start_line = line_no
            buf.append(ch)
        else:
            emit(ch)
        i += 1

    # Handle last statement without a terminating semicolon
    if buf and "".join(buf).strip() and start_line is not None:
        statements.append((start_line, "".join(buf)))

    return statements


def _file_hash(path: Path) -> str:
    """Fast hash of file content for caching."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def check_file(
    path: Path,
    rules: list[Rule],
    fail_fast: bool = False,
) -> list[Finding]:
    """Check a single SQL file against all rules.

    Uses two-pass strategy:
    1. Single-pass rules: line-by-line (fast)
    2. Multi-line rules: statement-level (only if needed)
    """
    findings: list[Finding] = []
    file_str = str(path)

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = path.read_text(encoding="latin-1")
        except Exception as e:
            return [
                Finding(
                    rule_id="SYS",
                    severity="error",
                    file=file_str,
                    line=0,
                    message=f"Cannot read file: {e}",
                )
            ]
    except PermissionError:
        return [
            Finding(
                rule_id="SYS",
                severity="error",
                file=file_str,
                line=0,
                message="Permission denied",
            )
        ]
    except OSError as e:
        return [
            Finding(
                rule_id="SYS",
                severity="error",
                file=file_str,
                line=0,
                message=f"Cannot read file: {e}",
            )
        ]

    single_pass_rules = [r for r in rules if not r.multiline]
    multi_line_rules = [r for r in rules if r.multiline]
    disables = parse_disables(content)

    # Pass 1: line-by-line rules
    for line_num, line in enumerate(content.splitlines(), 1):
        for rule in single_pass_rules:
            finding = rule.check_line(line, line_num, file_str)
            if finding and not disables.is_disabled(finding.line, finding.rule_id):
                findings.append(finding)
                if fail_fast and finding.severity == "error":
                    return findings

    # Pass 2: statement-level rules
    if multi_line_rules:
        statements = _split_statements(content)
        for start_line, statement in statements:
            for rule in multi_line_rules:
                finding = rule.check_statement(statement, start_line, file_str)
                if finding and not disables.is_disabled(finding.line, finding.rule_id):
                    findings.append(finding)
                    if fail_fast and finding.severity == "error":
                        return findings

    # Pass 3: file-level rules. Default ``check_file`` returns an empty
    # list so line- and statement-rules pay nothing here. File-level
    # rules (e.g. the dbt-aware pack) override it.
    for rule in rules:
        for finding in rule.check_file(file_str):
            if disables.is_disabled(finding.line, finding.rule_id):
                continue
            findings.append(finding)
            if fail_fast and finding.severity == "error":
                return findings

    return findings


def check_python_file(
    path: Path,
    rules: list[Rule],
    disabled_rules: set[str] | None = None,
    fail_fast: bool = False,
) -> list[Finding]:
    """Lint SQL strings embedded in a Python source file.

    The Python-only P-rules always run on what the libCST scanner extracts.
    For concrete string literals, the standard SQL rules also run so that
    DELETE-without-WHERE, SELECT *, etc. are caught inside ``.py`` files.
    """
    findings: list[Finding] = []
    file_str = str(path)

    if not python_scanner.libcst_available():
        findings.append(
            Finding(
                rule_id="SYS",
                severity="warning",
                file=file_str,
                line=0,
                message="Python scanning requested but libcst is not installed",
                suggestion="pip install sql-sop[python]",
            )
        )
        return findings

    try:
        content = path.read_text(encoding="utf-8")
        disables = parse_disables(content)
    except (OSError, UnicodeDecodeError):
        disables = DisableMap()

    hits = python_scanner.extract_from_file(path)
    disabled = disabled_rules or set()

    for hit in hits:
        # Python-only rules fire on every hit.
        for rule in PYTHON_RULES:
            if rule.id in disabled:
                continue
            finding = rule.check(hit, file_str)
            if finding and not disables.is_disabled(finding.line, finding.rule_id):
                findings.append(finding)
                if fail_fast and finding.severity == "error":
                    return findings

        # Standard SQL rules re-run on concrete literals only.
        if hit.kind != "literal" or not hit.sql:
            continue
        for rule in rules:
            if rule.multiline:
                finding = rule.check_statement(hit.sql, hit.line, file_str)
            else:
                # Single-line rules evaluate the whole string as one line.
                finding = rule.check_line(hit.sql, hit.line, file_str)
            if finding and not disables.is_disabled(finding.line, finding.rule_id):
                findings.append(finding)
                if fail_fast and finding.severity == "error":
                    return findings

    return findings


def check(
    paths: list[str],
    severity: str = "warning",
    fail_fast: bool = False,
    disabled_rules: set[str] | None = None,
    ignore: list[str] | None = None,
    include_python: bool = False,
    contract: Contract | None = None,
    dbt_project: "DbtProject | None" = None,  # noqa: F821 -- imported below
) -> CheckResult:
    """Run all rules against discovered SQL (and optionally Python) files.

    Args:
        paths: Files or directories to check.
        severity: Minimum severity to report ("error" or "warning").
        fail_fast: Stop after first error.
        disabled_rules: Set of rule IDs to skip.
        ignore: Path patterns to ignore.
        include_python: Also scan ``.py`` files for embedded SQL via libCST.
        contract: Optional data contract. When provided, contract-aware rules
            (C001-...) are activated and given this contract instance.
        dbt_project: Optional discovered dbt project. When provided,
            dbt-aware rules (DBT001-...) are activated and given this project.

    Returns:
        CheckResult with all findings.
    """
    t0 = time.perf_counter()
    rules = get_rules(disabled_ids=disabled_rules, contract=contract, dbt_project=dbt_project)
    discovered = discover_files(paths, ignore=ignore, include_python=include_python)

    result = CheckResult()
    result.files_checked = len(discovered)

    for path in discovered:
        if path.suffix == ".py":
            file_findings = check_python_file(
                path, rules, disabled_rules=disabled_rules, fail_fast=fail_fast
            )
        else:
            file_findings = check_file(path, rules, fail_fast=fail_fast)

        # Filter by severity
        if severity == "error":
            file_findings = [f for f in file_findings if f.severity == "error"]

        if file_findings:
            result.files_with_issues += 1
            result.findings.extend(file_findings)

            if fail_fast and any(f.severity == "error" for f in file_findings):
                break

    result.duration_seconds = round(time.perf_counter() - t0, 3)
    return result
