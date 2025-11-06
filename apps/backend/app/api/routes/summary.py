"""
Rota para geração de resumos de transcrições.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db, User, Job
from app.core.auth import get_current_user
from app.workers.tasks import generate_summary_task
from app.models.schemas import SummaryResponse, GenerateSummaryRequest

router = APIRouter()


@router.get("/{job_id}", response_model=SummaryResponse)
async def get_summary(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtém o resumo de uma transcrição (se já foi gerado).

    Args:
        job_id: ID do job
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Resumo da transcrição

    Raises:
        HTTPException 404: Se job não existir ou resumo não foi gerado
        HTTPException 403: Se usuário não tiver acesso
    """
    # Buscar job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )

    # Verificar permissão
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )

    # Verificar se transcrição está completa
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcrição ainda não foi concluída"
        )

    # Verificar se resumo existe
    if not job.summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resumo ainda não foi gerado. Use POST /v1/summary/{job_id} para gerar."
        )

    return SummaryResponse(
        job_id=job.id,
        summary=job.summary,
        cached=True
    )


@router.post("/{job_id}", response_model=SummaryResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_summary(
    job_id: str,
    request: GenerateSummaryRequest = GenerateSummaryRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Gera (ou regenera) um resumo para uma transcrição.

    Se o resumo já existe, retorna o cached.
    Para forçar regeneração, delete o resumo antes.

    Args:
        job_id: ID do job
        request: Parâmetros de geração (opcional)
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Resumo gerado (ou cached se já existia)

    Raises:
        HTTPException 404: Se job não existir
        HTTPException 403: Se usuário não tiver acesso
        HTTPException 400: Se transcrição não estiver completa
    """
    logger.info(f"Solicitação de resumo para job {job_id}")

    # Buscar job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )

    # Verificar permissão
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )

    # Verificar se transcrição está completa
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcrição ainda não foi concluída"
        )

    # Verificar se já tem resumo
    if job.summary:
        logger.info(f"Resumo já existe para job {job_id}, retornando cached")
        return SummaryResponse(
            job_id=job.id,
            summary=job.summary,
            cached=True
        )

    # Enfileirar task de geração de resumo
    try:
        generate_summary_task.delay(
            job_id=job_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        logger.info(f"Task de resumo enfileirada para job {job_id}")

        # Retornar resposta indicando que está sendo gerado
        return SummaryResponse(
            job_id=job.id,
            summary="Resumo sendo gerado... Use GET para verificar quando estiver pronto.",
            cached=False
        )

    except Exception as e:
        logger.error(f"Erro ao enfileirar task de resumo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar resumo"
        )


@router.delete("/{job_id}")
async def delete_summary(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deleta o resumo de um job (para forçar regeneração).

    Args:
        job_id: ID do job
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Mensagem de sucesso

    Raises:
        HTTPException 404: Se job não existir
        HTTPException 403: Se usuário não tiver acesso
    """
    # Buscar job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )

    # Verificar permissão
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )

    # Deletar resumo
    job.summary = None
    db.commit()

    logger.info(f"Resumo deletado para job {job_id}")

    return {"message": "Resumo deletado com sucesso"}
