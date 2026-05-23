"""Configuration management for the Azure Resource Tagger application."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path


# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure Configuration
    azure_subscription_id: str
    azure_tenant_id: str
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    
    # Azure AI Foundry Configuration
    azure_foundry_endpoint: str
    azure_foundry_api_key: Optional[str] = None
    azure_foundry_deployment_name: str = "gpt-4o"
    azure_foundry_api_version: str = "2024-05-01-preview"
    
    # Cosmos DB Configuration
    cosmos_db_endpoint: Optional[str] = None
    cosmos_db_key: Optional[str] = None
    cosmos_db_database_name: str = "resourcetagger"
    cosmos_db_container_name: str = "resources"
    
    # Application Configuration
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    
    # Authentication Mode
    auth_mode: str = "service_principal"  # Only "service_principal" supported
    
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
