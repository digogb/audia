"""
Rotas para consultar status e informações de jobs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db, User, Job
from app.core.auth import get_current_user
from app.models.schemas import JobStatus

router = APIRouter()


@router.get("/{job_id}/status", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtém o status atual de um job de transcrição.

    Args:
        job_id: ID do job
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Status do job (QUEUED, PROCESSING, COMPLETED, FAILED)

    Raises:
        HTTPException 404: Se job não existir
        HTTPException 403: Se job não pertencer ao usuário
    """
    # Buscar job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )

    # Verificar se o job pertence ao usuário
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a este job"
        )

    return JobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message
    )
