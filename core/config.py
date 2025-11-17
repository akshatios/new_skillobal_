from pathlib import Path
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    MONGODB_URI: str
    DB_NAME: str
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in the .env file

class JWTSettings(BaseSettings):
    SUGAR_VALUE: str
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in the .env file


class TencentSettings(BaseSettings):
    TENCENT_SECRET_ID: str
    TENCENT_SUB_APP_ID: str
    TENCENT_SECRET_KEY: str
    TENCENT_REGION: str
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in the .env file


# Instantiate settings
db_settings = DatabaseSettings()
jwt_settings = JWTSettings()
settings = TencentSettings()