"""
Rota de upload de arquivos de áudio/vídeo.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from loguru import logger
from datetime import timedelta

from app.core.database import get_db, User, Job
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.utils import now
from app.services.storage_oci import oci_storage_service
from app.services.audio_converter import audio_converter_service
from app.workers.tasks import process_transcription_task
from app.models.schemas import UploadResponse

router = APIRouter()


def check_file_extension(filename: str) -> bool:
    """Verifica se a extensão do arquivo é permitida"""
    extension = filename.lower().split(".")[-1]
    return extension in settings.ALLOWED_EXTENSIONS


def check_upload_rate_limit(user_id: int, db: Session) -> bool:
    """
    Verifica se o usuário não excedeu o limite de uploads por hora.

    Args:
        user_id: ID do usuário
        db: Sessão do banco

    Returns:
        True se pode fazer upload, False caso contrário
    """
    # Contar uploads na última hora
    one_hour_ago = now() - timedelta(hours=1)

    uploads_count = db.query(Job).filter(
        Job.user_id == user_id,
        Job.created_at >= one_hour_ago
    ).count()

    return uploads_count < settings.MAX_UPLOADS_PER_HOUR


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Faz upload de um arquivo de áudio/vídeo para transcrição.

    Args:
        file: Arquivo enviado
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Informações do job criado (job_id, status)

    Raises:
        HTTPException 400: Se arquivo for inválido
        HTTPException 429: Se excedeu limite de uploads
        HTTPException 413: Se arquivo for muito grande
    """
    logger.info(f"Upload iniciado por usuário {current_user.id}: {file.filename}")

    # 1. Validar extensão do arquivo
    if not check_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensão não permitida. Permitidas: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 2. Verificar rate limit
    if not check_upload_rate_limit(current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite de {settings.MAX_UPLOADS_PER_HOUR} uploads por hora excedido"
        )

    # 3. Ler conteúdo do arquivo
    file_content = await file.read()
    file_size = len(file_content)

    # 4. Verificar tamanho do arquivo
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Máximo: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    logger.info(f"Arquivo validado: {file.filename} ({file_size / (1024*1024):.2f}MB)")

    # 5. Converter áudio para WAV se necessário
    final_filename = file.filename
    final_content = file_content

    if audio_converter_service.is_conversion_needed(file.filename):
        try:
            logger.info(f"Convertendo {file.filename} para WAV...")
            from io import BytesIO

            wav_content, wav_filename = audio_converter_service.convert_to_wav(
                input_file=BytesIO(file_content),
                input_filename=file.filename
            )

            final_content = wav_content
            final_filename = wav_filename
            file_size = len(final_content)

            logger.info(
                f"Conversão concluída: {file.filename} -> {wav_filename} "
                f"({len(file_content) / (1024*1024):.2f}MB -> {file_size / (1024*1024):.2f}MB)"
            )

        except Exception as e:
            logger.error(f"Erro na conversão de áudio: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao converter áudio: {str(e)}"
            )
    else:
        logger.info(f"Arquivo {file.filename} já é WAV, sem necessidade de conversão")

    # 6. Fazer upload para OCI Object Storage
    try:
        # Gerar caminho único (usar nome final após conversão)
        object_path = oci_storage_service.generate_upload_path(
            user_id=current_user.id,
            filename=final_filename
        )

        logger.info(f"Fazendo upload para OCI: {object_path}")

        # Upload (usar conteúdo final após conversão)
        from io import BytesIO
        file_obj = BytesIO(final_content)

        # Determinar content_type correto
        content_type = "audio/wav" if final_filename.endswith(".wav") else file.content_type

        oci_storage_service.upload_file(
            file_content=file_obj,
            object_name=object_path,
            content_type=content_type
        )

        file_url = oci_storage_service.get_object_url(object_path)

        logger.info(f"Upload para OCI concluído: {file_url}")

    except Exception as e:
        logger.error(f"Erro ao fazer upload para OCI: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer upload: {str(e)}"
        )

    # 7. Criar job no banco de dados
    job_id = str(uuid.uuid4())

    new_job = Job(
        id=job_id,
        user_id=current_user.id,
        filename=final_filename,  # Usar nome final após conversão
        file_size=file_size,
        file_url=object_path,  # Salvar object path, não URL completa
        status="QUEUED",
        progress=0.0
    )

    db.add(new_job)
    db.commit()

    logger.info(f"Job criado: {job_id}")

    # 7. Enfileirar task Celery
    try:
        process_transcription_task.delay(job_id, object_path)
        logger.info(f"Task enfileirada para job {job_id}")

    except Exception as e:
        logger.error(f"Erro ao enfileirar task: {str(e)}")
        # Atualizar status do job
        new_job.status = "FAILED"
        new_job.error_message = f"Erro ao enfileirar: {str(e)}"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar arquivo"
        )

    # 8. Retornar resposta
    return UploadResponse(
        job_id=job_id,
        filename=final_filename,  # Retornar nome final
        file_size=file_size,
        status="QUEUED",
        message="Arquivo recebido e enfileirado para processamento"
    )
