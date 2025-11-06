"""
Configuração do banco de dados SQLite para armazenamento de usuários e jobs.
Usa SQLAlchemy para ORM.
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.utils import now

# Engine SQLite
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Necessário para SQLite
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


class User(Base):
    """Modelo de usuário para autenticação"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class Job(Base):
    """Modelo de job de transcrição"""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(Integer, index=True, nullable=False)
    filename = Column(String, nullable=False)
    file_size = Column(Integer)  # bytes
    file_url = Column(String, nullable=False)  # URL no OCI Object Storage

    status = Column(String, default="QUEUED")  # QUEUED, PROCESSING, COMPLETED, FAILED
    progress = Column(Float, default=0.0)  # 0.0 a 1.0

    # Resultados
    transcription_url = Column(String)  # URL do JSON completo no OCI
    transcription_text = Column(Text)  # Texto completo da transcrição
    edited_transcription = Column(Text)  # Transcrição editada pelo usuário
    speaker_names = Column(Text)  # JSON com mapeamento {speaker_id: nome_customizado}
    summary = Column(Text)  # Resumo gerado
    meeting_minutes = Column(Text)  # Ata de reunião gerada (JSON)
    duration_seconds = Column(Float)  # Duração do áudio

    # Metadados Azure Speech
    azure_job_id = Column(String)  # ID do job no Azure Speech Batch

    # Timestamps
    created_at = Column(DateTime, default=now)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Erro (se houver)
    error_message = Column(Text)


def get_db():
    """
    Dependency para obter sessão do banco de dados.
    Uso: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria todas as tabelas no banco de dados"""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Dropa todas as tabelas (usar com cuidado!)"""
    Base.metadata.drop_all(bind=engine)
