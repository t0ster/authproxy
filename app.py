"""
Simple reverse proxy which stores jwt token in encrypted cookie and adds
`Authorization: Bearer <jwt_token>` header to requests to the upstream server
"""
import base64
from os import environ
from os.path import join
from typing import Union

import uvicorn
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.starlette_client import OAuth, StarletteRemoteApp
from httpx import Response as HttpxResponse
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.datastructures import Secret
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware as BaseSessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp

from logger import logger

try:
    settings = __import__(environ.get("AUTHPROXY_SETTINGS", "settings"))
except ImportError:
    import settings_from_env as settings

if settings.DEBUG:
    logger.setLevel("DEBUG")

oauth = OAuth()
oauth.register(
    "auth0",
    client_id=settings.OAUTH_CLIENT_ID,
    client_secret=settings.OAUTH_CLIENT_SECRET,
    jwks_uri=settings.OAUTH_JWKS_URI,
    token_endpoint=settings.OAUTH_TOKEN_ENDPOINT,
    authorize_url=settings.OAUTH_AUTHORIZATION_ENDPOINT,
    scope=settings.OAUTH_SCOPE,
)


async def auth_facebook(request: Request):
    auth_client: StarletteRemoteApp = oauth.create_client("auth0")
    return await auth_client.authorize_redirect(
        request,
        settings.CALLBACK_URI,
        audience=settings.OAUTH_AUDIENCE,
        connection="facebook",
    )


async def callback(request: Request):
    auth_client = oauth.create_client("auth0")
    # TODO: Handle failed auth
    token: StarletteRemoteApp = await auth_client.authorize_access_token(request)
    del token["id_token"]
    request.session["token"] = token
    logger.debug(token)
    # TODO: Handle custom redirect
    return RedirectResponse(settings.CLIENT_DEFAULT_REDIRECT)


async def logout(request: Request):
    if "token" in request.session:
        del request.session["token"]
    return RedirectResponse(
        request.query_params.get("next", settings.CLIENT_DEFAULT_REDIRECT)
    )


def proxy(upstream_url: str, upstream_base_path: str):
    async def _proxy(request: Request):
        # pylint: disable=protected-access
        auth_client: AsyncOAuth2Client = oauth.create_client(
            "auth0"
        )._get_oauth_client()
        auth_client.token = request.session.get("token")
        qs = request.scope["query_string"]
        qs = f"?{qs}" if qs else ""
        upstream_path = request.path_params["upstream_path"]
        url = f"{upstream_url}{upstream_base_path}/{upstream_path}{qs}"
        req = auth_client.build_request(
            request.method,
            url,
            # TODO: May be do not send cookies to upstream
            headers=dict(request.headers),
            content=await request.body(),
        )

        if not auth_client.token:
            auth = None
        else:
            if auth_client.token.is_expired():
                await auth_client.ensure_active_token()
            auth = auth_client.token_auth

        res: HttpxResponse = await auth_client.send(
            req, auth=auth, stream=True, allow_redirects=False
        )
        await res.aread()
        response = Response(
            content=res.content,
            status_code=res.status_code,
            headers=res.headers,
            background=BackgroundTask(auth_client.aclose),
        )
        return response

    return _proxy


class SessionMiddleware(BaseSessionMiddleware):
    # pylint: disable=too-many-arguments,redefined-outer-name
    def __init__(
        self,
        app: ASGIApp,
        secret_key: Union[str, Secret],
        session_cookie: str = "session",
        max_age: int = 14 * 24 * 60 * 60,  # 14 days, in seconds
        same_site: str = "lax",
        https_only: bool = False,
        domain: Union[str, None] = None,
    ) -> None:
        super().__init__(
            app, secret_key, session_cookie, max_age, same_site, https_only
        )
        if domain:
            self.security_flags += "; domain=%s" % domain


def make_routes():
    return [
        Route(
            join(route["path"], "{upstream_path:path}"),
            proxy(route["upstream_url"], route["upstream_base_path"]),
            methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        )
        for route in settings.ROUTES
    ]


routes = [
    Route("/auth/facebook", auth_facebook),
    Route("/auth/callback", callback),
    Route("/auth/logout", logout),
] + make_routes()

middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=base64.urlsafe_b64decode(settings.SESSION_SECRET),
        session_cookie="authproxy_session",
        domain=settings.COOKIE_DOMAIN,
    ),
    Middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
        allow_credentials=True,
    ),
]

app = Starlette(routes=routes, middleware=middleware, debug=settings.DEBUG)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
