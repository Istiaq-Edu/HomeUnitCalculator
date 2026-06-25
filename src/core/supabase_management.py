"""Supabase Management API client.

Wraps the Supabase Management API REST endpoints for:
- Listing organizations
- Listing and creating projects
- Applying database migrations (SQL)
- Fetching project API keys
- Checking project health

All endpoints verified against https://supabase.com/docs/reference/api
Authentication: Bearer token (OAuth2 access_token or PAT).
"""

import logging
import requests

logger = logging.getLogger(__name__)

MANAGEMENT_API_BASE = "https://api.supabase.com/v1"


class SupabaseManagementClient:
    """Client for the Supabase Management API.

    Args:
        access_token: OAuth2 access token or PAT for authentication.
    """

    def __init__(self, access_token: str):
        self.access_token = access_token
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, timeout: int = 30) -> requests.Response:
        return requests.get(
            f"{MANAGEMENT_API_BASE}{path}", headers=self._headers, timeout=timeout
        )

    def _post(self, path: str, json: dict = None, timeout: int = 180) -> requests.Response:
        return requests.post(
            f"{MANAGEMENT_API_BASE}{path}",
            headers=self._headers,
            json=json,
            timeout=timeout,
        )

    def list_organizations(self) -> list[dict]:
        """GET /v1/orgs — List all organizations for the authenticated user."""
        resp = self._get("/orgs")
        if resp.status_code != 200:
            raise Exception(f"Failed to list organizations: HTTP {resp.status_code} — {resp.text}")
        return resp.json()

    def list_projects(self) -> list[dict]:
        """GET /v1/projects — List all projects for the authenticated user."""
        resp = self._get("/projects")
        if resp.status_code != 200:
            raise Exception(f"Failed to list projects: HTTP {resp.status_code} — {resp.text}")
        return resp.json()

    def create_project(
        self,
        name: str,
        organization_slug: str,
        db_password: str,
        region: str = "ap-southeast-1",
    ) -> dict:
        """POST /v1/projects — Create a new Supabase project.

        Args:
            name: Project display name.
            organization_slug: Organization slug (from list_organizations).
            db_password: Database password (min 12 chars recommended).
            region: Supabase region (default: ap-southeast-1).

        Returns:
            Project dict with keys: id, ref, name, status, etc.

        Raises:
            Exception: If creation fails (e.g., free tier limit reached).
        """
        body = {
            "name": name,
            "organization_slug": organization_slug,
            "db_pass": db_password,
            "region": region,
            "plan": "free",
        }
        resp = self._post("/projects", json=body)
        if resp.status_code != 201:
            raise Exception(
                f"Project creation failed: HTTP {resp.status_code} — {resp.text}"
            )
        return resp.json()

    def apply_migration(self, project_ref: str, name: str, query: str) -> dict:
        """POST /v1/projects/{ref}/database/migrations — Apply a SQL migration.

        Args:
            project_ref: The project reference ID.
            name: Migration name (e.g., "001_create_tables").
            query: SQL statements to execute.

        Returns:
            Migration result dict.

        Raises:
            Exception: If the migration fails.
        """
        body = {"name": name, "query": query}
        resp = self._post(
            f"/projects/{project_ref}/database/migrations",
            json=body,
            timeout=180,
        )
        if resp.status_code not in (200, 201):
            raise Exception(
                f"Migration '{name}' failed: HTTP {resp.status_code} — {resp.text}"
            )
        return resp.json()

    def get_project_api_keys(self, project_ref: str) -> list[dict]:
        """GET /v1/projects/{ref}/api-keys — Get project API keys.

        Returns a list of API key dicts, each with at least:
        - id: Key identifier (e.g., "anon", "service_role")
        - api_key: The actual key string
        """
        resp = self._get(f"/projects/{project_ref}/api-keys")
        if resp.status_code != 200:
            raise Exception(f"Failed to get API keys: HTTP {resp.status_code} — {resp.text}")
        return resp.json()

    def get_anon_api_key(self, project_ref: str) -> str:
        """Get the anon (public) API key for a project.

        Raises:
            Exception: If the anon key is not found.
        """
        keys = self.get_project_api_keys(project_ref)
        for key in keys:
            if key.get("id") == "anon" or key.get("name") == "anon key":
                return key["api_key"]
        raise Exception("Anon API key not found in project API keys response")

    def is_project_healthy(self, project_ref: str) -> bool:
        """GET /v1/projects/{ref}/endpoints/health — Check if all services are healthy.

        Returns True only if ALL services report HEALTHY status.
        """
        resp = self._get(f"/projects/{project_ref}/endpoints/health")
        if resp.status_code != 200:
            return False
        services = resp.json()
        if not services:
            return False
        return all(s.get("health") == "HEALTHY" for s in services)

    def get_project(self, project_ref: str) -> dict:
        """GET /v1/projects/{ref} — Get project details."""
        resp = self._get(f"/projects/{project_ref}")
        if resp.status_code != 200:
            raise Exception(f"Failed to get project: HTTP {resp.status_code} — {resp.text}")
        return resp.json()

    def run_query(self, project_ref: str, query: str) -> list[dict]:
        """POST /v1/projects/{ref}/database/query — Run a read-only SQL query.

        Used for schema version checks.

        Returns:
            List of row dicts from the query result.
        """
        resp = self._post(
            f"/projects/{project_ref}/database/query",
            json={"query": query},
            timeout=30,
        )
        if resp.status_code != 200:
            raise Exception(f"Query failed: HTTP {resp.status_code} — {resp.text}")
        data = resp.json()
        # The endpoint may return rows directly or wrapped in a result key
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        return []
