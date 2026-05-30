import uvicorn

from fastapi import (
    FastAPI,
    status,
    Query
)

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Annotated
from datetime import date

from core.config import get_settings
from core.dependencies import (
    get_neo4j_driver,
    get_pg_connection,
    CourseServiceDep,
)
from schemas.schemas import CourseInfoResponse


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    neo4j_driver = get_neo4j_driver()
    pg_conn = get_pg_connection()

    yield

    neo4j_driver.close()
    pg_conn.close()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan
)


@app.get(
    '/course',
    response_model=CourseInfoResponse
)
def get_course_info(
    course_service: CourseServiceDep,
    course_name: Annotated[str, Query()] = 'Стратегическое и широкое интернет-решение',
    semester: Annotated[int, Query()] = 3,
    year: Annotated[int, Query()] = 2026
):
    return course_service.get_course_info(
        course_name,
        semester,
        year
    )


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        reload=settings.debug,
        host='0.0.0.0',
        port=8000
    )
