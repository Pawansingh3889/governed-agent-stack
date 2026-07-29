#!/usr/bin/env python3
"""Validate every packages/*/server.json against the official MCP schema.

Registry rejections surface at release time, after the PyPI upload has already
happened — too late to fix cheaply. This runs on every PR instead.

It caught sql-explorer-mcp shipping a 166-character description against a
maxLength of 100, which would have failed the first publish from the monorepo.

Offline (no network), the schema fetch is skipped and only the local checks
run, so a CI outage upstream does not block a merge.
"""

from __future__ import annotations

import json
import pathlib
import sys
import urllib.error
import urllib.request

REPO = "https://github.com/Pawansingh3889/governed-agent-stack"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def fetch_schema(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=15) as fh:
            return json.load(fh)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"  ! schema unreachable ({exc}) — running local checks only")
        return None


def main() -> int:
    paths = sorted(ROOT.glob("packages/*/server.json"))
    if not paths:
        print("no server.json files found")
        return 0

    try:
        import jsonschema
    except ImportError:
        print("jsonschema not installed — run via `uv run --with jsonschema`")
        return 2

    failures = []
    schema_cache: dict[str, dict | None] = {}

    for path in paths:
        pkg = path.parent.name
        doc = json.loads(path.read_text())

        # The package's own pyproject is the source of truth for the version;
        # server.json carries a duplicate that drifts silently.
        pyproject = path.parent / "pyproject.toml"
        if pyproject.exists():
            import tomllib

            declared = tomllib.load(pyproject.open("rb"))["project"]["version"]
            versions = [doc.get("version")] + [
                e.get("version") for e in doc.get("packages", [])
            ]
            for got in versions:
                if got != declared:
                    failures.append(
                        f"{pkg}: server.json version {got!r} != pyproject {declared!r}"
                    )

        # The repo moved into this monorepo; a stale URL points at an archive.
        repo = doc.get("repository", {})
        if repo.get("url") != REPO:
            failures.append(f"{pkg}: repository.url is {repo.get('url')!r}, expected {REPO!r}")
        expected_sub = f"packages/{pkg}"
        if repo.get("subfolder") != expected_sub:
            failures.append(
                f"{pkg}: repository.subfolder is {repo.get('subfolder')!r}, "
                f"expected {expected_sub!r}"
            )

        url = doc.get("$schema")
        if url:
            if url not in schema_cache:
                schema_cache[url] = fetch_schema(url)
            schema = schema_cache[url]
            if schema is not None:
                try:
                    jsonschema.validate(doc, schema)
                except jsonschema.ValidationError as exc:
                    where = ".".join(str(p) for p in exc.absolute_path) or "(root)"
                    failures.append(f"{pkg}: {where}: {exc.message}")

        if not [f for f in failures if f.startswith(f"{pkg}:")]:
            print(f"  ok   {pkg}")

    if failures:
        print("\nserver.json validation failed:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"\n{len(paths)} server.json files valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
