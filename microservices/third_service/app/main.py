import uvicorn

from fastapi import (
    FastAPI,
    status,
    Query,
    HTTPException
)

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Annotated

from core.config import get_settings
from core.dependencies import (
    get_neo4j_driver,
    get_redis_client,
    get_postgres_conn,
    GroupReportServiceDep
)
from schemas.schemas import GroupReportResponse


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    neo4j_driver = get_neo4j_driver()
    redis_client = get_redis_client()
    pg_conn = get_postgres_conn()

    yield

    neo4j_driver.close()
    redis_client.close()
    pg_conn.close()


app = FastAPI(
    title=f"{settings.app_name} - Лабораторная работа №3",
    description="Отчёт по группе: объём прослушанных часов лекций по специальным дисциплинам",
    version="1.0.0",
    lifespan=lifespan
)


@app.get(
    '/group_report',
    response_model=GroupReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Отчёт по группе",
    description="Возвращает отчёт по заданной группе с указанием объёма прослушанных и запланированных часов по специальным дисциплинам"
)
def get_group_report(
    service: GroupReportServiceDep,
    group_name: Annotated[str, Query(description="Название группы (например, ИКБО-01-23)")]
):
    try:
        result = service.get_group_report(group_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail='Not found')


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        reload=settings.debug,
        host='0.0.0.0',
        port=8000
    )