"""drift-gate — refuse to run against a schema you have not verified.

Part of the Governed Agent Stack. Deterministic by design: no model,
no network, no autonomy. It compares two schema-scout catalogs, applies
a policy you wrote, and exits non-zero when something breaking moved.
"""

__version__ = "0.1.0"

from .catalog import Catalog, Change, diff_catalogs, load_catalog  # noqa: F401
from .manifest import Seal, seal, verify  # noqa: F401
from .policy import Policy, Severity, Verdict, overall  # noqa: F401
from .types import TypeChange, classify_type_change, parse_type  # noqa: F401

__all__ = [
    "__version__",
    "Catalog", "Change", "load_catalog", "diff_catalogs",
    "Policy", "Severity", "Verdict", "overall",
    "Seal", "seal", "verify",
    "TypeChange", "classify_type_change", "parse_type",
]
