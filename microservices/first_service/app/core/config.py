from pydantic_settings import BaseSettings

from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = 'First service'
    debug: bool = True

    # =========== elasticSearch ===========
    
    elastic_host: str = 'elastic'
    elastic_port: int = 9200

    # =========== neo4j ===========

    neo4j_host: str = 'neo4j'
    neo4j_port: int = 7687
    neo4j_user: str = 'neo4j'
    neo4j_password: str = 'password'

    # =========== redis ===========

    redis_host: str = 'redis'
    redis_port: int = 6379

    # =========== postgres ===========

    postgres_host: str = 'postgres'
    postgres_port: int = 5432
    postgres_user: str = 'postgres'
    postgres_password: str = 'postgres'
    postgres_db: str = 'university_system'

    @property
    def neo4j_url(self) -> str:
        return f'bolt://{self.neo4j_host}:{self.neo4j_port}'
    
    @property
    def elastic_url(self) -> str:
        return f'http://{self.elastic_host}:{self.elastic_port}'
    
    @property
    def postgres_dsn(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    class Config:
        env_file = '.env'
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
