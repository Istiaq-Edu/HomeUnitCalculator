"""Supabase OAuth2 PKCE flow utilities.

Handles the OAuth2 authorization code flow with PKCE (Proof Key for Code Exchange)
for secure authorization against the Supabase Management API.

Verified against: https://supabase.com/docs/guides/integrations/build-a-supabase-integration
"""

import hashlib
import base64
import secrets
import logging
import os
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────
# OAuth App credentials are loaded from oauth_credentials.py (gitignored).
# If that file doesn't exist (e.g., fresh clone), fall back to placeholders
# so the app runs but the Connect button won't work until credentials are set.
# Register at: https://supabase.com/dashboard/org/_/settings → OAuth Apps
# Set the redirect URI to: http://localhost:8765/callback

try:
    from src.core.oauth_credentials import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET
except ImportError:
    # Fallback: check environment variables (useful for dev and packaged builds)
    OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "YOUR_CLIENT_ID_HERE")
    OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE")

OAUTH_REDIRECT_URI = "http://localhost:8765/callback"

OAUTH_AUTHORIZE_URL = "https://api.supabase.com/v1/oauth/authorize"
OAUTH_TOKEN_URL = "https://api.supabase.com/v1/oauth/token"

# Local callback server port — must match the port in OAUTH_REDIRECT_URI
OAUTH_CALLBACK_PORT = 8765

# ─── PKCE ────────────────────────────────────────────────────────────────────


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code verifier and code challenge (S256).

    Returns:
        Tuple of (code_verifier, code_challenge).
        - verifier: 43-128 char random URL-safe string
        - challenge: base64url(SHA256(verifier)) without padding
    """
    verifier = secrets.token_urlsafe(64)
    # Ensure length is within RFC 7636 bounds (43-128 chars)
    if len(verifier) > 128:
        verifier = verifier[:128]

    challenge_bytes = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b"=").decode("ascii")

    return verifier, challenge


def build_authorize_url(code_challenge: str, state: str) -> str:
    """Build the OAuth2 authorize URL with PKCE parameters.

    Args:
        code_challenge: The PKCE code challenge (from generate_pkce_pair).
        state: Random state string for CSRF protection.

    Returns:
        Full authorize URL to open in the browser.
    """
    params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


# ─── Token Exchange ──────────────────────────────────────────────────────────


def exchange_code_for_tokens(code: str, code_verifier: str) -> dict:
    """Exchange an authorization code for access and refresh tokens.

    Calls POST https://api.supabase.com/v1/oauth/token with the authorization
    code and PKCE verifier. Uses HTTP Basic Auth with client_id:client_secret.

    Args:
        code: The authorization code from the callback redirect.
        code_verifier: The PKCE code verifier used to generate the challenge.

    Returns:
        Dict with keys: access_token, refresh_token, token_type, expires_in.

    Raises:
        Exception: If the token exchange fails (non-200 response).
    """
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "code_verifier": code_verifier,
    }

    resp = requests.post(
        OAUTH_TOKEN_URL,
        data=data,
        auth=(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )

    if resp.status_code != 200:
        raise Exception(
            f"Token exchange failed: HTTP {resp.status_code} — {resp.text}"
        )

    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an expired access token using the refresh token.

    Args:
        refresh_token: The refresh token from a previous exchange.

    Returns:
        Dict with keys: access_token, refresh_token, expires_in.

    Raises:
        Exception: If the refresh fails (non-200 response).
    """
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    resp = requests.post(
        OAUTH_TOKEN_URL,
        data=data,
        auth=(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )

    if resp.status_code != 200:
        raise Exception(
            f"Token refresh failed: HTTP {resp.status_code} — {resp.text}"
        )

    return resp.json()
