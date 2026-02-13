"""
Authentication configuration settings
"""
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class AuthSettings(BaseSettings):
    """Authentication settings"""
    # Google OAuth settings
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    REDIRECT_URI: str = os.getenv("REDIRECT_URI", "")
    
    # JWT settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:8000",
        "http://127.0.0.1:58628",
        "http://127.0.0.1:57954",  # Cascade browser preview
        "https://accounts.google.com"
    ]
    
    # Development mode
    DEV_MODE: bool = os.getenv("DEV_MODE", "false").lower() == "true"
    
    model_config = SettingsConfigDict(extra='ignore', env_file=".env", case_sensitive=True)

# Create settings instance
auth_settings = AuthSettings()