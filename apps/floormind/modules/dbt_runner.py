"""Execute dbt commands and read project metadata.

Provides a thin wrapper around the dbt CLI for running models,
reading compiled SQL, and accessing the manifest file.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


class DbtRunner:
    """Execute dbt commands and read project metadata."""

    def __init__(self, project_dir: str, profile_dir: Optional[str] = None) -> None:
        self.project_dir = Path(project_dir)
        self.profile_dir = Path(profile_dir) if profile_dir else self.project_dir / "profiles"

    def _build_env(self) -> dict[str, str]:
        """Build environment variables for dbt subprocess calls."""
        env = dict(os.environ)
        env["DBT_PROFILES_DIR"] = str(self.profile_dir)
        return env

    def run_model(self, model_name: str, full_refresh: bool = False) -> dict[str, Any]:
        """Run a specific dbt model.

        Returns a dict with keys: success, output, error.
        """
        cmd = ["dbt", "run", "--select", model_name]
        if full_refresh:
            cmd.append("--full-refresh")

        log.info("Running dbt: %s (project=%s)", " ".join(cmd), self.project_dir)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                env=self._build_env(),
                timeout=300,
            )
        except FileNotFoundError:
            return {
                "success": False,
                "output": "",
                "error": "dbt executable not found. Install dbt-core (pip install dbt-core).",
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "dbt run timed out after 300 seconds.",
            }

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
        }

    def run_test(self, model_name: Optional[str] = None) -> dict[str, Any]:
        """Run dbt tests, optionally scoped to a model."""
        cmd = ["dbt", "test"]
        if model_name:
            cmd.extend(["--select", model_name])

        log.info("Running dbt test: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                env=self._build_env(),
                timeout=300,
            )
        except FileNotFoundError:
            return {
                "success": False,
                "output": "",
                "error": "dbt executable not found.",
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "dbt test timed out after 300 seconds.",
            }

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
        }

    def get_manifest(self) -> dict[str, Any]:
        """Read the dbt manifest.json for schema information."""
        manifest_path = self.project_dir / "target" / "manifest.json"
        if not manifest_path.exists():
            log.warning("Manifest not found at %s", manifest_path)
            return {}

        try:
            return json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            log.error("Failed to read manifest: %s", exc)
            return {}

    def get_compiled_sql(self, model_name: str) -> Optional[str]:
        """Get compiled SQL for a model from the target directory."""
        compiled_path = (
            self.project_dir / "target" / "compiled" / model_name / "model.sql"
        )
        if not compiled_path.exists():
            log.warning("Compiled SQL not found for model %s", model_name)
            return None

        try:
            return compiled_path.read_text()
        except OSError as exc:
            log.error("Failed to read compiled SQL: %s", exc)
            return None

    def list_models(self) -> list[str]:
        """List all model names from the manifest."""
        manifest = self.get_manifest()
        models = []
        for _node_id, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") == "model":
                name = node.get("name")
                if name:
                    models.append(name)
        return sorted(models)

    def get_catalog(self) -> dict[str, Any]:
        """Read the dbt catalog.json for column metadata."""
        catalog_path = self.project_dir / "target" / "catalog.json"
        if not catalog_path.exists():
            return {}

        try:
            return json.loads(catalog_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            log.error("Failed to read catalog: %s", exc)
            return {}
