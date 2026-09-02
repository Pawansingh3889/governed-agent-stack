"""Tests for the statement splitter in ``sql_guard.checker``."""

from __future__ import annotations

from sql_guard.checker import _split_statements, check


def test_single_statement_unchanged() -> None:
    stmts = _split_statements("SELECT * FROM t\nWHERE a = 1;\n")
    assert stmts == [(1, "SELECT * FROM t\nWHERE a = 1;")]


def test_two_statements_on_one_line_are_split() -> None:
    stmts = _split_statements("DELETE FROM foo; DELETE FROM bar WHERE x=1;\n")
    assert [text for _, text in stmts] == ["DELETE FROM foo;", "DELETE FROM bar WHERE x=1;"]
    assert [line for line, _ in stmts] == [1, 1]


def test_semicolon_inside_string_literal_is_not_a_split_point() -> None:
    stmts = _split_statements("SELECT ';' AS x; SELECT 2;\n")
    assert [text for _, text in stmts] == ["SELECT ';' AS x;", "SELECT 2;"]


def test_semicolon_inside_block_comment_is_not_a_split_point() -> None:
    stmts = _split_statements("SELECT /* block ; comment */ 1;\n")
    assert len(stmts) == 1


def test_leading_comment_and_blank_lines_are_skipped() -> None:
    stmts = _split_statements("-- header\nSELECT 1;\n\nSELECT 2;\n")
    assert stmts == [(2, "SELECT 1;"), (4, "SELECT 2;")]


def test_end_to_end_two_statements_one_line_both_checked(tmp_path) -> None:
    # Regression: a single unguarded DELETE hidden on the same line as a
    # second, safely-guarded DELETE must still be caught. Previously the
    # whole line was merged into one statement, so the second
    # statement's WHERE clause hid the first statement's missing WHERE.
    sql = tmp_path / "two_deletes.sql"
    sql.write_text("DELETE FROM foo; DELETE FROM bar WHERE x=1;\n")
    result = check([str(sql)])
    e001 = [f for f in result.findings if f.rule_id == "E001"]
    assert len(e001) == 1
