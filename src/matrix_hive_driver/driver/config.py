from __future__ import annotations

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_prefix="", case_sensitive=False)

    driver_host: str = "0.0.0.0"
    driver_port: int = 7000

    hive_endpoint: str = "http://hive-runtime:8080"
    tool_proxy_endpoint: str = "http://matrix-architect:9000/tool-proxy"

    evidence_sink: str = "local"  # local|hub|s3|minio
    log_level: str = "info"

    # LLM provider: "none" | "ollama" (optional, for dev/CI verification only)
    # The main LLM lives in Matrix AI — this is a local fallback for development.
    llm_provider: str = "none"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"


settings = Settings()
