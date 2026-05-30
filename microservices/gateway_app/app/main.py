import uvicorn

from fastapi import (
    FastAPI, Request,
    Query, Path,
    status
)

from typing import Annotated, AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date

from core.config import get_settings
from schemas.auth import JWTTokenResponse
from core.dependencies import (
    RequireAuthDep,
    JWTAuthServiceDep,
    GatewayServiceDep,
    get_http_client
)


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    http_client = get_http_client()
    yield
    await http_client.aclose()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan
)


@app.post(
    '/jwt',
    response_model=JWTTokenResponse,
    status_code=status.HTTP_200_OK
)
def get_jwt_token(
    username: Annotated[str, Query(min_length=3)],
    jwt_service: JWTAuthServiceDep
):
    return jwt_service.generate_token(username)


@app.get('/first_lab')
async def get_attendance_stats(
    request: Request,
    gateway_service: GatewayServiceDep,
    _: RequireAuthDep,
    term: Annotated[str, Query()] = 'нейронные сети',
    date_from: Annotated[date, Query()] = date(2026, 2, 1),
    date_to: Annotated[date, Query()] = date(2026, 6, 30),
    limit: Annotated[int, Query(gt=0)] = 10
):
    query_params = request.query_params
    return await gateway_service.forward_request(
        request=request,
        service='first',
        path='attendance_stats',
        query_params=query_params
    )


@app.get('/second_lab')
async def get_course_info(
    request: Request,
    gateway_service: GatewayServiceDep,
    _: RequireAuthDep,
    course_name: Annotated[str, Query()] = 'Стратегическое и широкое интернет-решение',
    semester: Annotated[int, Query()] = 3,
    year: Annotated[int, Query()] = 2026
):
    query_params = request.query_params
    return await gateway_service.forward_request(
        request=request,
        service='second',
        path='course',
        query_params=query_params
    )


@app.get('/{service}/{path:path}')
async def gateway(
    request: Request,
    service: Annotated[str, Path()],
    path: Annotated[str, Path()],
    gateway_service: GatewayServiceDep,
    _: RequireAuthDep,
):
    return await gateway_service.forward_request(
        request=request,
        service=service,
        path=path
    )


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        reload=settings.debug,
        host='0.0.0.0',
        port=8000
    )
