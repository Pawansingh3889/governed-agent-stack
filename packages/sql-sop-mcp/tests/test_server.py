"""Smoke tests for the two MCP tools.

The MCP transport itself isn't exercised here -- FastMCP's own test suite covers that.
These tests pin the contract of what `lint_sql` and `list_rules` return so the LLM
that calls them gets a stable shape.
"""

from __future__ import annotations

from sql_sop_mcp.server import lint_sql, list_rules


# ---------------------------------------------------------------------------
# lint_sql
# ---------------------------------------------------------------------------


def test_lint_sql_flags_delete_without_where():
    result = lint_sql("DELETE FROM orders;")
    assert result["passed"] is False
    rule_ids = {f["rule_id"] for f in result["findings"]}
    assert "E001" in rule_ids


def test_lint_sql_flags_select_star():
    result = lint_sql("SELECT * FROM users;")
    rule_ids = {f["rule_id"] for f in result["findings"]}
    assert "W001" in rule_ids


def test_lint_sql_returns_findings_in_documented_shape():
    result = lint_sql("SELECT * FROM users;")
    assert "passed" in result
    assert "summary" in result
    assert "findings" in result
    for f in result["findings"]:
        assert {"rule_id", "severity", "line", "message", "suggestion"} <= set(f.keys())
        assert f["severity"] in ("error", "warning")
        assert isinstance(f["line"], int)


def test_lint_sql_disable_skips_listed_rules():
    result = lint_sql("SELECT * FROM users;", disable=["W001"])
    rule_ids = {f["rule_id"] for f in result["findings"]}
    assert "W001" not in rule_ids


def test_lint_sql_disable_is_case_insensitive():
    result = lint_sql("SELECT * FROM users;", disable=["w001"])
    rule_ids = {f["rule_id"] for f in result["findings"]}
    assert "W001" not in rule_ids


def test_lint_sql_severity_error_drops_warnings():
    sql = "SELECT * FROM users; DELETE FROM orders;"
    result = lint_sql(sql, severity="error")
    assert result["findings"], "expected at least one error"
    assert all(f["severity"] == "error" for f in result["findings"])


def test_lint_sql_passes_clean_query():
    sql = "SELECT id, name FROM users WHERE id = 1 LIMIT 10;"
    result = lint_sql(sql, severity="error")
    assert result["passed"] is True


# ---------------------------------------------------------------------------
# list_rules
# ---------------------------------------------------------------------------


def test_list_rules_returns_count_and_rules_keys():
    result = list_rules()
    assert "count" in result
    assert "rules" in result
    assert result["count"] == len(result["rules"])


def test_list_rules_returns_at_least_the_known_rule_count():
    # sql-sop v0.6.1 ships 33 SQL + 5 Python = 38 rules. New releases may add more.
    result = list_rules()
    assert result["count"] >= 38


def test_list_rules_includes_t_sql_safety_rules():
    result = list_rules()
    rule_ids = {r["id"] for r in result["rules"]}
    # T001 with-nolock and T005 create-index-without-online are signature T-SQL rules.
    assert "T001" in rule_ids
    assert "T005" in rule_ids


def test_list_rules_each_entry_has_documented_shape():
    result = list_rules()
    for r in result["rules"]:
        assert {"id", "name", "severity", "description"} <= set(r.keys())
        assert r["severity"] in ("error", "warning")
