"""Security helpers: bearer token authentication using constant-time comparison.

Authentication is configured entirely through environment variables
(MINIMCP_AUTH_TOKEN). No secrets are hardcoded or logged.
"""

import os

import hmac


def require_auth(request):
    """Validate the Authorization header against the configured token.

    The token is read from the environment at request time so tests can set
    MINIMCP_AUTH_TOKEN after the application module has been imported.

    Returns None when the request is authorized (or auth is disabled), or a
    Flask (response, status_code) tuple when unauthorized.
    """
    token = os.getenv("MINIMCP_AUTH_TOKEN", "")
    if not token:
        # Authentication not configured; allow all requests.
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return (
            {"error": "Unauthorized", "message": "Missing Bearer token"},
            401,
        )

    provided = auth_header[len("Bearer "):]
    if not hmac.compare_digest(provided, token):
        return (
            {"error": "Unauthorized", "message": "Invalid token"},
            401,
        )

    return None
