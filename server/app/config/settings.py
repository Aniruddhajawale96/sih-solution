from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Farm"
    API_V1_PREFIX: str = "/api/v1"
    
    # JWT settings
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    
    # MongoDB settings
    MONGODB_URL: str
    MONGODB_DB: str = "agritech"
    
    # Weather API
    WEATHER_API_KEY: Optional[str] = None
    WEATHER_API: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()