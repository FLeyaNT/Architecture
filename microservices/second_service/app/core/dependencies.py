from fastapi import Depends

from redis import Redis
import psycopg2
from neo4j import GraphDatabase, Driver, Session

from typing import Annotated, Generator
from functools import lru_cache

from core.config import get_settings
from repositories import (
    Neo4jRepo,
    PgRepo
)
from services.course_service import CourseService


settings = get_settings()


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True
    )

RedisClientDep = Annotated[
    Redis,
    Depends(get_redis_client)
]


@lru_cache(maxsize=1)
def get_pg_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        database=settings.pg_database,
        user=settings.pg_user,
        password=settings.pg_password
    )

PgConnectionDep = Annotated[
    psycopg2.extensions.connection,
    Depends(get_pg_connection)
]


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


def get_pg_repo(
    connection: PgConnectionDep
) -> PgRepo:
    return PgRepo(connection)

PgRepoDep = Annotated[
    PgRepo,
    Depends(get_pg_repo)
]


def get_student_service(
    pg_repo: PgRepoDep,
    neo4j_repo: Neo4jRepoDep
) -> CourseService:
    return CourseService(
        pg_repo=pg_repo,
        neo4j_repo=neo4j_repo
    )

CourseServiceDep = Annotated[
    CourseService,
    Depends(get_student_service)
]
