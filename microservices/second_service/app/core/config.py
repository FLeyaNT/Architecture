from pydantic_settings import BaseSettings

from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = 'Second service'
    debug: bool = True

    # =========== neo4j ===========

    neo4j_host: str = 'neo4j'
    neo4j_port: int = 7687
    neo4j_user: str = 'neo4j'
    neo4j_password: str = 'password'

    # =========== PostgreSQL ===========

    pg_host: str = 'postgres'
    pg_port: int = 5432
    pg_database: str = 'university_system'
    pg_user: str = 'postgres'
    pg_password: str = 'postgres'

    @property
    def neo4j_url(self) -> str:
        return f'bolt://{self.neo4j_host}:{self.neo4j_port}'

    class Config:
        env_file = '.env'
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
