# query-warden

**Role-based access control for SQL queries. Decide whether a role may run a query before it ever touches the database.**

> Part of the [Governed Agent Stack](https://github.com/Pawansingh3889/governed-agent-stack): free, on-prem building blocks for an AI agent you can point at a real database and audit.

A safety layer like [sql-sop](https://github.com/Pawansingh3889/sql-guard) answers "is this SQL safe?" and a read-only MCP server answers "is it read-only?". Neither answers the question that gets you in trouble with an LLM near real data: **"is this person allowed to see this?"** query-warden is that check.

You write the policy in YAML. It parses the query with [sqlglot](https://github.com/tobymao/sqlglot), pulls out the tables and columns it touches, and blocks anything outside the role's allow-list. No database connection, no execution, just a decision.

## Install

```bash
pip install query-warden
```

## Policy

```yaml
default_role: operator

domains:
  production: [production, prod_runs, waste_log]
  staff: [staff, prod_shifts]

roles:
  operator:
    allow_domains: [production]
    deny_columns: [hourly_rate, salary]   # never expose pay to the floor
  analyst:
    allow_tables: ["*"]                    # read anything
```

A role may allow whole **domains** (named groups of tables), specific **tables**, or `"*"` for everything. **`deny_columns`** blocks named columns, and a bare `SELECT *` is rejected when any column is denied (it could expose them). `COUNT(*)` is fine.

## Use it

As a library:

```python
from query_warden import Warden

warden = Warden.from_yaml("policy.yaml")

warden.check("SELECT product_id, waste_kg FROM waste_log", role="operator")
# Decision(allowed=True, role='operator', violations=[])

d = warden.check("SELECT name, hourly_rate FROM staff", role="operator")
d.allowed   # False
d.reason    # "role 'operator' may not query table 'staff'; role 'operator' may not access column 'hourly_rate'"
```

From the command line (exit 0 = allowed, 1 = denied):

```bash
query-warden check --policy policy.yaml --role operator "SELECT * FROM staff"
# DENY (role=operator): role 'operator' may not query table 'staff' ...
```

## Where it fits

query-warden is the access-control layer in the Governed Agent Stack. Put it next to the other guards, after SQL generation and before execution:

```
question -> agent -> generated SQL -> [read-only] -> [sql-sop lint] -> [query-warden role check] -> database
```

It pairs naturally with two other tools in the stack:

- **[schema-scout](https://github.com/Pawansingh3889/schema-scout)** already flags PII columns, so it can seed a starter policy ("deny these columns unless a role opts in").
- **[agent-blackbox](https://github.com/Pawansingh3889/agent-blackbox)** can record every allow and deny, so "who tried to access what" has a tamper-evident answer.

## Read-only by design

query-warden never connects to a database and never runs the query. It reasons about the SQL text alone, so it is safe to call on every query in the hot path and easy to test as a pure function.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE).
