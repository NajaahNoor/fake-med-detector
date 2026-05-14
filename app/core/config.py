"""
app/core/config.py
-------------------
Central configuration management using environment variables and python-dotenv.
"""

from dotenv import load_dotenv
import os
from typing import List

# Load .env file
load_dotenv()


class Settings:
    """Application settings loaded from .env file."""
    
    # App
    app_name: str = os.getenv("APP_NAME", "Fake Medicine Detector")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # OpenRouter API
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    primary_model: str = os.getenv("PRIMARY_MODEL", "openai/gpt-oss-20b:free")
    fallback_models: str = os.getenv("FALLBACK_MODELS", "z-ai/glm-4.5-air:free,openrouter/owl-alpha")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/drap.db")
    db_path: str = os.getenv("DB_PATH", "./data/drap.db")
    
    # API
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_reload: bool = os.getenv("API_RELOAD", "True").lower() == "true"
    cors_origins: List[str] = [
        
        "http://localhost:3000",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8501"
    ]
    
    # File Upload
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "./data/uploads")
    
    # OCR Configuration
    flags_use_onednn: int = int(os.getenv("FLAGS_USE_ONEDNN", "0"))
    flags_use_mkldnn: int = int(os.getenv("FLAGS_USE_MKLDNN", "0"))
    ocr_version: str = os.getenv("OCR_VERSION", "PP-OCRv4")
    ocr_lang: str = os.getenv("OCR_LANG", "en")
    ocr_use_angle_cls: bool = os.getenv("OCR_USE_ANGLE_CLS", "True").lower() == "true"
    
    @property
    def fallback_models_list(self) -> List[str]:
        """Convert fallback models string to list."""
        return [m.strip() for m in self.fallback_models.split(",")]
    
    def get_all_models(self) -> List[str]:
        """Get primary model and fallback models as a list."""
        return [self.primary_model] + self.fallback_models_list


# Global settings instance
settings = Settings()
