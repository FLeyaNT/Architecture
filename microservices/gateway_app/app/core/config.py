from pydantic_settings import BaseSettings

from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = 'API Gateway'
    debug: bool = True

    services: dict[str, str] = {
        'first': 'http://first_service:8000',
        'second': 'http://second_service:8000',
        'third': 'http://third_service:8000'
    }

    jwt_secret_key: str = 'dhdhf-5gsrhsh-afjjf-3thdhdhk-fdgsdkjdgas-dssgsd'
    jwt_algorithm: str = 'HS256'
    jwt_expire_minutes: int = 60 * 24

    class Config:
        env_file = '.env'
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
