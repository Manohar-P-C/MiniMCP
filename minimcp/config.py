"""Application configuration read from environment variables.

All values are read from the environment. No secrets are hardcoded.
Copy .env.example to .env and fill in placeholder values for local development.
"""

import os


class Config:
    SERVER_NAME = os.getenv("MINIMCP_SERVER_NAME", "MiniMCP")
    SERVER_VERSION = os.getenv("MINIMCP_SERVER_VERSION", "1.0.0")
    PROTOCOL_VERSION = os.getenv("MINIMCP_PROTOCOL_VERSION", "2025-03-26")

    # Bearer token used to protect the /mcp endpoint. When empty, authentication
    # is disabled (not recommended for production).
    AUTH_TOKEN = os.getenv("MINIMCP_AUTH_TOKEN", "")

    # Comma separated list of allowed CORS origins. "*" allows all origins.
    CORS_ORIGINS = [o.strip() for o in os.getenv("MINIMCP_CORS_ORIGINS", "*").split(",")]

    # Maximum request body size in bytes for the /mcp endpoint.
    MAX_REQUEST_SIZE = int(os.getenv("MINIMCP_MAX_REQUEST_SIZE", "1048576"))

    DEBUG = os.getenv("MINIMCP_DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("MINIMCP_LOG_LEVEL", "INFO")

    # Flask / server
    HOST = os.getenv("MINIMCP_HOST", "0.0.0.0")
    PORT = int(os.getenv("MINIMCP_PORT", "5000"))
