from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str = ""
    MONGODB_DB: str = ""
    AVIGILON_PROXY_URL: str = ""
    VERIFY_SSL: bool = False
    LOG_LEVEL: str = "INFO"
    SESSION_TOKEN: str = ""
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
