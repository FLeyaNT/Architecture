from fastapi import Depends
from redis import Redis
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase, Driver, Session
import psycopg2
from typing import Annotated, Generator
from functools import lru_cache

from core.config import get_settings
from repositories import (
    RedisRepo,
    ElasticRepo,
    Neo4jRepo,
    PostgresRepo
)
from services.student_service import StudentService

settings = get_settings()

# ---------- Redis ----------
@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True
    )
RedisClientDep = Annotated[Redis, Depends(get_redis_client)]

# ---------- Elasticsearch ----------
@lru_cache(maxsize=1)
def get_elastic_client() -> Elasticsearch:
    return Elasticsearch([settings.elastic_url])
ElasticClientDep = Annotated[Elasticsearch, Depends(get_elastic_client)]

# ---------- Neo4j ----------
@lru_cache(maxsize=1)
def get_neo4j_driver() -> Driver:
    return GraphDatabase.driver(
        uri=settings.neo4j_url,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
Neo4jDriverDep = Annotated[Driver, Depends(get_neo4j_driver)]

def get_neo4j_session(driver: Neo4jDriverDep) -> Generator[Session, None, None]:
    with driver.session() as session:
        yield session
Neo4jSessionDep = Annotated[Session, Depends(get_neo4j_session)]

# ---------- PostgreSQL ----------
def get_postgres_conn():
    conn = psycopg2.connect(settings.postgres_dsn)
    try:
        yield conn
    finally:
        conn.close()
PostgresConnDep = Annotated[psycopg2.extensions.connection, Depends(get_postgres_conn)]

# ---------- Репозитории ----------
def get_redis_repo(redis_client: RedisClientDep) -> RedisRepo:
    return RedisRepo(redis_client)
RedisRepoDep = Annotated[RedisRepo, Depends(get_redis_repo)]

def get_neo4j_repo(session: Neo4jSessionDep) -> Neo4jRepo:
    return Neo4jRepo(session)
Neo4jRepoDep = Annotated[Neo4jRepo, Depends(get_neo4j_repo)]

def get_elastic_repo(elastic_client: ElasticClientDep) -> ElasticRepo:
    return ElasticRepo(elastic_client)
ElasticRepoDep = Annotated[ElasticRepo, Depends(get_elastic_repo)]

def get_postgres_repo(conn: PostgresConnDep) -> PostgresRepo:
    return PostgresRepo(conn)
PostgresRepoDep = Annotated[PostgresRepo, Depends(get_postgres_repo)]

# ---------- Сервис ----------
def get_student_service(
    redis_repo: RedisRepoDep,
    elastic_repo: ElasticRepoDep,
    neo4j_repo: Neo4jRepoDep,
    postgres_repo: PostgresRepoDep
) -> StudentService:
    return StudentService(
        redis_repo=redis_repo,
        elastic_repo=elastic_repo,
        neo4j_repo=neo4j_repo,
        postgres_repo=postgres_repo
    )
StudentServiceDep = Annotated[StudentService, Depends(get_student_service)]