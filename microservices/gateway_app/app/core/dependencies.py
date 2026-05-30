from fastapi import (
    Depends,
    HTTPException,
    status,
    Security
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer
)

import httpx
from httpx import AsyncClient
from functools import lru_cache
from typing import Annotated

from services import (
    JWTAuthService,
    GatewayService
)
from core.config import get_settings


settings = get_settings()


security_scheme = HTTPBearer(
    auto_error=False,
    description='Введите JWT токен в формате: Bearer <token>'
)

AuthCredentialsDep = Annotated[
    HTTPAuthorizationCredentials,
    Security(security_scheme)
]


@lru_cache(maxsize=1)
def get_jwt_auth_service() -> JWTAuthService:
    return JWTAuthService()

JWTAuthServiceDep = Annotated[
    JWTAuthService,
    Depends(get_jwt_auth_service)
]


def get_current_user(
    credentials: AuthCredentialsDep,
    jwt_service: JWTAuthServiceDep
) -> dict:

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing authorization header',
            headers={
                'WWW-Authenticate': 'Bearer'
            }
        )
    
    token = credentials.credentials
    payload = jwt_service.verify_token(token)
    return payload

RequireAuthDep = Annotated[
    dict,
    Depends(get_current_user)
]


@lru_cache(maxsize=1)
def get_http_client() -> AsyncClient:
    return AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        )
    )

HttpClientDep = Annotated[
    AsyncClient,
    Depends(get_http_client)
]


def get_gateway_service(
    http_client: HttpClientDep
) -> GatewayService:
    return GatewayService(
        http_client=http_client,
        services=settings.services
    )

GatewayServiceDep = Annotated[
    GatewayService,
    Depends(get_gateway_service)
]
