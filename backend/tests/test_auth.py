"""Tests for JWT authentication on GET /hello.

Strategy:
- AUTH_ENABLED is False by default, so requests pass without tokens.
- Tests that enable auth patch settings and stub _decode_google_jwt
  so no real network call to Google is made.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def get_hello(client: TestClient, headers: dict | None = None):
    return client.get("/hello", headers=headers or {})


class TestAuthEnabled:
    """All tests in this class run with auth_enabled=True."""

    @pytest.fixture(autouse=True)
    def enable_auth(self):
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.auth_enabled = True
            mock_settings.google_client_id = "test-client-id"
            mock_settings.allowed_emails = ["allowed@example.com"]
            yield mock_settings

    def test_no_token_returns_401(self, client):
        resp = get_hello(client)
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "Unauthorized"

    def test_malformed_bearer_returns_401(self, client):
        resp = get_hello(client, headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401

    def test_unauthorized_email_returns_403(self, client):
        claims = {"email": "other@example.com", "email_verified": True}
        with patch("app.core.auth._decode_google_jwt", new=AsyncMock(return_value=claims)):
            resp = get_hello(client, headers={"Authorization": "Bearer fake.token"})
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "Forbidden"

    def test_unverified_email_returns_401(self, client):
        claims = {"email": "allowed@example.com", "email_verified": False}
        with patch("app.core.auth._decode_google_jwt", new=AsyncMock(return_value=claims)):
            resp = get_hello(client, headers={"Authorization": "Bearer fake.token"})
        assert resp.status_code == 401

    def test_valid_bearer_returns_200(self, client):
        claims = {"email": "allowed@example.com", "email_verified": True}
        with patch("app.core.auth._decode_google_jwt", new=AsyncMock(return_value=claims)):
            resp = get_hello(client, headers={"Authorization": "Bearer fake.token"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "allowed@example.com"

    def test_valid_x_ms_token_header_returns_200(self, client):
        claims = {"email": "allowed@example.com", "email_verified": True}
        with patch("app.core.auth._decode_google_jwt", new=AsyncMock(return_value=claims)):
            resp = get_hello(client, headers={"X-MS-TOKEN-GOOGLE-ID-TOKEN": "fake.token"})
        assert resp.status_code == 200

    def test_bearer_takes_priority_over_x_ms_header(self, client):
        claims = {"email": "allowed@example.com", "email_verified": True}
        with patch(
            "app.core.auth._decode_google_jwt", new=AsyncMock(return_value=claims)
        ) as mock_decode:
            get_hello(
                client,
                headers={
                    "Authorization": "Bearer bearer.token",
                    "X-MS-TOKEN-GOOGLE-ID-TOKEN": "ms.token",
                },
            )
        mock_decode.assert_awaited_once_with("bearer.token")


class TestAuthDisabled:
    def test_no_token_returns_200_when_auth_disabled(self, client):
        resp = get_hello(client)
        assert resp.status_code == 200
        assert resp.json()["email"] is None
