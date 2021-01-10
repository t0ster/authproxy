import json
import sys
from os import environ

from cryptography import fernet

from logger import logger

DEBUG = environ.get("AUTHPROXY_DEBUG", False)
HOST = environ.get("HOST", "0.0.0.0")
PORT = int(environ.get("PORT", 8080))
CALLBACK_URI = environ["AUTHPROXY_CALLBACK_URI"]
CLIENT_DEFAULT_REDIRECT = environ["AUTHPROXY_CLIENT_DEFAULT_REDIRECT"]
CORS_ALLOWED_ORIGINS = json.loads(environ["AUTHPROXY_CORS_ALLOWED_ORIGINS"])
COOKIE_DOMAIN = environ["AUTHPROXY_COOKIE_DOMAIN"]
try:
    SESSION_SECRET = environ["AUTHPROXY_SESSION_SECRET"]
except KeyError:
    logger.error("Provide AUTHPROXY_SESSION_SECRET")
    logger.error("It should be 32 url-safe base64-encoded bytes")
    logger.error("For example: %s", fernet.Fernet.generate_key().decode())
    sys.exit()


OAUTH_DOMAIN = environ.get("AUTHPROXY_OAUTH_DOMAIN")
if not OAUTH_DOMAIN and not (
    environ.get("AUTHPROXY_OAUTH_JWKS_URI")
    and environ.get("AUTHPROXY_OAUTH_TOKEN_ENDPOINT")
    and environ.get("AUTHPROXY_AUTHORIZATION_ENDPOINT")
):
    logger.error(
        "Provide AUTHPROXY_OAUTH_DOMAIN or "
        "(AUTHPROXY_OAUTH_JWKS_URI, "
        "AUTHPROXY_OAUTH_TOKEN_ENDPOINT and AUTHPROXY_AUTHORIZATION_ENDPOINT"
    )
    sys.exit()
OAUTH_CLIENT_ID = environ["AUTHPROXY_OAUTH_CLIENT_ID"]
OAUTH_CLIENT_SECRET = environ["AUTHPROXY_OAUTH_CLIENT_SECRET"]
OAUTH_JWKS_URI = environ.get(
    "AUTHPROXY_OAUTH_JWKS_URI",
    f"https://{OAUTH_DOMAIN}/.well-known/jwks.json",
)
OAUTH_TOKEN_ENDPOINT = environ.get(
    "AUTHPROXY_OAUTH_TOKEN_ENDPOINT",
    f"https://{OAUTH_DOMAIN}/oauth/token",
)
OAUTH_AUTHORIZATION_ENDPOINT = environ.get(
    "AUTHPROXY_AUTHORIZATION_ENDPOINT", f"https://{OAUTH_DOMAIN}/authorize"
)
OAUTH_SCOPE = environ.get("AUTHPROXY_OAUTH_SCOPE")
OAUTH_AUDIENCE = environ.get("AUTHPROXY_OAUTH_AUDIENCE")

try:
    ROUTES = json.loads(environ["AUTHPROXY_ROUTES"])
except KeyError:
    logger.warning("You did not provide any routes (AUTHPROXY_ROUTES)")
    ROUTES = []
