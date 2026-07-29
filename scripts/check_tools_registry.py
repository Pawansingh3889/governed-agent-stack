#!/usr/bin/env python3
"""Validate apps/control-tower/tools.yaml against the contract in REGISTRY.md.

control-tower's registry is the one file that has to describe *this* machine
correctly. The failure mode it replaced was a registry full of paths from
another host: every entry parsed, nothing resolved, and the page showed a wall
of dead dots that looked like broken services rather than a stale file.

So this checks the things a YAML parser cannot:

  * no path from another operating system survived a move
  * every run.cmd names a console script some package actually declares
  * every metric reads a source the tower knows how to read, from a path
    inside this tree
  * ports are unique, groups are real, and the service/artifact split holds

Run it directly (`python3 scripts/check_tools_registry.py`) or via `make check`.
Exits 0 when the registry is consistent, 1 with one line per problem when not.
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(
        "PyYAML is needed to read the registry.\n"
        "  uv run --with pyyaml python scripts/check_tools_registry.py\n"
        "  (or `make check`, which does that for you)"
    )

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "apps" / "control-tower" / "tools.yaml"

TIERS = {"service", "artifact"}
CHECK_TYPES = {"http", "tcp"}
METRIC_SOURCES = {"sqlite", "json_file"}
GATEWAY_FLAVORS = {"fastmcp", "mcp-sdk"}

# Paths that mean the registry was written for a machine that is not this one.
# The lookbehind keeps `http://` from reading as a `p:` drive letter: a real
# drive letter stands alone, a URL scheme has letters in front of the colon.
FOREIGN_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|\bwsl(\.exe)?\s|\\\\wsl\$")

problems: list[str] = []


def fail(where: str, msg: str) -> None:
    problems.append(f"{where}: {msg}")


def console_scripts() -> dict[str, str]:
    """Every console script the workspace declares, mapped to its package."""
    found = {}
    for pyproject in sorted(ROOT.glob("packages/*/pyproject.toml")):
        data = tomllib.loads(pyproject.read_text())
        for script in data.get("project", {}).get("scripts", {}):
            found[script] = pyproject.parent.name
    return found


def check_run(tool_id: str, run: dict, scripts: dict[str, str]) -> None:
    where = f"{tool_id}.run"
    cmd = run.get("cmd")
    if not cmd:
        fail(where, "missing `cmd`")
        return

    cwd = run.get("cwd")
    if cwd and not (ROOT / cwd).is_dir():
        fail(where, f"cwd {cwd!r} is not a directory in this tree")

    parts = cmd.split()
    if parts[:2] == ["uv", "run"]:
        # `uv run --project <path> <console-script> [args]`
        if "--project" not in parts:
            fail(where, "a `uv run` command must pass --project so it resolves "
                        "against the workspace rather than an ambient venv")
            return
        project = parts[parts.index("--project") + 1]
        if not (ROOT / project).is_dir():
            fail(where, f"--project {project!r} is not a directory in this tree")
        script = parts[parts.index("--project") + 2]
        if script not in scripts:
            fail(where, f"{script!r} is not a console script any package declares "
                        f"(known: {', '.join(sorted(scripts))})")
    else:
        # A bare command run from `cwd`, e.g. `streamlit run app.py`. Check any
        # argument that looks like a file in the tree really is one.
        base = ROOT / (cwd or ".")
        for arg in parts[1:]:
            if arg.endswith(".py") and not (base / arg).is_file():
                fail(where, f"{arg!r} does not exist under {cwd or '.'}")


def check_metric(tool_id: str, i: int, metric: dict) -> None:
    where = f"{tool_id}.metrics[{i}]"
    for field in ("label", "source", "path"):
        if not metric.get(field):
            fail(where, f"missing `{field}`")
    source, path = metric.get("source"), metric.get("path")

    if source not in METRIC_SOURCES:
        fail(where, f"source {source!r} is not one of {sorted(METRIC_SOURCES)}")
    elif source == "sqlite" and not metric.get("query"):
        fail(where, "a sqlite metric needs a `query`")
    elif source == "json_file" and not metric.get("key"):
        fail(where, "a json_file metric needs a `key`")

    if not path:
        return
    if Path(path).is_absolute() or ".." in Path(path).parts:
        fail(where, f"path {path!r} must be relative to the repo root and stay "
                    "inside the tree — the tower is not portable otherwise")
    elif not metric.get("optional") and not (ROOT / path).exists():
        fail(where, f"path {path!r} does not exist. Mark it `optional: true` if "
                    "it only appears after the tool has run once")


def check_tool(tool: dict, seen_ids: set, seen_ports: dict, groups: list,
               scripts: dict[str, str]) -> None:
    tool_id = tool.get("id")
    if not tool_id:
        fail("<tool>", "missing `id`")
        return
    if tool_id in seen_ids:
        fail(tool_id, "duplicate id")
    seen_ids.add(tool_id)

    for field in ("name", "group", "tier", "desc", "run"):
        if not tool.get(field):
            fail(tool_id, f"missing `{field}`")

    if (group := tool.get("group")) and group not in groups:
        fail(tool_id, f"group {group!r} is not declared in the top-level `groups`")

    tier = tool.get("tier")
    if tier and tier not in TIERS:
        fail(tool_id, f"tier {tier!r} is not one of {sorted(TIERS)}")

    port, check = tool.get("port"), tool.get("check")
    if tier == "service":
        if not port:
            fail(tool_id, "a service needs a `port`")
        if not check:
            fail(tool_id, "a service needs a `check`, or the tower cannot tell "
                          "whether it is up")
    elif tier == "artifact" and (port or check):
        fail(tool_id, "an artifact produces output rather than serving it, so it "
                      "should declare neither `port` nor `check`")

    if port:
        if port in seen_ports:
            fail(tool_id, f"port {port} is already taken by {seen_ports[port]!r}")
        seen_ports[port] = tool_id

    if check:
        ctype = check.get("type")
        if ctype not in CHECK_TYPES:
            fail(tool_id, f"check type {ctype!r} is not one of {sorted(CHECK_TYPES)}")
        elif ctype == "tcp" and check.get("port") != port:
            fail(tool_id, f"tcp check port {check.get('port')} does not match the "
                          f"tool's port {port}")
        elif ctype == "http" and not check.get("url"):
            fail(tool_id, "an http check needs a `url`")

    if isinstance(tool.get("run"), dict):
        check_run(tool_id, tool["run"], scripts)

    metrics = tool.get("metrics")
    if metrics is None:
        fail(tool_id, "missing `metrics` (use an empty list if there is nothing "
                      "to read yet — silence and omission should not look alike)")
    else:
        for i, metric in enumerate(metrics):
            check_metric(tool_id, i, metric)

    if gateway := tool.get("gateway"):
        where = f"{tool_id}.gateway"
        if tier != "service":
            fail(where, "only a service is fronted by the gateway")
        if gateway.get("flavor") not in GATEWAY_FLAVORS:
            fail(where, f"flavor {gateway.get('flavor')!r} is not one of "
                        f"{sorted(GATEWAY_FLAVORS)}")
        if not gateway.get("module"):
            fail(where, "missing `module`")
        if (req := gateway.get("requires")) and Path(req).is_absolute():
            fail(where, f"requires {req!r} must be relative to the repo root")


def main() -> int:
    if not REGISTRY.is_file():
        print(f"error: {REGISTRY.relative_to(ROOT)} does not exist", file=sys.stderr)
        return 1

    raw = REGISTRY.read_text()
    for lineno, line in enumerate(raw.splitlines(), 1):
        if FOREIGN_PATH.search(line):
            fail(f"line {lineno}", f"path from another machine: {line.strip()!r}")

    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        print(f"error: {REGISTRY.relative_to(ROOT)} is not valid YAML: {e}", file=sys.stderr)
        return 1

    groups = doc.get("groups") or []
    if not groups:
        fail("<root>", "missing `groups`")
    tools = doc.get("tools")
    if not tools:
        fail("<root>", "missing `tools`")
        tools = []

    scripts = console_scripts()
    seen_ids: set = set()
    seen_ports: dict = {}
    for tool in tools:
        check_tool(tool, seen_ids, seen_ports, groups, scripts)

    if problems:
        print(f"{REGISTRY.relative_to(ROOT)}: {len(problems)} problem(s)\n", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1

    services = sum(1 for t in tools if t.get("tier") == "service")
    print(f"{REGISTRY.relative_to(ROOT)}: {len(tools)} tools "
          f"({services} services, {len(tools) - services} artifacts) across "
          f"{len(groups)} groups — every path resolves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
