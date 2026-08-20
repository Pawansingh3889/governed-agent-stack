#!/usr/bin/env python3
"""A governance gateway in front of an OpenAI-compatible LLM.

The model can *say* anything. This gateway sits between the model and the
database and decides what is allowed to run:

    you --(natural language)--> gateway --> LLM (OpenAI API)
                                   |                |
                                   |          (model writes SQL)
                                   v                |
                            sql_guard policy <------+
                                   |
                        allow (SELECT) / refuse (writes, DDL)
                                   |
                                   v
                        append-only, hash-chained ledger

Every decision leaves a receipt you can verify.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LEDGER = Path(__file__).with_name("ledger.jsonl")

# The same policy shape as the sql_guard demo: reads pass, writes and DDL die.
BLOCKED = {"insert", "update", "delete", "drop", "alter", "truncate", "create", "grant"}


def verb(statement: str) -> str:
    m = re.match(r"\s*([a-zA-Z]+)", statement)
    return m.group(1).lower() if m else ""


def judge(statement: str) -> tuple[bool, str]:
    """Return (allowed, reason) for a SQL statement."""
    v = verb(statement)
    if v == "select":
        return True, "read-only statement"
    if v in BLOCKED:
        return False, f'statement verb "{v}" is not permitted by sql_guard'
    return False, f'unrecognised verb "{v or "?"}", the gate fails closed'


def ask_model(request: str, model: str) -> str:
    """Ask the model to turn a request into a single SQL statement."""
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    prompt = (
        "You are a SQL generator. Reply with ONE SQL statement only, no prose, "
        "no explanation, no markdown fences. Request: " + request
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
    )
    text = response.choices[0].message.content or ""
    return _extract_sql(text)


def _extract_sql(text: str) -> str:
    """Pull the first SQL-looking statement out of a model response."""
    text = re.sub(r"```[a-zA-Z]*", "", text).replace("```", "").strip()
    keywords = "|".join(BLOCKED | {"select", "with"})
    m = re.search(rf"(?is)\b({keywords})\b.*?(;|$)", text)
    return m.group(0).strip().rstrip(";") if m else text.splitlines()[0].strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ledger_append(request: str, sql: str, allowed: bool, reason: str) -> dict:
    """Append a hash-chained record. Each hash covers the previous hash, so
    editing any past entry breaks the chain from that point forward."""
    prev = "0" * 64
    if LEDGER.exists():
        lines = LEDGER.read_text(encoding="utf-8").splitlines()
        if lines:
            prev = json.loads(lines[-1])["hash"]
    entry = {
        "ts": _now(),
        "request": request,
        "sql": sql,
        "verdict": "ALLOW" if allowed else "REFUSE",
        "reason": reason,
        "prev_hash": prev,
    }
    payload = json.dumps({k: entry[k] for k in entry if k != "hash"}, sort_keys=True)
    entry["hash"] = hashlib.sha256((prev + payload).encode()).hexdigest()
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def verify_ledger() -> bool:
    """Recompute the chain and confirm no entry was tampered with."""
    if not LEDGER.exists():
        return True
    prev = "0" * 64
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        payload = json.dumps({k: e[k] for k in e if k != "hash"}, sort_keys=True)
        if e["prev_hash"] != prev or hashlib.sha256((prev + payload).encode()).hexdigest() != e["hash"]:
            return False
        prev = e["hash"]
    return True


def run(request: str, model: str = DEFAULT_MODEL) -> None:
    print(f"\nrequest : {request}")
    sql = ask_model(request, model)
    print(f"model   : {sql}")
    allowed, reason = judge(sql)
    verdict = "ALLOW  ✅ (would execute)" if allowed else "REFUSE 🛑 (blocked at the gate)"
    print(f"gateway : {verdict}  — {reason}")
    entry = ledger_append(request, sql, allowed, reason)
    print(f"ledger  : {entry['hash'][:12]}…  (chain {'intact ✅' if verify_ledger() else 'BROKEN ❌'})")


if __name__ == "__main__":
    model = DEFAULT_MODEL
    if len(sys.argv) > 1:
        run(" ".join(sys.argv[1:]), model)
    else:
        # Demo: one safe request, two dangerous ones. Watch the gate.
        for r in [
            "show me total sales by customer",
            "delete every order older than 2020",
            "drop the customers table",
        ]:
            run(r, model)
        print(f"\nfull ledger at {LEDGER}  —  tamper-evident chain verified: {verify_ledger()}")
