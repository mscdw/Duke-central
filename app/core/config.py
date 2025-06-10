from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_BASE: str = ""
    MONGODB_DB: str = ""
    VERIFY_SSL: bool = False
    SESSION_TOKEN: str = ""
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
