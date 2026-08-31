"""AI descriptions via OpenAI-compatible API.

This is the differentiated layer: feed each table's structure + profile +
sample values to a *local* LLM and get back plain-English descriptions that
make the catalog searchable and feed a NL->SQL retriever. Use an OpenAI-
compatible endpoint (local proxy like LiteLLM or the real API) so no schema
or sample data leaves the machine when running on-prem.

``requests`` and an OpenAI-compatible endpoint are only needed for
``describe_*``; prompt building is pure and testable.
"""
from __future__ import annotations

import json
import os

from schema_scout.model import Table

_SYSTEM = (
    "You are a data analyst documenting a database for other analysts. "
    "Be concise and factual. Do not invent columns or meanings you cannot "
    "infer from the names, types and sample values given."
)


def build_describe_prompt(table: Table, max_cols: int = 60) -> str:
    """Build a prompt asking for a table description + per-column one-liners.

    Asks for strict JSON back so the result is machine-parseable.
    """
    lines = [
        f"Table: {table.qualified_name}",
        f"Role (heuristic): {table.kind}",
        f"Approx rows: {table.row_count:,}",
        f"Primary key: {', '.join(table.primary_key) or 'none declared'}",
        "",
        "Columns (name | type | sample values):",
    ]
    for c in table.columns[:max_cols]:
        samples = ", ".join(c.sample_values[:5]) if c.sample_values else ""
        pk = " [PK]" if c.is_primary_key else ""
        lines.append(f"- {c.name} | {c.data_type}{pk} | {samples}")
    if table.foreign_keys:
        lines.append("")
        lines.append("Relationships:")
        for fk in table.foreign_keys:
            lines.append(
                f"- {fk.parent_column} -> {fk.ref_table}.{fk.ref_column}"
            )
    lines.append("")
    lines.append(
        "Respond with JSON only, no prose, in exactly this shape:\n"
        '{"table": "one sentence on what this table holds", '
        '"columns": {"<column_name>": "short meaning", ...}}'
    )
    return "\n".join(lines)


def describe_table(
    table: Table,
    model: str = None,
    host: str = None,
    timeout: int = 120,
) -> dict:
    """Call an OpenAI-compatible model and apply the descriptions to ``table``.

    Args:
        table: The table to describe.
        model: Model name (default: OPENAI_MODEL env or gpt-4o).
        host: Base URL for OpenAI-compatible API (default: OPENAI_BASE_URL env).
        timeout: Request timeout in seconds.

    Returns the parsed dict. On any failure returns {} and leaves the table
    untouched, so a bad/absent model never breaks a catalog run.
    """
    from openai import OpenAI

    model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = host or os.getenv("OPENAI_BASE_URL")

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    prompt = build_describe_prompt(table)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
    except Exception:
        return {}

    if isinstance(parsed.get("table"), str):
        table.description = parsed["table"].strip()
    col_desc = parsed.get("columns", {})
    if isinstance(col_desc, dict):
        for c in table.columns:
            d = col_desc.get(c.name)
            if isinstance(d, str) and d.strip():
                c.description = d.strip()
    return parsed
