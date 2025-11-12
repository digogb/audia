"""
Rota para geração de atas de reunião de transcrições.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from loguru import logger
import json

from app.core.database import get_db, User, Job
from app.core.auth import get_current_user
from app.workers.tasks import generate_meeting_minutes_task
from app.models.schemas import (
    MeetingMinutesResponse,
    GenerateMeetingMinutesRequest,
    MeetingMinutesData
)
from app.services.azure_openai import azure_openai_service

router = APIRouter()


@router.get("/{job_id}", response_model=MeetingMinutesResponse)
async def get_meeting_minutes(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtém a ata de reunião de uma transcrição (se já foi gerada).

    Args:
        job_id: ID do job
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Ata de reunião da transcrição

    Raises:
        HTTPException 404: Se job não existir ou ata não foi gerada
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

    # Verificar se ata existe
    if not job.meeting_minutes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ata ainda não foi gerada. Use POST /v1/meeting-minutes/{job_id} para gerar."
        )

    # Parse JSON
    minutes_data = json.loads(job.meeting_minutes)

    return MeetingMinutesResponse(
        job_id=job.id,
        meeting_minutes=MeetingMinutesData(**minutes_data),
        cached=True
    )


@router.post("/{job_id}", response_model=MeetingMinutesResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_meeting_minutes(
    job_id: str,
    request: GenerateMeetingMinutesRequest = GenerateMeetingMinutesRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Gera (ou regenera) uma ata de reunião para uma transcrição.

    Se a ata já existe, retorna a cached.
    Para forçar regeneração, delete a ata antes.

    Args:
        job_id: ID do job
        request: Parâmetros de geração (opcional)
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Ata de reunião gerada (ou cached se já existia)

    Raises:
        HTTPException 404: Se job não existir
        HTTPException 403: Se usuário não tiver acesso
        HTTPException 400: Se transcrição não estiver completa
    """
    logger.info(f"Solicitação de ata de reunião para job {job_id}")

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

    # Verificar se já tem ata
    if job.meeting_minutes:
        logger.info(f"Ata já existe para job {job_id}, retornando cached")
        minutes_data = json.loads(job.meeting_minutes)
        return MeetingMinutesResponse(
            job_id=job.id,
            meeting_minutes=MeetingMinutesData(**minutes_data),
            cached=True
        )

    # Enfileirar task de geração de ata
    try:
        generate_meeting_minutes_task.delay(
            job_id=job_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        logger.info(f"Task de ata de reunião enfileirada para job {job_id}")

        # Retornar resposta indicando que está sendo gerada
        # Criar estrutura vazia temporária
        temp_minutes = MeetingMinutesData(
            title="Gerando...",
            summary="Ata de reunião sendo gerada... Use GET para verificar quando estiver pronta.",
            topics=[],
            action_items=[],
            decisions=[],
            next_steps=[]
        )

        return MeetingMinutesResponse(
            job_id=job.id,
            meeting_minutes=temp_minutes,
            cached=False
        )

    except Exception as e:
        logger.error(f"Erro ao enfileirar task de ata: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar ata de reunião"
        )


@router.delete("/{job_id}")
async def delete_meeting_minutes(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deleta a ata de reunião de um job (para forçar regeneração).

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

    # Deletar ata
    job.meeting_minutes = None
    db.commit()

    logger.info(f"Ata de reunião deletada para job {job_id}")

    return {"message": "Ata de reunião deletada com sucesso"}


@router.get("/{job_id}/download")
async def download_meeting_minutes_docx(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Faz download da ata de reunião em formato .docx formatado.

    Args:
        job_id: ID do job
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Arquivo .docx com a ata formatada

    Raises:
        HTTPException 404: Se job não existir ou ata não foi gerada
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

    # Verificar se ata existe
    if not job.meeting_minutes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ata ainda não foi gerada. Use POST /v1/meeting-minutes/{job_id} para gerar."
        )

    try:
        # Parse JSON da ata
        minutes_data = json.loads(job.meeting_minutes)

        # Gerar documento .docx
        docx_buffer = azure_openai_service.generate_meeting_minutes_docx(
            minutes_data=minutes_data,
            filename=job.filename
        )

        # Nome do arquivo de saída
        safe_filename = job.filename.rsplit('.', 1)[0] if '.' in job.filename else job.filename
        output_filename = f"ata_{safe_filename}.docx"

        logger.info(f"Enviando ata .docx para job {job_id}")

        # Retornar como download
        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=\"{output_filename}\""
            }
        )

    except Exception as e:
        logger.error(f"Erro ao gerar .docx da ata para download: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar documento .docx da ata"
        )
