"""Model Context Protocol server that exposes sql-sop's linter as LLM-callable tools.

Two tools:
* ``lint_sql`` runs sql-sop against a SQL string and returns structured findings.
* ``list_rules`` returns the catalogue of every rule sql-sop ships with.

Designed for Claude Desktop, Cursor, ChatGPT desktop, Continue, and any other
MCP client. Communication happens over stdio so no network listener is opened.
"""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field
from sql_guard import SqlGuard

mcp = FastMCP(
    name="sql-sop",
    instructions=(
        "Lint SQL for safety issues before suggesting it to a user. "
        "Use lint_sql when generating or reviewing SQL; reject or rewrite anything "
        "that comes back with severity=error. Use list_rules to discover the rule "
        "catalogue if you need to explain a finding."
    ),
)


@mcp.tool(
    description=(
        "Lint a SQL string with sql-sop. Catches dangerous patterns "
        "(DELETE/UPDATE without WHERE, SQL injection via string concat, "
        "DROP COLUMN, ADD NOT NULL without DEFAULT), SARGability mistakes "
        "(function on indexed column, leading-wildcard LIKE, OR across columns), "
        "5 T-SQL specific rules (NOLOCK, xp_cmdshell, deprecated outer join, etc.), "
        "and 5 Python source rules for sqlalchemy.text() / cursor.execute() injection. "
        "38 rules in total. Returns one JSON object listing every finding plus a "
        "human-readable summary."
    )
)
def lint_sql(
    sql: Annotated[
        str, Field(description="The SQL string to lint. Can be one or many statements.")
    ],
    severity: Annotated[
        str,
        Field(
            description="Minimum severity to report. 'error' returns only blocking issues; "
            "'warning' returns everything (default).",
            examples=["warning", "error"],
        ),
    ] = "warning",
    disable: Annotated[
        list[str] | None,
        Field(
            description="Rule IDs to skip for this call, e.g. ['W001', 'T001']. "
            "Useful when the LLM knows a specific finding is a false positive in context.",
            examples=[["W001"], ["T001", "W008"]],
        ),
    ] = None,
) -> dict:
    guard = SqlGuard()
    if disable:
        guard = guard.disable(*[r.upper() for r in disable])
    if severity == "error":
        guard = guard.severity("error")
    result = guard.scan(sql)

    findings = [
        {
            "rule_id": f.rule_id,
            "severity": f.severity,
            "line": f.line,
            "message": f.message,
            "suggestion": f.suggestion or "",
        }
        for f in result.findings
    ]

    summary = (
        result.summary()
        if hasattr(result, "summary") and callable(result.summary)
        else f"{len(findings)} finding(s)"
    )

    return {
        "passed": getattr(result, "passed", len([f for f in findings if f["severity"] == "error"]) == 0),
        "summary": summary,
        "findings": findings,
    }


@mcp.tool(
    description=(
        "List every rule sql-sop ships with. Useful for explaining a finding's full "
        "description, picking which rules to disable for a project, or for an LLM to "
        "discover what it can use lint_sql to catch."
    )
)
def list_rules() -> dict:
    from sql_guard.rules import ALL_RULES
    from sql_guard.rules.python_rules import PYTHON_RULES

    rules = []
    for r in [*ALL_RULES, *PYTHON_RULES]:
        rules.append(
            {
                "id": r.id,
                "name": r.name,
                "severity": r.severity,
                "description": r.description,
            }
        )
    return {"count": len(rules), "rules": rules}


def main() -> None:
    """Console-script entry point. Runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
