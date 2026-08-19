# Tool Installation Log — Example Workstation

> **Example documentation.** All server/database names and figures below are
> fictional samples to illustrate the format. Replace with your own when using
> this template.

A standardized, reusable record of the tools used to run schema-scout on a
Windows workstation. Companion spreadsheet: `tool-installation-log.xlsx`.

> **How to reuse this file**
> - Copy it for a new machine, or add a new row to the Summary table + a detail
>   block for each new tool.
> - Fill every `<…>` placeholder; use `n/a` if it doesn't apply — keep the field.
> - Update **Last updated** whenever you add something.

## 1. Machine details

| Field | Value |
|---|---|
| Machine / hostname | `<fill>` |
| User | Pawan Kapkoti |
| OS / version | Windows 11 |
| Owner / team | Data Engineering |
| Date created | `<YYYY-MM-DD>` |
| Last updated | `<YYYY-MM-DD>` |
| Purpose | Run schema-scout (read-only SQL Server cataloging) + DB/reporting tooling |

## 2. Tools downloaded / used

### Downloaded & installed

| Tool | Version | Install method / ID | Purpose |
|---|---|---|---|
| Git for Windows | 2.54.0 | winget `Git.Git` | Clone repos, version control |
| Python | 3.12.10 | winget `Python.Python.3.12` | Runs schema-scout |
| ODBC Driver 18 for SQL Server | 18.x | winget `Microsoft.msodbcsql.18` | SQL Server connectivity (pyodbc) |
| OpenAI API key | n/a | Set `OPENAI_API_KEY` env var | LLM for table descriptions |
| SQL Server Management Studio | `<fill: Help→About>` | winget `Microsoft.SQLServerManagementStudio` | Run SQL, review roles & access |
| Power BI Desktop | `<fill: File→About>` | winget `Microsoft.PowerBI` | Reporting / dashboards |
| schema-scout | source | `git clone <repo-url>` | Read-only data catalog |

### Python packages (schema-scout dependencies, installed via pip)

| Package | Version | Purpose |
|---|---|---|
| pyodbc | >=5.0 | SQL Server connection (read-only) |
| pandas | >=2.0 | Data handling / profiling |
| openai | >=1.30 | Talks to OpenAI-compatible API |
| pytest | >=8.0 | Tests (development only) |

### Used but not downloaded (built into Windows)

| Tool | Purpose | Verify |
|---|---|---|
| Windows PowerShell | Ran all install / run commands | `$PSVersionTable` |
| winget | Installed the tools above | `winget --version` |

## 3. Tool detail

### schema-scout
- **Install method:** `git clone <repo-url>`, venv + `pip install -r requirements.txt`
- **Install location:** `C:\Users\<user>\schema-scout`
- **Verify command:** `python -m schema_scout.cli --help`
- **Purpose:** Read-only catalog of a target database
- **Notes:** Python deps — pyodbc>=5.0, pandas>=2.0, requests>=2.31, pytest>=8.0.

### OpenAI API
- **Install method:** Set `OPENAI_API_KEY` environment variable
- **Verify command:** Verify API key is set
- **Purpose:** LLM for schema-scout `--describe`; use a local proxy for on-prem
- **Notes:** Model: gpt-4o (configurable via --model flag).

## 4. Configuration changes

| Change | Command / setting | Scope | Reason |
|---|---|---|---|
| PATH | added Git / Python dirs | user | tools usable in any terminal |
| PS execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` | user | allow venv activation script |

## 5. Verification

```text
git --version
python --version
echo $OPENAI_API_KEY   # should be set
python -m schema_scout.cli --help
```

## 6. Authorization & data-handling notes

- **Software install approved by:** `<name / ticket>`
- **Data access approved by:** `<data owner name>`
- **Access level:** Read-only (SELECT only)
- **Sensitivity notes:** Catalog output contains schema + flagged PII; keep on
  approved internal systems, do not upload externally.
