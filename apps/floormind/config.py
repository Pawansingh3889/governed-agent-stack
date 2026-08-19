"""FloorMind configuration."""
import os

# LLM (OpenAI-compatible)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)  # set for local proxies (e.g. LiteLLM)
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

# Database
# Supports SQLite (demo) and SQL Server (production)
#
# SQLite (default demo):
#   FLOORMIND_DB=sqlite:///data/demo.db
#
# SQL Server (read-only):
#   FLOORMIND_DB=mssql+pyodbc://readonly_user:password@SERVER/DATABASE?driver=ODBC+Driver+17+for+SQL+Server
#
# SQL Server with Windows Auth:
#   FLOORMIND_DB=mssql+pyodbc://SERVER/DATABASE?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
#
DATABASE_URL = os.getenv("FLOORMIND_DB", "sqlite:///data/demo.db")

# Database type detection
DB_TYPE = "mssql" if "mssql" in DATABASE_URL else "sqlite"

# ChromaDB
CHROMA_DIR = os.getenv("FLOORMIND_CHROMA_DIR", "data/chroma_store")

# Vector search backend: "chromadb" (default) or "pgvector"
VECTOR_DB = os.getenv("FLOORMIND_VECTOR_DB", "chromadb")
VECTOR_PG_URL = os.getenv("FLOORMIND_VECTOR_PG_URL", "")

# App
APP_NAME = "FloorMind"
APP_TAGLINE = "The AI Brain for Your Operations"
VERSION = "0.3.1"

# Schema
SCHEMA_CONFIG = os.getenv("SCHEMA_CONFIG", "schema.yaml")
SCHEMA_MODE = os.getenv("SCHEMA_MODE", "auto")  # "auto" or "mapped"

# SQL validation
SQL_MAX_ROWS = int(os.getenv("FLOORMIND_SQL_MAX_ROWS", "1000"))

# Domain documentation (runtime-loaded business rules)
DOMAIN_DOCS_DIR = os.getenv("FLOORMIND_DOMAIN_DOCS", "docs/domains")

# Alerts
YIELD_DROP_THRESHOLD = 5.0  # Alert if yield drops more than 5% vs average
TEMP_MAX_COLD_ROOM = 5.0    # Alert above 5°C
TEMP_MIN_COLD_ROOM = -2.0   # Alert below -2°C
MAX_WEEKLY_HOURS = 48        # Working Time Regulations

# Production alerts
PROD_YIELD_MIN = 90.0        # Alert if run yield below 90%
GIVEAWAY_PCT_THRESHOLD = 3.0 # Alert if giveaway exceeds 3%
NC_CRITICAL_OPEN_DAYS = 2    # Alert if critical NC open > 2 days

# MCP Servers
MCP_DB_HOST = os.getenv("MCP_DB_HOST", "localhost")
MCP_DB_PORT = int(os.getenv("MCP_DB_PORT", "9000"))
MCP_DOC_HOST = os.getenv("MCP_DOC_HOST", "localhost")
MCP_DOC_PORT = int(os.getenv("MCP_DOC_PORT", "9001"))
MCP_ENABLED = os.getenv("MCP_ENABLED", "false").lower() == "true"

# dbt Integration
DBT_ENABLED = os.getenv("FLOORMIND_DBT_ENABLED", "false").lower() == "true"
DBT_PROJECT_DIR = os.getenv("FLOORMIND_DBT_PROJECT_DIR", "")
DBT_PROFILE_DIR = os.getenv("FLOORMIND_DBT_PROFILE_DIR", "")
