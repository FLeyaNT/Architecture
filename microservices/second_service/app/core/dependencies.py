from fastapi import Depends

from neo4j import GraphDatabase, Driver, Session

from typing import Annotated, Generator
from functools import lru_cache

from core.config import get_settings
from repositories import (
    Neo4jRepo,
)
from services.course_service import CourseService


settings = get_settings()


@lru_cache(maxsize=1)
def get_neo4j_driver() -> Driver:
    return GraphDatabase.driver(
        uri=settings.neo4j_url,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

Neo4jDriverDep = Annotated[
    Driver,
    Depends(get_neo4j_driver)
]


def get_neo4j_session(
    driver: Neo4jDriverDep
) -> Generator[Session, None, None]:
    with driver.session() as session:
        yield session

Neo4jSessionDep = Annotated[
    Session,
    Depends(get_neo4j_session)
]


def get_neo4j_repo(
    session: Neo4jSessionDep
) -> Neo4jRepo:
    return Neo4jRepo(session)

Neo4jRepoDep = Annotated[
    Neo4jRepo,
    Depends(get_neo4j_repo)
]


def get_student_service(
    neo4j_repo: Neo4jRepoDep
) -> CourseService:
    return CourseService(
        neo4j_repo=neo4j_repo
    )

CourseServiceDep = Annotated[
    CourseService,
    Depends(get_student_service)
]
