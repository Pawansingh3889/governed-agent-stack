"""Read dbt manifest and extract schema information.

Parses the dbt manifest.json to extract model definitions, column
metadata, descriptions, and tags. Converts this information into
FloorMind's schema registry format for domain-scoped SQL generation.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class DbtMetadata:
    """Extract schema information from a dbt manifest dict."""

    def __init__(self, manifest: dict[str, Any]) -> None:
        self.manifest = manifest
        self.nodes: dict[str, Any] = manifest.get("nodes", {})

    def get_models(self) -> list[dict[str, Any]]:
        """Get all dbt models with their metadata."""
        models = []
        for _node_id, node in self.nodes.items():
            if node.get("resource_type") == "model":
                models.append({
                    "name": node.get("name", ""),
                    "description": node.get("description", ""),
                    "columns": self._extract_columns(node),
                    "tags": node.get("tags", []),
                    "path": node.get("original_file_path", ""),
                    "schema": node.get("schema", ""),
                    "database": node.get("database", ""),
                    "depends_on": node.get("depends_on", {}).get("nodes", []),
                })
        return models

    def get_model_schema(self, model_name: str) -> dict[str, Any]:
        """Get schema for a specific model by name."""
        for _node_id, node in self.nodes.items():
            if node.get("name") == model_name:
                columns = self._extract_columns(node)
                return {
                    "name": model_name,
                    "description": node.get("description", ""),
                    "columns": columns,
                    "columns_dict": {col["name"]: col for col in columns},
                    "tags": node.get("tags", []),
                    "path": node.get("original_file_path", ""),
                }
        return {}

    def get_models_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Get all models that have a specific tag."""
        models = []
        for _node_id, node in self.nodes.items():
            if node.get("resource_type") == "model":
                if tag in node.get("tags", []):
                    models.append({
                        "name": node.get("name", ""),
                        "description": node.get("description", ""),
                        "columns": self._extract_columns(node),
                        "tags": node.get("tags", []),
                    })
        return models

    def get_exposures(self) -> list[dict[str, Any]]:
        """Get all exposures from the manifest."""
        exposures = []
        for _node_id, node in self.manifest.get("exposures", {}).items():
            exposures.append({
                "name": node.get("name", ""),
                "type": node.get("type", ""),
                "depends_on": node.get("depends_on", {}).get("nodes", []),
            })
        return exposures

    def _extract_columns(self, node: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract column information from a node."""
        columns = []
        for col_name, col_meta in node.get("columns", {}).items():
            columns.append({
                "name": col_name,
                "description": col_meta.get("description", ""),
                "data_type": col_meta.get("data_type", ""),
                "tags": col_meta.get("tags", []),
                "meta": col_meta.get("meta", {}),
            })
        return columns

    def to_schema_registry_format(self) -> dict[str, Any]:
        """Convert dbt metadata to FloorMind schema registry format.

        Groups models by tags (using the first tag as domain) or falls
        back to a "dbt" domain for untagged models.

        Returns:
            Dict mapping domain names to {description, tables} structure
            compatible with schema_registry.DEFAULT_SCHEMA.
        """
        registry: dict[str, Any] = {}

        for model in self.get_models():
            tags = model["tags"]
            if tags:
                domain = tags[0]
            else:
                domain = "dbt"

            if domain not in registry:
                registry[domain] = {
                    "description": f"dbt models tagged: {domain}" if tags else "dbt models",
                    "tables": {},
                }

            columns_str = ", ".join(col["name"] for col in model["columns"])
            registry[domain]["tables"][model["name"]] = columns_str

        return registry

    def find_model_by_keywords(self, question: str) -> dict[str, Any] | None:
        """Best-effort match: find a dbt model whose name or description
        contains keywords from the question.

        Returns the matching model dict or None.
        """
        q_lower = question.lower()
        words = set(q_lower.split())

        best_match: dict[str, Any] | None = None
        best_score = 0

        for model in self.get_models():
            name_lower = model["name"].lower()
            desc_lower = model["description"].lower()

            score = 0
            for word in words:
                if len(word) < 3:
                    continue
                if word in name_lower:
                    score += 2
                if word in desc_lower:
                    score += 1

            if score > best_score:
                best_score = score
                best_match = model

        if best_score >= 2:
            return best_match
        return None
