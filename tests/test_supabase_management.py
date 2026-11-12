"""Tests for Supabase Management API client."""

from unittest.mock import patch, MagicMock
import pytest

from src.core.supabase_management import SupabaseManagementClient


def _mock_resp(status, json_data):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    r.text = str(json_data)
    return r


@patch("src.core.supabase_management.requests.get")
def test_list_organizations_returns_org_list(mock_get):
    mock_get.return_value = _mock_resp(200, [
        {"id": "org-1", "name": "My Org", "slug": "my-org"}
    ])
    client = SupabaseManagementClient("test_token")
    orgs = client.list_organizations()
    assert len(orgs) == 1
    assert orgs[0]["slug"] == "my-org"
    # Verify the correct endpoint was called
    call_url = mock_get.call_args[0][0]
    assert "/v1/organizations" in call_url


@patch("src.core.supabase_management.requests.get")
def test_list_projects_returns_project_list(mock_get):
    mock_get.return_value = _mock_resp(200, [
        {"id": 1, "ref": "abcdef", "name": "My Project", "status": "ACTIVE"}
    ])
    client = SupabaseManagementClient("test_token")
    projects = client.list_projects()
    assert len(projects) == 1
    assert projects[0]["ref"] == "abcdef"


@patch("src.core.supabase_management.requests.get")
def test_list_projects_returns_empty_list_when_no_projects(mock_get):
    mock_get.return_value = _mock_resp(200, [])
    client = SupabaseManagementClient("test_token")
    assert client.list_projects() == []


@patch("src.core.supabase_management.requests.post")
def test_create_project_sends_correct_body(mock_post):
    mock_post.return_value = _mock_resp(201, {
        "id": 1, "ref": "newproject", "name": "HUC Data"
    })
    client = SupabaseManagementClient("test_token")
    result = client.create_project(
        name="HUC Data",
        organization_slug="my-org",
        db_password="SecurePass123!",
        region="ap-southeast-1",
    )
    assert result["ref"] == "newproject"
    call_args = mock_post.call_args
    body = call_args[1]["json"]
    assert body["name"] == "HUC Data"
    assert body["organization_slug"] == "my-org"
    assert body["db_pass"] == "SecurePass123!"


@patch("src.core.supabase_management.requests.post")
def test_apply_migration_sends_name_and_query(mock_post):
    mock_post.return_value = _mock_resp(200, {"id": 1})
    client = SupabaseManagementClient("test_token")
    client.apply_migration(
        project_ref="abcdef",
        name="001_create_tables",
        query="CREATE TABLE test (id INT);",
    )
    call_args = mock_post.call_args
    body = call_args[1]["json"]
    assert body["name"] == "001_create_tables"
    assert body["query"] == "CREATE TABLE test (id INT);"


@patch("src.core.supabase_management.requests.get")
def test_get_project_api_keys_returns_keys(mock_get):
    mock_get.return_value = _mock_resp(200, [
        {"id": "anon", "name": "anon key", "api_key": "eyJhbGci***anon_key***"}
    ])
    client = SupabaseManagementClient("test_token")
    keys = client.get_project_api_keys("abcdef")
    assert len(keys) == 1
    assert keys[0]["api_key"] == "eyJhbGci***anon_key***"


@patch("src.core.supabase_management.requests.get")
def test_get_project_api_keys_finds_anon_key(mock_get):
    mock_get.return_value = _mock_resp(200, [
        {"id": "service_role", "api_key": "service_key_here"},
        {"id": "anon", "api_key": "anon_key_here"},
    ])
    client = SupabaseManagementClient("test_token")
    anon_key = client.get_anon_api_key("abcdef")
    assert anon_key == "anon_key_here"


@patch("src.core.supabase_management.requests.get")
def test_get_project_health_returns_true_for_healthy(mock_get):
    mock_get.return_value = _mock_resp(200, [
        {"name": "db", "health": "HEALTHY"},
        {"name": "rest", "health": "HEALTHY"},
    ])
    client = SupabaseManagementClient("test_token")
    assert client.is_project_healthy("abcdef") is True


@patch("src.core.supabase_management.requests.get")
def test_get_project_health_returns_false_for_unhealthy(mock_get):
    mock_get.return_value = _mock_resp(200, [
        {"name": "db", "health": "UNHEALTHY"},
    ])
    client = SupabaseManagementClient("test_token")
    assert client.is_project_healthy("abcdef") is False


@patch("src.core.supabase_management.requests.post")
def test_create_project_raises_on_error(mock_post):
    mock_post.return_value = _mock_resp(400, {"message": "Limit reached"})
    client = SupabaseManagementClient("test_token")
    with pytest.raises(Exception, match="Project creation failed"):
        client.create_project(
            name="test", organization_slug="org", db_password="pass"
        )
