"""
Rotas para acessar transcrições completas.
"""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db, User, Job
from app.core.auth import get_current_user
from app.services.storage_oci import oci_storage_service
from app.services.embeddings import embeddings_service
from app.models.schemas import (
    TranscriptionResponse,
    TranscriptionPhrase,
    TranscriptionSpeaker,
    TranscriptionListItem,
    TranscriptionListResponse,
    UpdateSpeakerNamesRequest,
    UpdateTranscriptionRequest,
    UpdateTranscriptionResponse
)

router = APIRouter()


@router.get("/{job_id}", response_model=TranscriptionResponse)
async def get_transcription(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtém a transcrição completa de um job.

    Args:
        job_id: ID do job
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Transcrição completa com diarização e timestamps

    Raises:
        HTTPException 404: Se job não existir
        HTTPException 403: Se job não pertencer ao usuário
        HTTPException 400: Se transcrição não estiver completa
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
            detail="Acesso negado a este job"
        )

    # Verificar se está completo
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transcrição não disponível. Status: {job.status}"
        )

    # Baixar JSON do OCI
    try:
        result_path = oci_storage_service.generate_result_path(
            job_id,
            "transcription.json"
        )

        content = oci_storage_service.download_file(result_path)
        transcription_data = json.loads(content.decode("utf-8"))

    except Exception as e:
        logger.error(f"Erro ao baixar transcrição: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao carregar transcrição"
        )

    # Parsear para schema
    phrases = [
        TranscriptionPhrase(**phrase)
        for phrase in transcription_data.get("phrases", [])
    ]

    speakers = [
        TranscriptionSpeaker(**speaker)
        for speaker in transcription_data.get("speakers", [])
    ]

    # Usar texto editado se existir, caso contrário usar o original
    full_text = job.edited_transcription if job.edited_transcription else transcription_data.get("full_text", "")

    # Aplicar nomes customizados de speakers se existirem
    if job.speaker_names:
        try:
            custom_names = json.loads(job.speaker_names)
            logger.info(f"Aplicando nomes customizados: {custom_names}")
            logger.info(f"Speakers antes da modificação: {[{'id': s.speaker_id, 'texts': s.texts} for s in speakers]}")

            # Atualizar textos dos speakers com nomes customizados
            for speaker in speakers:
                speaker_id_str = str(speaker.speaker_id)
                if speaker_id_str in custom_names:
                    # Atualizar os textos para usar o nome customizado
                    custom_name = custom_names[speaker_id_str]
                    logger.info(f"Substituindo 'Speaker {speaker.speaker_id}' por '{custom_name}' nos textos do speaker {speaker.speaker_id}")
                    speaker.texts = [
                        text.replace(f"Speaker {speaker.speaker_id}", custom_name)
                        for text in speaker.texts
                    ]
                    logger.info(f"Textos após substituição: {speaker.texts}")

            # Atualizar também o full_text com os nomes customizados
            for speaker_id_str, custom_name in custom_names.items():
                speaker_id = speaker_id_str
                old_name = f"Speaker {speaker_id}"
                logger.info(f"Substituindo '{old_name}' por '{custom_name}' no full_text")
                full_text = full_text.replace(old_name, custom_name)

            logger.info(f"Speakers após modificação: {[{'id': s.speaker_id, 'texts': s.texts} for s in speakers]}")
        except json.JSONDecodeError:
            logger.warning(f"Erro ao parsear speaker_names para job {job_id}")

    return TranscriptionResponse(
        job_id=job.id,
        filename=job.filename,
        status=job.status,
        full_text=full_text,
        duration_seconds=transcription_data.get("duration_seconds", 0.0),
        phrases=phrases,
        speakers=speakers,
        created_at=job.created_at,
        completed_at=job.completed_at
    )


@router.get("/{job_id}/download")
async def download_transcription(
    job_id: str,
    format: str = Query(default="txt", regex="^(txt|json)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download da transcrição em formato TXT ou JSON.

    Args:
        job_id: ID do job
        format: Formato do arquivo (txt ou json)
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Arquivo para download

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

    # Verificar permissão
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )

    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcrição não disponível"
        )

    # Baixar arquivo do OCI
    try:
        filename = f"transcription.{format}"
        result_path = oci_storage_service.generate_result_path(job_id, filename)

        content = oci_storage_service.download_file(result_path)

        # Se houver texto editado e formato for TXT, usar o editado
        if format == "txt" and job.edited_transcription:
            content = job.edited_transcription.encode("utf-8")

        # Se houver nomes customizados de speakers e formato for JSON, aplicar as alterações
        if format == "json" and (job.speaker_names or job.edited_transcription):
            transcription_data = json.loads(content.decode("utf-8"))

            # Aplicar texto editado
            if job.edited_transcription:
                transcription_data["full_text"] = job.edited_transcription

            # Aplicar nomes customizados
            if job.speaker_names:
                try:
                    custom_names = json.loads(job.speaker_names)
                    # Atualizar speakers
                    for speaker in transcription_data.get("speakers", []):
                        speaker_id_str = str(speaker["speaker_id"])
                        if speaker_id_str in custom_names:
                            custom_name = custom_names[speaker_id_str]
                            speaker["texts"] = [
                                text.replace(f"Speaker {speaker['speaker_id']}", custom_name)
                                for text in speaker["texts"]
                            ]
                except json.JSONDecodeError:
                    pass

            content = json.dumps(transcription_data, ensure_ascii=False, indent=2).encode("utf-8")

        # Determinar content type
        content_type = "application/json" if format == "json" else "text/plain"

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={job.filename}.{format}"
            }
        )

    except Exception as e:
        logger.error(f"Erro ao baixar arquivo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao baixar arquivo"
        )


