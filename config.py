"""
Configuration module for Shopline scraper
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Shopline API Configuration
    SHOPLINE_DOMAIN: str = "zgallerie"
    API_VERSION: str = "v20251201"
    API_TOKEN: str

    # Database Configuration
    DATABASE_URL: str

    # Application Settings
    DEFAULT_IMAGE_URL: str = "https://via.placeholder.com/300"
    LOG_LEVEL: str = "INFO"

    # Table Names
    TARGET_TABLE: str = "api_bc_skuinfo"
    HISTORY_TABLE: str = "hisrecord_bcsku"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
