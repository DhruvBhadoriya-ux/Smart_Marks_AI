from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    SECRET_KEY: str = "smartmarks-ai-secure-prototype-key-32chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "smartmarks_ai"
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    # Storage
    UPLOAD_DIR: str = "temp_scans"
    EXPORT_DIR: str = "generated_exports"
    
    # OCR
    OCR_ENGINE: str = "RAPID_OCR"
    OCR_CONFIDENCE_THRESHOLD: float = 0.65

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
