"""Focused tests for ``modules.dbt_runner``, ``modules.dbt_metadata``,
and ``modules.dbt_integration``.

Uses a synthetic manifest dict -- no dbt installation or project required.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from modules.dbt_metadata import DbtMetadata  # noqa: E402
from modules.dbt_runner import DbtRunner  # noqa: E402

# ---------------------------------------------------------------------------
# Synthetic manifest for testing
# ---------------------------------------------------------------------------

SAMPLE_MANIFEST = {
    "metadata": {"project_name": "test_project", "adapter_type": "postgres"},
    "nodes": {
        "model.test_project.dim_products": {
            "resource_type": "model",
            "name": "dim_products",
            "description": "Product dimension table",
            "original_file_path": "models/marts/dim_products.sql",
            "schema": "marts",
            "database": "warehouse",
            "tags": ["production", "products"],
            "columns": {
                "product_code": {"description": "Unique product code", "data_type": "text", "tags": [], "meta": {}},
                "product_name": {"description": "Product name", "data_type": "text", "tags": [], "meta": {}},
                "category": {"description": "Product category", "data_type": "text", "tags": [], "meta": {}},
                "allergens": {"description": "Allergen info", "data_type": "text", "tags": [], "meta": {}},
            },
            "depends_on": {"nodes": ["source.test_project.raw_products"]},
        },
        "model.test_project.fct_production": {
            "resource_type": "model",
            "name": "fct_production",
            "description": "Production run facts with yield and waste",
            "original_file_path": "models/marts/fct_production.sql",
            "schema": "marts",
            "database": "warehouse",
            "tags": ["production"],
            "columns": {
                "run_number": {"description": "Unique run identifier", "data_type": "integer", "tags": [], "meta": {}},
                "product_code": {"description": "FK to dim_products", "data_type": "text", "tags": [], "meta": {}},
                "yield_pct": {"description": "Yield percentage", "data_type": "numeric", "tags": [], "meta": {}},
                "waste_kg": {"description": "Waste in kilograms", "data_type": "numeric", "tags": [], "meta": {}},
            },
            "depends_on": {"nodes": ["model.test_project.dim_products"]},
        },
        "model.test_project.stg_orders": {
            "resource_type": "model",
            "name": "stg_orders",
            "description": "Staged customer orders",
            "original_file_path": "models/staging/stg_orders.sql",
            "schema": "staging",
            "database": "warehouse",
            "tags": ["orders"],
            "columns": {
                "order_id": {"description": "Order ID", "data_type": "integer", "tags": [], "meta": {}},
                "customer": {"description": "Customer name", "data_type": "text", "tags": [], "meta": {}},
                "quantity_kg": {"description": "Order quantity", "data_type": "numeric", "tags": [], "meta": {}},
            },
            "depends_on": {"nodes": []},
        },
        "source.test_project.raw_products": {
            "resource_type": "source",
            "name": "raw_products",
            "description": "Raw source products",
            "original_file_path": "models/sources.yml",
        },
    },
    "exposures": {
        "exposure.test_project.order_dashboard": {
            "name": "order_dashboard",
            "type": "dashboard",
            "depends_on": {"nodes": ["model.test_project.stg_orders"]},
        }
    },
}


# ---------------------------------------------------------------------------
# DbtMetadata tests
# ---------------------------------------------------------------------------

class TestDbtMetadata:
    def setup_method(self) -> None:
        self.metadata = DbtMetadata(SAMPLE_MANIFEST)

    def test_get_models_returns_only_models(self) -> None:
        models = self.metadata.get_models()
        names = [m["name"] for m in models]
        assert "dim_products" in names
        assert "fct_production" in names
        assert "stg_orders" in names
        # source node should not appear
        assert "raw_products" not in names

    def test_get_models_count(self) -> None:
        assert len(self.metadata.get_models()) == 3

    def test_get_model_schema_found(self) -> None:
        schema = self.metadata.get_model_schema("dim_products")
        assert schema["name"] == "dim_products"
        assert schema["description"] == "Product dimension table"
        assert len(schema["columns"]) == 4
        assert "columns_dict" in schema
        assert "product_code" in schema["columns_dict"]

    def test_get_model_schema_not_found(self) -> None:
        schema = self.metadata.get_model_schema("nonexistent_model")
        assert schema == {}

    def test_get_models_by_tag(self) -> None:
        production_models = self.metadata.get_models_by_tag("production")
        names = [m["name"] for m in production_models]
        assert "dim_products" in names
        assert "fct_production" in names
        assert "stg_orders" not in names

    def test_get_models_by_tag_single(self) -> None:
        order_models = self.metadata.get_models_by_tag("orders")
        assert len(order_models) == 1
        assert order_models[0]["name"] == "stg_orders"

    def test_to_schema_registry_format(self) -> None:
        registry = self.metadata.to_schema_registry_format()
        # Three tags: production, products, orders -> 3 domains
        assert "production" in registry
        assert "orders" in registry
        # dim_products has ["production", "products"] tags
        # "production" tag is first -> maps to production domain
        assert "dim_products" in registry["production"]["tables"]
        assert "fct_production" in registry["production"]["tables"]
        assert "stg_orders" in registry["orders"]["tables"]

    def test_to_schema_registry_columns_string(self) -> None:
        registry = self.metadata.to_schema_registry_format()
        cols = registry["production"]["tables"]["dim_products"]
        assert "product_code" in cols
        assert "product_name" in cols

    def test_get_exposures(self) -> None:
        exposures = self.metadata.get_exposures()
        assert len(exposures) == 1
        assert exposures[0]["name"] == "order_dashboard"

    def test_find_model_by_keywords_exact_name(self) -> None:
        match = self.metadata.find_model_by_keywords("production yield waste")
        assert match is not None
        assert match["name"] == "fct_production"

    def test_find_model_by_keywords_description(self) -> None:
        match = self.metadata.find_model_by_keywords("customer orders quantity")
        assert match is not None
        assert match["name"] == "stg_orders"

    def test_find_model_by_keywords_no_match(self) -> None:
        match = self.metadata.find_model_by_keywords("xyzzy plugh")
        assert match is None

    def test_empty_manifest(self) -> None:
        metadata = DbtMetadata({})
        assert metadata.get_models() == []
        assert metadata.get_model_schema("anything") == {}
        assert metadata.to_schema_registry_format() == {}


# ---------------------------------------------------------------------------
# DbtRunner tests (mock subprocess)
# ---------------------------------------------------------------------------

class TestDbtRunner:
    def test_init_default_profile_dir(self) -> None:
        runner = DbtRunner("/path/to/project")
        assert runner.project_dir == Path("/path/to/project")
        assert runner.profile_dir == Path("/path/to/project/profiles")

    def test_init_custom_profile_dir(self) -> None:
        runner = DbtRunner("/project", "/custom/profiles")
        assert runner.profile_dir == Path("/custom/profiles")

    @patch("modules.dbt_runner.subprocess.run")
    def test_run_model_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Done. PASS=1 WARN=0 ERROR=0 SKIP=0",
            stderr="",
        )
        runner = DbtRunner("/project")
        result = runner.run_model("dim_products")
        assert result["success"] is True
        assert "PASS=1" in result["output"]

    @patch("modules.dbt_runner.subprocess.run")
    def test_run_model_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: table not found",
        )
        runner = DbtRunner("/project")
        result = runner.run_model("bad_model")
        assert result["success"] is False
        assert "table not found" in result["error"]

    @patch("modules.dbt_runner.subprocess.run")
    def test_run_model_full_refresh(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        runner = DbtRunner("/project")
        runner.run_model("dim_products", full_refresh=True)
        cmd = mock_run.call_args[0][0]
        assert "--full-refresh" in cmd

    def test_run_model_dbt_not_found(self) -> None:
        runner = DbtRunner("/nonexistent")
        result = runner.run_model("anything")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_list_models_empty_manifest(self) -> None:
        runner = DbtRunner("/project")
        with patch.object(runner, "get_manifest", return_value={}):
            assert runner.list_models() == []


# ---------------------------------------------------------------------------
# dbt_enabled flag in schema_registry (no actual dbt needed)
# ---------------------------------------------------------------------------

class TestSchemaRegistryDbtFlag:
    def test_get_dbt_integration_returns_none_when_disabled(self) -> None:
        from modules import schema_registry

        # Reset cached value
        schema_registry._dbt_integration = None
        with patch("modules.schema_registry.DBT_ENABLED", False):
            assert schema_registry.get_dbt_integration() is None

    def test_get_dbt_integration_returns_none_when_no_project_dir(self) -> None:
        from modules import schema_registry

        schema_registry._dbt_integration = None
        with patch("modules.schema_registry.DBT_ENABLED", True), \
             patch("modules.schema_registry.DBT_PROJECT_DIR", ""):
            assert schema_registry.get_dbt_integration() is None
