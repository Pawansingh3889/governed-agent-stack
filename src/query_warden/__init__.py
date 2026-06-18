"""query-warden: role-based access control for SQL queries.

Part of the Governed Agent Stack. Decide whether a role may run a query before
it reaches the database: read-only, on-prem, no database connection needed.
"""
from .policy import Policy, Role
from .warden import Decision, Warden

__all__ = ["Warden", "Decision", "Policy", "Role"]
__version__ = "0.1.0"
