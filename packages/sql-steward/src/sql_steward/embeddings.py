"""Optional embedding generation for semantic_search.

Off by default. Point ``SQL_STEWARD_EMBED_URL`` at an OpenAI-compatible API
endpoint and set ``SQL_STEWARD_EMBED_MODEL``. Keeps the on-prem promise when
used with a local proxy (e.g. LiteLLM). Returns None if not configured or
unreachable, so the caller can refuse cleanly.
"""
from __future__ import annotations

import json
import os
import urllib.request


def embed(text: str) -> list[float] | None:
    url = os.environ.get("SQL_STEWARD_EMBED_URL")
    if not url:
        return None
    model = os.environ.get("SQL_STEWARD_EMBED_MODEL", "text-embedding-3-small")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    try:
        payload = json.dumps({"model": model, "input": text}).encode("utf-8")
        req = urllib.request.Request(
            url.rstrip("/") + "/v1/embeddings",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        emb = None
        if isinstance(data.get("data"), list) and data["data"]:
            emb = data["data"][0].get("embedding")
        return [float(x) for x in emb] if emb else None
    except Exception:
        return None
