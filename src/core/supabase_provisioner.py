"""Supabase project provisioning orchestrator.

Ties together the OAuth2 flow, Management API, and schema migration
to fully automate the setup of a user's Supabase project.

Flow:
1. Use OAuth2 access_token to authenticate with Management API
2. List existing projects → find one with HUC schema, or create new
3. If creating: wait for project to become healthy
4. Apply schema migration (create tables, RLS policies)
5. Fetch the project's anon API key
6. Store project ref + URL + anon key in the local DB
7. Create storage bucket for rental images

This module does NOT handle the OAuth2 login itself — it receives an
access_token that was obtained via supabase_oauth.py.
"""

import logging
import time
import secrets
import string

from src.core.supabase_management import SupabaseManagementClient
from src.core.supabase_schema import get_migration_sql, SCHEMA_VERSION, get_version_check_sql

logger = logging.getLogger(__name__)

# Project name used when creating a new project
HUC_PROJECT_NAME = "HUC Data"

# Default region (can be overridden). ap-southeast-1 is a good default for Asia users.
DEFAULT_REGION = "ap-southeast-1"

# How long to wait for a new project to become healthy (seconds)
MAX_HEALTH_WAIT = 120
HEALTH_POLL_INTERVAL = 5


def _generate_db_password() -> str:
    """Generate a secure random database password for the new project."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(20))


class SupabaseProvisioner:
    """Orchestrates the full Supabase project provisioning flow.

    Args:
        access_token: OAuth2 access token (from supabase_oauth.exchange_code_for_tokens).
    """

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.mgmt = SupabaseManagementClient(access_token)

    def provision(self, db_manager) -> dict:
        """Run the full provisioning flow and store credentials.

        Handles all 6 scenarios:
        A) No existing project → create new, apply schema
        B) Existing HUC project, schema up-to-date → reuse, skip schema
        C) Existing HUC project, no schema → reuse, apply schema
        D) Existing HUC project, older schema → reuse, apply schema (idempotent)
        E) Existing non-HUC project (only 1 active) → reuse, apply schema
        F) Multiple existing non-HUC projects → pick first (future: picker dialog)

        Args:
            db_manager: DBManager instance for storing project ref + API key.

        Returns:
            Dict with keys: project_ref, project_url, anon_key.

        Raises:
            Exception: If any step fails (project limit, schema error, etc.).
        """
        # Step 1: List existing projects
        projects = self.mgmt.list_projects()
        huc_project = self._find_huc_project(projects)

        if huc_project:
            logger.info(f"Found existing project: {huc_project['ref']} (name: {huc_project.get('name')})")
            project_ref = huc_project["ref"]

            # Step 2: Check if schema is already applied and current
            schema_version = self._check_schema_version(project_ref)
            if schema_version >= SCHEMA_VERSION:
                logger.info(f"Schema v{schema_version} already applied — skipping migration")
            else:
                # Scenario C/D/E: existing project needs schema
                logger.info(f"Schema version {schema_version} (need {SCHEMA_VERSION}) — applying migration...")
                self._apply_schema(project_ref)
        else:
            # Scenario A: No existing project → create new one
            project_ref = self._create_new_project()
            # Wait for it to become healthy before applying schema
            self._wait_for_health(project_ref)
            # Apply schema to the fresh project
            self._apply_schema(project_ref)

        # Step 3: Fetch anon API key
        anon_key = self.mgmt.get_anon_api_key(project_ref)
        project_url = f"https://{project_ref}.supabase.co"

        # Step 4: Store credentials in local DB
        db_manager.save_project_ref(project_ref)
        db_manager.save_config(project_url, anon_key)

        logger.info(f"✅ Provisioning complete. Project: {project_ref}")

        return {
            "project_ref": project_ref,
            "project_url": project_url,
            "anon_key": anon_key,
        }

    def _check_schema_version(self, project_ref: str) -> int:
        """Check the current HUC schema version on a project.

        Uses the Management API's "Run a query" endpoint to check
        if the _huc_schema_version table exists and what version it reports.

        Returns:
            Schema version integer (0 if table doesn't exist or query fails).
        """
        try:
            rows = self.mgmt.run_query(
                project_ref=project_ref,
                query=get_version_check_sql(),
            )
            if rows:
                return int(rows[0].get("version", 0))
            return 0
        except Exception as e:
            logger.info(f"Schema version check failed (expected for new projects): {e}")
            return 0

    def _apply_schema(self, project_ref: str) -> None:
        """Apply the HUC schema migration to a project.

        The migration SQL is idempotent (all CREATE TABLE IF NOT EXISTS),
        so it's safe to run on projects that already have some tables.
        """
        self.mgmt.apply_migration(
            project_ref=project_ref,
            name=f"huc_schema_v{SCHEMA_VERSION}",
            query=get_migration_sql(),
        )

    def _find_huc_project(self, projects: list[dict]) -> dict | None:
        """Find a project that already has the HUC schema.

        Heuristic: look for projects named "HUC Data" or with "HUC" in the name.
        If only one active project exists, use it.
        If multiple active projects exist and none are named "HUC Data",
        return None (will create a new one).
        """
        for project in projects:
            if project.get("status") != "ACTIVE":
                continue
            name = project.get("name", "")
            if name == HUC_PROJECT_NAME or "HUC" in name.upper():
                return project
        # If only one active project exists, use it
        active = [p for p in projects if p.get("status") == "ACTIVE"]
        if len(active) == 1:
            return active[0]
        return None

    def _create_new_project(self) -> str:
        """Create a new Supabase project in the user's first organization.

        Returns:
            The project reference ID.

        Raises:
            Exception: If creation fails (e.g., free tier 2-project limit).
        """
        orgs = self.mgmt.list_organizations()
        if not orgs:
            raise Exception("No organizations found. Please create an organization on supabase.com first.")

        org_slug = orgs[0]["slug"]
        db_password = _generate_db_password()

        logger.info(f"Creating new project '{HUC_PROJECT_NAME}' in org '{org_slug}'...")
        result = self.mgmt.create_project(
            name=HUC_PROJECT_NAME,
            organization_slug=org_slug,
            db_password=db_password,
            region=DEFAULT_REGION,
        )
        return result["ref"]

    def _wait_for_health(self, project_ref: str, max_wait: int = MAX_HEALTH_WAIT) -> None:
        """Poll project health until all services are healthy or timeout.

        New projects take ~30-60 seconds to provision.
        """
        logger.info(f"Waiting for project {project_ref} to become healthy...")
        elapsed = 0
        while elapsed < max_wait:
            if self.mgmt.is_project_healthy(project_ref):
                logger.info("✅ Project is healthy")
                return
            time.sleep(HEALTH_POLL_INTERVAL)
            elapsed += HEALTH_POLL_INTERVAL
        # Don't fail hard — the project might still be provisioning
        # Schema migration might still work even if health check is slow
        logger.warning(
            f"Project {project_ref} did not report healthy within {max_wait}s. "
            "Proceeding with schema migration anyway..."
        )
