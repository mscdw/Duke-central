from functools import lru_cache
from pydantic import validator
import re
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AWS_REGION: str = ""
    MONGODB_BASE: str = ""
    MONGODB_DB: str = ""
    VERIFY_SSL: bool = False
    SESSION_TOKEN: str = ""
    S3_FACE_IMAGE_BUCKET: str = ""

    @validator('AWS_REGION')
    def valid_aws_region(cls, v: str) -> str:
        """Ensures the AWS region string is in the correct format."""
        if not re.match(r'^[a-z]{2}-[a-z]+-\d$', v):
            raise ValueError(f"'{v}' is not a valid AWS region format. Expected format like 'us-east-2'.")
        return v

    class Config:
        env_file = ".env"

######################################
# Disabled caching because it is extremely confusing when the services don't pick up config changes
# example incorrect aws region name caused presigned urls to fail
# and then continued to fail even after correcting .env and 
# restarting services
######################################

# @lru_cache()
def get_settings():
    return Settings()
