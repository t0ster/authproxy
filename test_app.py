from os import environ

from starlette.testclient import TestClient

import settings_tests as settings

environ["AUTHPROXY_SETTINGS"] = "settings_tests"
settings.DEBUG = False
# pylint: disable=wrong-import-position
from app import app


def test_app():
    client = TestClient(app)
    response = client.get("/auth/facebook", allow_redirects=False)
    assert response.headers.get("location")
