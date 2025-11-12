"""
Configuração central da aplicação usando Pydantic Settings.
Carrega variáveis de ambiente e fornece validação de tipos.
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente"""

    # Azure Speech Service
    AZURE_SPEECH_REGION: str = Field(..., description="Região do Azure Speech Service")
    AZURE_SPEECH_KEY: str = Field(..., description="Chave de API do Azure Speech")

    # Azure OpenAI Service
    AZURE_OPENAI_ENDPOINT: str = Field(..., description="Endpoint do Azure OpenAI")
    AZURE_OPENAI_KEY: str = Field(..., description="Chave de API do Azure OpenAI")
    AZURE_OPENAI_DEPLOYMENT: str = Field(default="gpt-4", description="Nome do deployment GPT-4")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = Field(
        default="text-embedding-ada-002",
        description="Nome do deployment de embeddings"
    )
    AZURE_OPENAI_API_VERSION: str = Field(
        default="2024-02-15-preview",
        description="Versão da API Azure OpenAI"
    )

    # Oracle Cloud Infrastructure
    OCI_NAMESPACE: str = Field(..., description="Namespace do OCI Object Storage")
    OCI_BUCKET: str = Field(default="audia-media", description="Nome do bucket OCI")
    OCI_REGION: str = Field(default="sa-saopaulo-1", description="Região OCI")
    OCI_COMPARTMENT_OCID: str = Field(..., description="OCID do compartment OCI")
    OCI_CONFIG_PATH: str = Field(default="~/.oci/config", description="Caminho do config OCI")
    OCI_PROFILE: str = Field(default="DEFAULT", description="Profile OCI a usar")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="URL do Redis")
    REDIS_HOST: str = Field(default="localhost", description="Host do Redis")
    REDIS_PORT: int = Field(default=6379, description="Porta do Redis")
    REDIS_DB: int = Field(default=0, description="Database do Redis")

    # FAISS
    FAISS_PATH: str = Field(
        default="/app/data/faiss_store",
        description="Caminho para armazenar índices FAISS"
    )

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(..., description="Chave secreta para JWT (min 32 chars)")
    JWT_ALGORITHM: str = Field(default="HS256", description="Algoritmo JWT")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Tempo de expiração do access token em minutos"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Tempo de expiração do refresh token em dias"
    )

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./data/audia.db",
        description="URL de conexão do banco de dados"
    )

    # Application
    APP_NAME: str = Field(default="Audia", description="Nome da aplicação")
    APP_VERSION: str = Field(default="1.0.0", description="Versão da aplicação")
    DEBUG: bool = Field(default=False, description="Modo debug")
    LOG_LEVEL: str = Field(default="INFO", description="Nível de log")

    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Origens permitidas para CORS (separadas por vírgula)"
    )

    @validator("CORS_ORIGINS")
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Converte string de origens em lista"""
        return [origin.strip() for origin in v.split(",")]

    # Upload Limits
    MAX_UPLOAD_SIZE_MB: int = Field(default=500, description="Tamanho máximo de upload em MB")
    MAX_UPLOADS_PER_HOUR: int = Field(default=3, description="Máximo de uploads por hora")
    ALLOWED_EXTENSIONS: str = Field(
        default="mp3,wav,mp4,m4a,avi,mov,webm,asf",
        description="Extensões permitidas (separadas por vírgula)"
    )

    @validator("ALLOWED_EXTENSIONS")
    def parse_allowed_extensions(cls, v: str) -> List[str]:
        """Converte string de extensões em lista"""
        return [ext.strip().lower() for ext in v.split(",")]

    # Rate Limiting
    RATE_LIMIT_CHAT: str = Field(default="20/minute", description="Rate limit para chat")
    RATE_LIMIT_UPLOAD: str = Field(default="3/hour", description="Rate limit para uploads")

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="URL do broker Celery"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Backend de resultados Celery"
    )
    CELERY_TASK_TRACK_STARTED: bool = Field(
        default=True,
        description="Rastrear início de tasks"
    )
    CELERY_TASK_TIME_LIMIT: int = Field(
        default=7200,
        description="Limite de tempo para tasks (segundos)"
    )
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=7000,
        description="Limite suave de tempo para tasks (segundos)"
    )

    # Processing
    CHUNK_SIZE_TOKENS: int = Field(
        default=512,
        description="Tamanho dos chunks para embeddings"
    )
    CHUNK_OVERLAP_TOKENS: int = Field(
        default=50,
        description="Overlap entre chunks"
    )
    MAX_CONTEXT_CHUNKS: int = Field(
        default=5,
        description="Número máximo de chunks de contexto para RAG"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instância global de configurações
settings = Settings()
