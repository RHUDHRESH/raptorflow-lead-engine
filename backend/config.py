"""Configuration for the Raptorflow Lead Engine."""

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """App settings loaded from env vars."""

    # API
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./raptorflow_leads.db")

    # Ollama
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model_1b: str = os.getenv("OLLAMA_MODEL_1B", "gemma3:1b")
    ollama_model_4b: str = os.getenv("OLLAMA_MODEL_4B", "gemma3:4b")
    ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    ollama_vision_model: str = os.getenv("OLLAMA_VISION_MODEL", "llava")

    # Alternative Model Support (Mistral, Llama, etc.)
    enable_alternative_models: bool = os.getenv("ENABLE_ALTERNATIVE_MODELS", "false").lower() == "true"
    fallback_model_1b: str = os.getenv("FALLBACK_MODEL_1B", "mistral:7b")
    fallback_model_4b: str = os.getenv("FALLBACK_MODEL_4B", "llama3:8b")

    # Quantization Support
    use_quantized_models: bool = os.getenv("USE_QUANTIZED_MODELS", "false").lower() == "true"
    quantized_model_1b: str = os.getenv("QUANTIZED_MODEL_1B", "gemma3:1b-q4")
    quantized_model_4b: str = os.getenv("QUANTIZED_MODEL_4B", "gemma3:4b-q4")

    # Classifiers
    classifier_score_threshold: int = 70  # Only generate 4B dossier for leads > this score
    prefilter_score_threshold: int = int(os.getenv("PREFILTER_SCORE_THRESHOLD", "20"))  # Multi-stage: skip 4B if below this

    # Model Parameters - Dynamic Context Windows
    context_window_1b_short: int = int(os.getenv("CONTEXT_WINDOW_1B_SHORT", "4096"))  # For short text (<500 chars)
    context_window_1b_long: int = int(os.getenv("CONTEXT_WINDOW_1B_LONG", "8192"))  # For longer text
    context_window_4b: int = int(os.getenv("CONTEXT_WINDOW_4B", "8192"))
    context_length_threshold: int = int(os.getenv("CONTEXT_LENGTH_THRESHOLD", "500"))  # Chars to switch context window

    # Model Temperature Settings
    temperature_1b: float = float(os.getenv("TEMPERATURE_1B", "0.3"))
    temperature_4b: float = float(os.getenv("TEMPERATURE_4B", "0.5"))

    # Caching Configuration
    enable_response_cache: bool = os.getenv("ENABLE_RESPONSE_CACHE", "true").lower() == "true"
    cache_backend: str = os.getenv("CACHE_BACKEND", "memory")  # "memory" or "redis"
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "2592000"))  # 30 days default
    cache_max_size: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))  # LRU cache max entries
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Streaming Configuration
    enable_streaming: bool = os.getenv("ENABLE_STREAMING", "false").lower() == "true"
    stream_chunk_size: int = int(os.getenv("STREAM_CHUNK_SIZE", "512"))  # Bytes per chunk

    # Batch Processing
    batch_concurrency_limit: int = int(os.getenv("BATCH_CONCURRENCY_LIMIT", "5"))  # Max concurrent requests
    batch_enable_parallel: bool = os.getenv("BATCH_ENABLE_PARALLEL", "true").lower() == "true"

    # Health Monitoring
    enable_health_monitoring: bool = os.getenv("ENABLE_HEALTH_MONITORING", "true").lower() == "true"
    health_check_interval_seconds: int = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "300"))  # 5 min
    health_check_timeout_seconds: int = int(os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "10"))

    # Embeddings for ICP Matching
    enable_embeddings: bool = os.getenv("ENABLE_EMBEDDINGS", "false").lower() == "true"
    embedding_similarity_threshold: float = float(os.getenv("EMBEDDING_SIMILARITY_THRESHOLD", "0.7"))
    embedding_cache_ttl: int = int(os.getenv("EMBEDDING_CACHE_TTL", "604800"))  # 7 days

    # Prompt Templates
    prompt_template_path: str = os.getenv("PROMPT_TEMPLATE_PATH", "./prompts")
    enable_custom_prompts: bool = os.getenv("ENABLE_CUSTOM_PROMPTS", "false").lower() == "true"

    # GPU Acceleration
    enable_gpu_acceleration: bool = os.getenv("ENABLE_GPU_ACCELERATION", "false").lower() == "true"
    gpu_backend: str = os.getenv("GPU_BACKEND", "auto")  # "cuda", "vulkan", "metal", "auto"
    gpu_device_id: int = int(os.getenv("GPU_DEVICE_ID", "0"))
    gpu_memory_limit: str = os.getenv("GPU_MEMORY_LIMIT", "")  # e.g., "4GB"
    gpu_threads: int = int(os.getenv("GPU_THREADS", "4"))
    gpu_batch_size: int = int(os.getenv("GPU_BATCH_SIZE", "1"))

    class Config:
        env_file = ".env"
        case_sensitive = False