@router.get("/", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todas as transcrições do usuário com paginação.

    Args:
        page: Página atual (1-indexed)
        page_size: Itens por página
        status_filter: Filtrar por status (opcional)
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Lista paginada de transcrições
    """
    # Query base
    query = db.query(Job).filter(Job.user_id == current_user.id)

    # Filtrar por status se especificado
    if status_filter:
        query = query.filter(Job.status == status_filter.upper())

    # Contar total
    total = query.count()

    # Paginação
    offset = (page - 1) * page_size
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size).all()

    # Converter para schema
    items = [
        TranscriptionListItem(
            job_id=job.id,
            filename=job.filename,
            status=job.status,
            progress=job.progress,
            duration_seconds=job.duration_seconds,
            created_at=job.created_at,
            completed_at=job.completed_at
        )
        for job in jobs
    ]

    total_pages = (total + page_size - 1) // page_size

    return TranscriptionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.put("/{job_id}/speakers", response_model=UpdateTranscriptionResponse)
async def update_speaker_names(
    job_id: str,
    request: UpdateSpeakerNamesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza os nomes customizados dos speakers de uma transcrição.

    Args:
        job_id: ID do job
        request: Mapeamento de speaker_id para nome customizado
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Confirmação da atualização

    Raises:
        HTTPException 404: Se job não existir
        HTTPException 403: Se job não pertencer ao usuário
    """
    logger.info(f"=== Requisição de atualização de speakers recebida para job {job_id} ===")
    logger.info(f"Usuário: {current_user.id} ({current_user.email})")
    logger.info(f"Nomes de speakers: {request.speaker_names}")

    # Buscar job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        logger.warning(f"Job {job_id} não encontrado")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )

    # Verificar permissão
    if job.user_id != current_user.id:
        logger.warning(f"Usuário {current_user.id} tentou acessar job {job_id} do usuário {job.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )

    # Log valor anterior
    logger.info(f"Valor anterior de speaker_names: {job.speaker_names}")

    # Salvar mapeamento de nomes como JSON
    job.speaker_names = json.dumps(request.speaker_names, ensure_ascii=False)
    db.commit()

    # Verificar se foi salvo
    db.refresh(job)
    logger.info(f"Valor após commit: {job.speaker_names}")
    logger.info(f"✅ Nomes de speakers salvos com sucesso para job {job_id}")

    # Recriar índice FAISS com os nomes atualizados
    try:
        logger.info(f"Recriando índice FAISS para job {job_id} com nomes atualizados...")

        # Obter texto com nomes customizados aplicados
        transcription_text = job.edited_transcription if job.edited_transcription else job.transcription_text
        if transcription_text and job.speaker_names:
            custom_names = json.loads(job.speaker_names)
            for speaker_id_str, custom_name in custom_names.items():
                old_name = f"Speaker {speaker_id_str}"
                transcription_text = transcription_text.replace(old_name, custom_name)

        # Recriar índice
        if transcription_text:
            embeddings_service.create_index_for_job(
                job_id=job_id,
                text=transcription_text,
                metadata={"filename": job.filename}
            )
            logger.info(f"✅ Índice FAISS recriado com sucesso para job {job_id}")
    except Exception as e:
        logger.error(f"Erro ao recriar índice FAISS: {str(e)}")
        # Não falhar a requisição se o índice falhar, apenas logar o erro

    return UpdateTranscriptionResponse(
        job_id=job_id,
        message="Nomes de speakers atualizados com sucesso"
    )


@router.put("/{job_id}/edit", response_model=UpdateTranscriptionResponse)
async def update_transcription(
    job_id: str,
    request: UpdateTranscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza o texto editado de uma transcrição.

    Args:
        job_id: ID do job
        request: Texto editado da transcrição
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Confirmação da atualização

    Raises:
        HTTPException 404: Se job não existir
        HTTPException 403: Se job não pertencer ao usuário
    """
    logger.info(f"=== Requisição de edição recebida para job {job_id} ===")
    logger.info(f"Usuário: {current_user.id} ({current_user.email})")
    logger.info(f"Tamanho do texto editado: {len(request.edited_text)} chars")

    # Buscar job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        logger.warning(f"Job {job_id} não encontrado")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )

    # Verificar permissão
    if job.user_id != current_user.id:
        logger.warning(f"Usuário {current_user.id} tentou acessar job {job_id} do usuário {job.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )

    # Log valor anterior
    logger.info(f"Valor anterior de edited_transcription: {job.edited_transcription[:100] if job.edited_transcription else 'None'}...")

    # Salvar transcrição editada
    job.edited_transcription = request.edited_text
    db.commit()

    # Verificar se foi salvo
    db.refresh(job)
    logger.info(f"Valor após commit: {job.edited_transcription[:100] if job.edited_transcription else 'None'}...")
    logger.info(f"✅ Transcrição editada salva com sucesso para job {job_id}")

    return UpdateTranscriptionResponse(
        job_id=job_id,
        message="Transcrição atualizada com sucesso"
    )
