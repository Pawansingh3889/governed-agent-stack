# sql-sop-mcp

[![PyPI](https://img.shields.io/pypi/v/sql-sop-mcp)](https://pypi.org/project/sql-sop-mcp/) [![Downloads](https://static.pepy.tech/badge/sql-sop-mcp)](https://pepy.tech/projects/sql-sop-mcp)

[![PyPI](https://img.shields.io/pypi/v/sql-sop-mcp)](https://pypi.org/project/sql-sop-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/sql-sop-mcp)](https://pypi.org/project/sql-sop-mcp/)
[![CI](https://github.com/Pawansingh3889/sql-sop-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/Pawansingh3889/sql-sop-mcp/actions/workflows/ci.yml)
[![pre-commit.ci](https://results.pre-commit.ci/badge/github/Pawansingh3889/sql-sop-mcp/main.svg)](https://results.pre-commit.ci/latest/github/Pawansingh3889/sql-sop-mcp/main)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Model Context Protocol server that wires [sql-sop](https://pypi.org/project/sql-sop/) into any MCP-aware LLM client. Lets Claude Desktop, Cursor, ChatGPT desktop, Continue, and similar tools call sql-sop's linter as a callable tool from inside a chat.

The point: when an LLM generates SQL for you, it can lint that SQL itself before suggesting it. Or you can say "lint this query", paste the SQL, and the model uses the tool rather than guessing.

## What it exposes

Two tools, both stdio-transport:

| Tool | What it does |
|---|---|
| `lint_sql(sql, severity?, disable?)` | Run sql-sop against a SQL string. Returns `{passed, summary, findings[]}`. Each finding has `rule_id`, `severity`, `line`, `message`, `suggestion`. |
| `list_rules()` | Return the full rule catalogue (43 rules in sql-sop v0.7.0; 48 with `--contract` enabled). |

Backed by [sql-sop](https://github.com/Pawansingh3889/sql-guard), a fast rule-based SQL linter with 38 SQL rules (including 5 T-SQL specific ones) and 5 Python source rules for SQL injection on `cursor.execute()` / `sqlalchemy.text()`. As of v0.7.0 it also offers an opt-in Contracts pack (5 schema-aware rules) for projects that maintain a YAML data contract. There's a [browser playground](https://pawansingh3889.github.io/sql-guard/) if you want to feel out the rules before wiring this up.

## Install

```bash
pip install sql-sop-mcp
```

Or with `pipx` if you want the CLI on PATH without polluting your project's venv:

```bash
pipx install sql-sop-mcp
```

## Wire it into your LLM client

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "sql-sop": {
      "command": "sql-sop-mcp"
    }
  }
}
```

Restart Claude Desktop. New chats will see two tools: `lint_sql` and `list_rules`.

### Cursor

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "sql-sop": {
      "command": "sql-sop-mcp"
    }
  }
}
```

### Continue (VS Code / JetBrains plugin)

Add to `~/.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "sql-sop",
      "command": "sql-sop-mcp"
    }
  ]
}
```

### Generic stdio-MCP client

Anything that speaks MCP over stdio will work. Run `sql-sop-mcp` as a subprocess and talk to it on stdin/stdout.

## What a typical interaction looks like

You: *"Write me a query to remove inactive users older than a year and lint it before suggesting."*

The model calls `lint_sql` against its draft, gets back something like:

```json
{
  "passed": false,
  "summary": "1 error, 1 warning in 1 statement",
  "findings": [
    {
      "rule_id": "E001",
      "severity": "error",
      "line": 1,
      "message": "DELETE without WHERE clause -- this will delete all rows",
      "suggestion": "Add a WHERE clause to limit affected rows"
    },
    {
      "rule_id": "W003",
      "severity": "warning",
      "line": 1,
      "message": "Function on column in WHERE -- kills index usage",
      "suggestion": "Move the function to the value side: WHERE date >= '2024-01-01'"
    }
  ]
}
```

It then revises the query and lints again before showing it to you.

## When to use `disable`

If the model is sure a rule is a false positive in context (e.g. a one-off admin script where SELECT * is genuinely fine), it can pass `disable: ["W001"]`. Treat this as the model's reasoning surface. Read the suggested rationale, not just the final SQL.

## Roadmap (open to PRs)

- `lint_file(path)`: lint a file the LLM has access to via filesystem MCP
- `explain_rule(rule_id)`: return the rule's full documentation, examples of pass/fail SQL
- `lint_python_file(path)`: wrap the Python-source scanner so the LLM can audit `.py` files for `cursor.execute(f"...")` SQL injection
- `suggest_index(sql, schema)`: emit candidate covering-index DDL based on the query

## Related

- [sql-sop](https://pypi.org/project/sql-sop/): the linter this server wraps. CLI, pre-commit hook, GitHub Action, browser playground
- [pr-sop](https://pypi.org/project/pr-sop/): sister tool for PR governance
- [Model Context Protocol](https://modelcontextprotocol.io/): the spec
- [FastMCP](https://github.com/jlowin/fastmcp): the Python framework this server is built on

## License

MIT. See [LICENSE](LICENSE).
