from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    全局配置，通过 .env 加载
    """
    # OpenAI API 配置
    openai_api_key: str
    openai_chat_model: str = "gpt-4o-mini"
    openai_image_model: str = "dall-e-3"
    
    # LLM 服务配置
    llm_default_model: str = "gpt-4.1"
    llm_default_temperature: float = 0.7
    llm_streaming_enabled: bool = True
    
    # 缓存配置
    llm_cache_enabled: bool = True
    llm_cache_ttl: int = 3600  # 1小时

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"


# 全局单例配置
settings = Settings()
