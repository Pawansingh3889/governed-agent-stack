# elenchus-mcp

Model Context Protocol server that exposes [Elenchus](https://github.com/govern-agents/elenchus) survey tools to LLMs.

## What it does

Lets an LLM create, publish, conduct, and analyse surveys through a running Elenchus instance. No survey logic lives here; every call is an HTTP request to Elenchus's API.

## Tools

| Tool | Description |
|------|-------------|
| `list_surveys` | List published survey templates with run counts |
| `create_survey` | Create a new survey template with questions |
| `generate_survey` | Generate a survey from natural-language description |
| `publish_survey` | Open a draft survey for responses |
| `start_conversation` | Begin a survey run with a respondent |
| `send_response` | Record a respondent's answer |
| `get_results` | Get aggregated survey results and report |
| `close_survey` | Prevent new conversations from starting |

## Install

```bash
pip install elenchus-mcp
```

Or from the monorepo:

```bash
uv sync --package elenchus-mcp
```

## Configure

Set these environment variables:

```bash
ELENCHUS_URL=http://localhost:8000    # Elenchus backend URL
ELENCHUS_USER_ID=your-user-id        # Caller identity (X-User-Id header)
```

## Run

```bash
elenchus-mcp
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "elenchus": {
      "command": "elenchus-mcp",
      "env": {
        "ELENCHUS_URL": "http://localhost:8000",
        "ELENCHUS_USER_ID": "00000000-0000-0000-0000-0000000000a1"
      }
    }
  }
}
```

## Development

```bash
uv sync --package elenchus-mcp --all-extras
uv run pytest packages/elenchus-mcp/tests/
uv run ruff check packages/elenchus-mcp/
```

## License

MIT
