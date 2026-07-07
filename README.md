# pii-veil

[![PyPI](https://img.shields.io/pypi/v/pii-veil)](https://pypi.org/project/pii-veil/) [![Downloads](https://static.pepy.tech/badge/pii-veil)](https://pepy.tech/projects/pii-veil)

**Mask PII in SQL query results before they reach the LLM or the screen.**

> Part of the [Governed Agent Stack](https://github.com/Pawansingh3889/governed-agent-stack): free, on-prem building blocks for an AI agent you can point at a real database and audit.

[schema-scout](https://github.com/Pawansingh3889/schema-scout) *flags* the PII columns and [query-warden](https://github.com/Pawansingh3889/query-warden) can *block* them, but some queries still legitimately return rows that contain personal data. pii-veil is the last step: it scrubs PII out of the result data so the model and the user see a customer's name as `<PERSON>` and an email as `<EMAIL_ADDRESS>`, not the real values.

It is powered by [Microsoft Presidio](https://github.com/microsoft/presidio) when that is installed (names, locations, and the structured types), and falls back to built-in regex detectors (email, phone, card, IP) otherwise, so it works out of the box with no model download. It only ever touches the result data, never a live database.

## Install

```bash
pip install pii-veil                 # regex backend, zero dependencies
pip install "pii-veil[presidio]"     # add Presidio for full PII detection
```

## Use it

```python
from pii_veil import Veil

veil = Veil()                        # uses Presidio if installed, else regex
veil.backend                         # "presidio" or "regex"

veil.scrub_text("reach me at john@acme.com or 07911 123456")
# "reach me at <EMAIL_ADDRESS> or <PHONE_NUMBER>"

# Scrub query results: string cells are masked, numbers and dates pass through.
rows = [{"customer": "John Smith", "email": "j@acme.com", "qty_kg": 42}]
veil.scrub_rows(rows)
# [{"customer": "<PERSON>", "email": "<EMAIL_ADDRESS>", "qty_kg": 42}]   # with Presidio

# Or scrub only specific columns:
veil.scrub_rows(rows, columns=["customer", "email"])
```

From the command line:

```bash
pii-veil "reach me at john@acme.com"
# reach me at <EMAIL_ADDRESS>
```

## Where it fits

pii-veil is the result-masking step in the Governed Agent Stack. Run it on the rows after execution, before they go back to the agent:

```
... -> query-warden role check -> sql-explorer-mcp (run query) -> pii-veil (mask results) -> agent / user
```

- **[schema-scout](https://github.com/Pawansingh3889/schema-scout)** already flags which columns are PII, so it can tell pii-veil exactly which columns to scrub.
- **[query-warden](https://github.com/Pawansingh3889/query-warden)** blocks access by role; pii-veil masks what is allowed through.

## Read-only by design

pii-veil reasons about result data alone. It never connects to a database and never runs a query, so it is safe to call on every result and easy to test as a pure function.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE).
