import uvicorn

from fastapi import (
    FastAPI,
    status,
    Query,
    HTTPException
)

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Annotated
from datetime import date

from core.config import get_settings
from core.dependencies import (
    get_elastic_client,
    get_neo4j_driver,
    get_redis_client,
    StudentServiceDep
)
from schemas.schemas import AttendanceReportResponse


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    redis_client = get_redis_client()
    elastic_client = get_elastic_client()
    neo4j_driver = get_neo4j_driver()

    yield

    redis_client.close()
    elastic_client.close()
    neo4j_driver.close()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan
)


@app.get(
    '/attendance_stats',
    response_model=AttendanceReportResponse,
    status_code=status.HTTP_200_OK
)
def get_attendance_stats(
    student_service: StudentServiceDep,
    term: Annotated[str, Query()] = 'нейронные сети',
    date_from: Annotated[date, Query()] = date(2026, 2, 1),
    date_to: Annotated[date, Query()] = date(2026, 6, 30),
    limit: Annotated[int, Query(gt=0)] = 10
):
    try:
        return student_service.get_attendance_report(
            term,
            str(date_from),
            str(date_to),
            limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Not found'
        )


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        reload=settings.debug,
        host='0.0.0.0',
        port=8000
    )
