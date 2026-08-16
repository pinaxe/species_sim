"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # API
    api_title: str = "BioSim-Engine API"
    api_version: str = "0.1.0"
    api_description: str = "High-performance species dispersal simulator"

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    debug: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_cache_ttl: int = 3600

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # GBIF API
    gbif_api_url: str = "https://api.gbif.org/v1"
    gbif_timeout: int = 30

    # Climate data
    climate_cache_dir: str = "./data/climate"
    dem_cache_dir: str = "./data/dem"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
