"""High-level dbt integration for FloorMind.

Connects dbt metadata with FloorMind's schema registry and agent graph,
enabling dbt-powered schema discovery and model execution.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from modules.dbt_metadata import DbtMetadata
from modules.dbt_runner import DbtRunner

log = logging.getLogger(__name__)


class DbtIntegration:
    """Integrate dbt with FloorMind's query pipeline."""

    def __init__(self, project_dir: str, profile_dir: Optional[str] = None) -> None:
        self.runner = DbtRunner(project_dir, profile_dir)
        self._manifest: dict[str, Any] | None = None
        self._metadata: DbtMetadata | None = None

    @property
    def metadata(self) -> DbtMetadata:
        """Lazy-load dbt metadata from the manifest."""
        if self._metadata is None:
            self._manifest = self.runner.get_manifest()
            self._metadata = DbtMetadata(self._manifest)
        return self._metadata

    def refresh_metadata(self) -> None:
        """Force a re-read of the dbt manifest."""
        self._manifest = self.runner.get_manifest()
        self._metadata = DbtMetadata(self._manifest)

    def is_available(self) -> bool:
        """Check if dbt metadata is loaded and has models."""
        try:
            return len(self.metadata.get_models()) > 0
        except Exception:
            return False

    def get_schema_for_domain(self, domain: str) -> dict[str, Any]:
        """Get schema for a specific domain from dbt models.

        Matches domain against model tags. Returns empty dict if no
        dbt models match.
        """
        return self.metadata.to_schema_registry_format().get(domain, {})

    def get_all_schemas(self) -> dict[str, Any]:
        """Get all schemas from dbt models in registry format."""
        return self.metadata.to_schema_registry_format()

    def get_schema_for_question(self, question: str) -> dict[str, Any]:
        """Try to find a dbt model matching the question.

        Uses keyword matching on model names and descriptions.
        Returns schema dict in registry format or empty dict.
        """
        match = self.metadata.find_model_by_keywords(question)
        if match:
            columns_str = ", ".join(col["name"] for col in match["columns"])
            return {
                "description": match.get("description", ""),
                "tables": {match["name"]: columns_str},
            }
        return {}

    def run_model(self, model_name: str, full_refresh: bool = False) -> dict[str, Any]:
        """Run a dbt model and return results."""
        result = self.runner.run_model(model_name, full_refresh=full_refresh)
        if not result["success"]:
            return {"error": f"dbt run failed: {result['error']}"}

        compiled_sql = self.runner.get_compiled_sql(model_name)
        return {
            "success": True,
            "model": model_name,
            "compiled_sql": compiled_sql,
            "output": result["output"],
        }

    def get_compiled_sql(self, model_name: str) -> Optional[str]:
        """Get the compiled SQL for a model."""
        return self.runner.get_compiled_sql(model_name)

    def list_models(self) -> list[str]:
        """List all available dbt models."""
        return self.runner.list_models()
