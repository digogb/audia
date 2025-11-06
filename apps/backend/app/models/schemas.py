"""
Schemas Pydantic para validação de dados da API.
Define modelos de request/response para todas as rotas.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, Field, field_validator, field_serializer, validator


def ensure_timezone(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Garante que um datetime tenha timezone (UTC).
    Se o datetime for naive (sem timezone), adiciona UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ============================================================================
# Auth Schemas
# ============================================================================

class UserRegister(BaseModel):
    """Schema para registro de novo usuário"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)

    @validator("username")
    def username_alphanumeric(cls, v):
        assert v.replace("_", "").replace("-", "").isalnum(), \
            "Username deve conter apenas letras, números, _ e -"
        return v


class UserLogin(BaseModel):
    """Schema para login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema de resposta com tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Schema para renovar access token"""
    refresh_token: str


class UserResponse(BaseModel):
    """Schema de resposta com dados do usuário"""
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Job/Transcription Schemas
# ============================================================================

class JobStatus(BaseModel):
    """Status de um job de transcrição"""
    job_id: str
    status: str  # QUEUED, PROCESSING, COMPLETED, FAILED
    progress: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class UploadResponse(BaseModel):
    """Resposta de upload de arquivo"""
    job_id: str
    filename: str
    file_size: int
    status: str
    message: str


class TranscriptionPhrase(BaseModel):
    """Uma frase da transcrição com diarização"""
    speaker: int
    text: str
    start_time: float  # segundos
    end_time: float  # segundos
    duration: float
    confidence: float


class TranscriptionSpeaker(BaseModel):
    """Informações de um speaker"""
    speaker_id: int
    texts: List[str]


class TranscriptionResponse(BaseModel):
    """Resposta completa com transcrição"""
    job_id: str
    filename: str
    status: str
    full_text: str
    duration_seconds: float
    phrases: List[TranscriptionPhrase]
    speakers: List[TranscriptionSpeaker]
    created_at: datetime
    completed_at: Optional[datetime]

    @field_serializer('created_at', 'completed_at', when_used='always')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        # Adicionar timezone se não tiver
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class TranscriptionListItem(BaseModel):
    """Item da lista de transcrições"""
    job_id: str
    filename: str
    status: str
    progress: float
    duration_seconds: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]

    @field_serializer('created_at', 'completed_at', when_used='always')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        # Adicionar timezone se não tiver
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class TranscriptionListResponse(BaseModel):
    """Lista paginada de transcrições"""
    items: List[TranscriptionListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Chat Schemas
# ============================================================================

class ChatMessage(BaseModel):
    """Mensagem de chat"""
    role: str  # "user" ou "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request de chat/pergunta"""
    question: str = Field(..., min_length=1, max_length=1000)
    chat_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Resposta do chat"""
    answer: str
    sources: List[Dict[str, Any]]  # Chunks usados como contexto
    job_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Transcription Editing Schemas
# ============================================================================

class UpdateSpeakerNamesRequest(BaseModel):
    """Request para atualizar nomes dos speakers"""
    speaker_names: Dict[str, str] = Field(..., description="Mapeamento {speaker_id: nome_customizado}")


class UpdateTranscriptionRequest(BaseModel):
    """Request para editar transcrição"""
    edited_text: str = Field(..., min_length=1, description="Texto editado da transcrição")


class UpdateTranscriptionResponse(BaseModel):
    """Resposta de atualização"""
    job_id: str
    message: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Summary Schemas
# ============================================================================

class SummaryResponse(BaseModel):
    """Resposta com resumo"""
    job_id: str
    summary: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    cached: bool = False  # Se foi carregado do cache


class GenerateSummaryRequest(BaseModel):
    """Request para gerar resumo (opcional: customizar parâmetros)"""
    max_tokens: Optional[int] = Field(default=500, ge=100, le=2000)
    temperature: Optional[float] = Field(default=0.3, ge=0.0, le=1.0)


# ============================================================================
# Meeting Minutes Schemas
# ============================================================================

class MeetingTopic(BaseModel):
    """Tópico discutido na reunião"""
    topic: str
    discussion: str


class MeetingActionItem(BaseModel):
    """Item de ação da reunião"""
    item: str
    responsible: str
    deadline: str


class MeetingMinutesData(BaseModel):
    """Estrutura da ata de reunião"""
    title: str
    summary: str
    topics: List[MeetingTopic]
    action_items: List[MeetingActionItem]
    decisions: List[str]
    next_steps: List[str]


class MeetingMinutesResponse(BaseModel):
    """Resposta com ata de reunião"""
    job_id: str
    meeting_minutes: MeetingMinutesData
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    cached: bool = False


class GenerateMeetingMinutesRequest(BaseModel):
    """Request para gerar ata de reunião"""
    max_tokens: Optional[int] = Field(default=1500, ge=500, le=3000)
    temperature: Optional[float] = Field(default=0.3, ge=0.0, le=1.0)


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema padrão de erro"""
    error: str
    detail: Optional[str] = None
    status_code: int


class ValidationErrorDetail(BaseModel):
    """Detalhe de erro de validação"""
    loc: List[str]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Resposta de erro de validação"""
    detail: List[ValidationErrorDetail]


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Status de saúde da aplicação"""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadinessResponse(BaseModel):
    """Status de prontidão da aplicação"""
    ready: bool
    services: Dict[str, bool]  # redis, database, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Stats Schemas
# ============================================================================

class JobStats(BaseModel):
    """Estatísticas de jobs"""
    total_jobs: int
    queued: int
    processing: int
    completed: int
    failed: int


class UserStats(BaseModel):
    """Estatísticas do usuário"""
    total_uploads: int
    total_duration_hours: float
    uploads_this_month: int
    storage_used_mb: float
