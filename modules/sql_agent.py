"""Natural language to SQL query agent. Uses schema registry + pre-built query library.

Part of the Governed Agent Stack: generated SQL is linted by sql-sop before it
runs, and every step is written to the audit log (and, when agent-blackbox is
installed, to a tamper-evident hash-chained ledger).
"""
import time

import pandas as pd
import streamlit as st

from modules import audit_log
from modules.database import get_engine
from modules.llm import get_response
from modules.monitoring import capture_exception
from modules.query_library import find_matching_query
from modules.schema_registry import get_prompt_for_question
from modules.sop_lint import lint as sop_lint


@st.cache_data(ttl=300, show_spinner=False)
def _cached_sql_query(sql):
    """Cache SQL query results for 5 minutes to avoid re-running identical queries."""
    engine = get_engine()
    return pd.read_sql(sql, engine)


EXPLAIN_PROMPT = """Explain these SQL results to a manager in 2-3 sentences. Use GBP and kg. Flag problems. Be concise."""


def _explain(prompt, df):
    """Explain results via the LLM, falling back to a plain summary if the LLM
    is unreachable, so a prebuilt query still returns its data."""
    try:
        return get_response(prompt, system_prompt=EXPLAIN_PROMPT)
    except Exception:
        n = 0 if df is None else len(df)
        return f"{n} rows returned. (LLM explanation unavailable.)"


def _sop_guard(sql):
    """Run the sql-sop lint layer over a query.

    Records findings to the audit log and returns a blocking result dict when
    sql-sop reports an error-severity finding, or None when the query may run.
    """
    sop = sop_lint(sql)
    if sop.errors or sop.warnings:
        audit_log.log_validation(
            passed=not sop.errors,
            lint_findings=sop.errors + sop.warnings,
        )
    if sop.errors:
        return {
            'sql': sql,
            'data': None,
            'explanation': 'Blocked by sql-sop: ' + '; '.join(sop.errors),
            'error': True,
        }
    return None


def run_query(question):
    """Convert natural language to SQL, execute, and explain results."""
    audit_log.log_question(question)
    try:
        # Step 0: Check pre-built query library first (guaranteed correct SQL)
        prebuilt_sql, prebuilt_desc = find_matching_query(question)
        if prebuilt_sql:
            sql = prebuilt_sql.strip()
            audit_log.log_sql_generated(sql, 'library', source='library')
            blocked = _sop_guard(sql)
            if blocked:
                return blocked
            t0 = time.perf_counter()
            try:
                df = _cached_sql_query(sql)
                audit_log.log_execution(
                    sql, row_count=len(df), duration_ms=(time.perf_counter() - t0) * 1000
                )
                if df.empty:
                    explanation = f'{prebuilt_desc}. No data found for the current period.'
                else:
                    data_summary = df.head(20).to_string()
                    prompt = f"Question: {question}\n\nResults:\n{data_summary}\n\nExplain:"
                    explanation = _explain(prompt, df)
                return {'sql': sql, 'data': df, 'explanation': explanation, 'error': False}
            except Exception as e:
                audit_log.log_execution(
                    sql, row_count=0, duration_ms=(time.perf_counter() - t0) * 1000, error=str(e)
                )
                capture_exception(e)
                return {'sql': sql, 'data': None, 'explanation': f'Query error: {e}', 'error': True}

        # Step 1: No pre-built match -- use LLM to generate SQL
        sql_prompt = get_prompt_for_question(question)
        sql = get_response(question, system_prompt=sql_prompt)

        # Clean markdown formatting
        sql = sql.strip()
        if sql.startswith('```'):
            sql = sql.split('\n', 1)[1] if '\n' in sql else sql[3:]
        if sql.endswith('```'):
            sql = sql[:-3]
        sql = sql.strip()
        if sql.lower().startswith('sql'):
            sql = sql[3:].strip()

        audit_log.log_sql_generated(sql, 'unknown', source='llm')

        # Safety: only allow SELECT and WITH (CTEs)
        first_word = sql.upper().strip().split()[0] if sql.strip() else ''
        if first_word not in ('SELECT', 'WITH'):
            audit_log.log_validation(passed=False, error='non-read-only statement')
            return {
                'sql': sql,
                'data': None,
                'explanation': 'For safety, FloorMind only runs read-only queries (SELECT). Please rephrase your question.',
                'error': True
            }

        # Block dangerous keywords
        dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 'EXEC', 'EXECUTE', 'xp_', 'sp_']
        sql_upper = sql.upper()
        for kw in dangerous:
            if kw in sql_upper:
                audit_log.log_validation(passed=False, error=f'blocked keyword: {kw}')
                return {
                    'sql': sql,
                    'data': None,
                    'explanation': f'Blocked: query contains "{kw}". FloorMind is read-only.',
                    'error': True
                }

        # Layer: sql-sop static lint (Governed Agent Stack)
        blocked = _sop_guard(sql)
        if blocked:
            return blocked

        # Step 3: Execute
        t0 = time.perf_counter()
        try:
            engine = get_engine()
            df = pd.read_sql(sql, engine)
            audit_log.log_execution(
                sql, row_count=len(df), duration_ms=(time.perf_counter() - t0) * 1000
            )
        except Exception as e:
            audit_log.log_execution(
                sql, row_count=0, duration_ms=(time.perf_counter() - t0) * 1000, error=str(e)
            )
            capture_exception(e)
            return {
                'sql': sql,
                'data': None,
                'explanation': f'SQL error: {e}. Try rephrasing your question.',
                'error': True
            }

        # Step 4: Explain
        if df.empty:
            explanation = 'No data found. Try adjusting the date range or search terms.'
        else:
            data_summary = df.head(20).to_string()
            prompt = f"Question: {question}\n\nSQL: {sql}\n\nResults:\n{data_summary}\n\nExplain:"
            explanation = _explain(prompt, df)

        return {
            'sql': sql,
            'data': df,
            'explanation': explanation,
            'error': False
        }
    except Exception as e:
        capture_exception(e)
        raise
