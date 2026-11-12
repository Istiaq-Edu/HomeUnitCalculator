"""Tests for Supabase OAuth2 PKCE flow utilities.

Tests cover:
- PKCE pair generation (verifier + challenge)
- Authorize URL building with all required params
- Token exchange (code → access + refresh)
- Token refresh
- Local callback server (code capture, error capture, state mismatch)
"""

import hashlib
import base64
import threading
import time
import urllib.request
from unittest.mock import patch, MagicMock

import pytest

from src.core.supabase_oauth import (
    generate_pkce_pair,
    build_authorize_url,
    exchange_code_for_tokens,
    refresh_access_token,
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
)
from src.ui.oauth_callback_server import OAuthCallbackServer


# ─── PKCE Pair Generation ───


def test_generate_pkce_pair_returns_verifier_and_challenge():
    verifier, challenge = generate_pkce_pair()
    assert len(verifier) >= 43
    assert len(verifier) <= 128
    # Challenge must be base64url(SHA256(verifier)) without padding
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    assert challenge == expected


def test_generate_pkce_pair_is_random():
    v1, c1 = generate_pkce_pair()
    v2, c2 = generate_pkce_pair()
    assert v1 != v2
    assert c1 != c2


# ─── Authorize URL Building ───


def test_build_authorize_url_contains_required_params():
    verifier, challenge = generate_pkce_pair()
    state = "random_state_123"
    url = build_authorize_url(challenge, state)
    assert "https://api.supabase.com/v1/oauth/authorize" in url
    assert "response_type=code" in url
    assert f"client_id={OAUTH_CLIENT_ID}" in url
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert f"state={state}" in url


def test_build_authorize_url_redirect_uri_is_url_encoded():
    _, challenge = generate_pkce_pair()
    url = build_authorize_url(challenge, "state")
    # localhost:8765/callback must be URL-encoded in the query string
    assert "localhost%3A8765" in url


# ─── Token Exchange ───


@patch("src.core.supabase_oauth.requests.post")
def test_exchange_code_for_tokens_returns_access_and_refresh(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "sbp_oauth_test_access",
        "refresh_token": "sbp_oauth_test_refresh",
        "token_type": "bearer",
        "expires_in": 3600,
    }
    mock_post.return_value = mock_resp

    result = exchange_code_for_tokens(
        code="test_code",
        code_verifier="test_verifier",
    )

    assert result["access_token"] == "sbp_oauth_test_access"
    assert result["refresh_token"] == "sbp_oauth_test_refresh"
    assert result["expires_in"] == 3600


@patch("src.core.supabase_oauth.requests.post")
def test_exchange_code_for_tokens_sends_correct_form_data(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "a", "refresh_token": "r"}
    mock_post.return_value = mock_resp

    exchange_code_for_tokens(code="my_code", code_verifier="my_verifier")

    call_args = mock_post.call_args
    assert "https://api.supabase.com/v1/oauth/token" in call_args[0][0]
    data = call_args[1]["data"]
    assert data["grant_type"] == "authorization_code"
    assert data["code"] == "my_code"
    assert data["code_verifier"] == "my_verifier"
    assert data["redirect_uri"] == OAUTH_REDIRECT_URI


@patch("src.core.supabase_oauth.requests.post")
def test_exchange_code_raises_on_error_status(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "invalid_grant"
    mock_post.return_value = mock_resp

    with pytest.raises(Exception, match="Token exchange failed"):
        exchange_code_for_tokens(code="bad", code_verifier="bad")


# ─── Token Refresh ───


@patch("src.core.supabase_oauth.requests.post")
def test_refresh_access_token_returns_new_tokens(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "sbp_oauth_new_access",
        "refresh_token": "sbp_oauth_new_refresh",
        "expires_in": 3600,
    }
    mock_post.return_value = mock_resp

    result = refresh_access_token("old_refresh_token")

    assert result["access_token"] == "sbp_oauth_new_access"
    call_args = mock_post.call_args
    data = call_args[1]["data"]
    assert data["grant_type"] == "refresh_token"
    assert data["refresh_token"] == "old_refresh_token"


# ─── Callback Server ───


def test_callback_server_captures_code_and_state():
    server = OAuthCallbackServer(port=8766)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)

    url = "http://localhost:8766/callback?code=test_auth_code_123&state=my_state"
    urllib.request.urlopen(url)

    time.sleep(0.3)
    server.shutdown()

    assert server.auth_code == "test_auth_code_123"
    assert server.state == "my_state"
    assert server.received is True


def test_callback_server_captures_error():
    server = OAuthCallbackServer(port=8767)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)

    url = "http://localhost:8767/callback?error=access_denied&error_description=user+denied"
    # Server returns 400 for error responses — urlopen raises HTTPError
    try:
        urllib.request.urlopen(url)
    except urllib.error.HTTPError:
        pass  # Expected — the server correctly returns 400

    time.sleep(0.3)
    server.shutdown()

    assert server.received is True
    assert server.error == "access_denied"
    assert server.auth_code is None


def test_callback_server_state_mismatch_detected():
    server = OAuthCallbackServer(port=8768, expected_state="correct_state")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)

    url = "http://localhost:8768/callback?code=some_code&state=wrong_state"
    # Server returns 400 for state mismatch — urlopen raises HTTPError
    try:
        urllib.request.urlopen(url)
    except urllib.error.HTTPError:
        pass  # Expected — the server correctly returns 400

    time.sleep(0.3)
    server.shutdown()

    assert server.state_mismatch is True
