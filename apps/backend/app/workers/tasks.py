"""
Tasks Celery para processamento assíncrono de transcrições.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from celery import Task
from loguru import logger
from sqlalchemy.orm import Session

from celery_app import celery_app
from app.core.database import SessionLocal, Job
from app.core.utils import now
from app.services.azure_speech import azure_speech_service
from app.services.azure_openai import azure_openai_service
from app.services.storage_oci import oci_storage_service
from app.services.embeddings import embeddings_service


class DatabaseTask(Task):
    """Task base com suporte a sessão de banco de dados"""
    _db: Session = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="process_transcription",
    max_retries=3,
    default_retry_delay=60
)
def process_transcription_task(self, job_id: str, file_url: str) -> Dict[str, Any]:
    """
    Task principal de processamento de transcrição.

    Fluxo:
    1. Atualizar status do job para PROCESSING
    2. Criar URL pré-assinada do arquivo no OCI
    3. Criar job no Azure Speech Batch API
    4. Aguardar conclusão (polling)
    5. Baixar resultado JSON
    6. Parsear transcrição com diarização
    7. Salvar resultado no OCI
    8. Gerar embeddings e indexar no FAISS
    9. Atualizar job com status COMPLETED

    Args:
        job_id: ID do job
        file_url: URL do arquivo no OCI Object Storage

    Returns:
        Dict com resultado do processamento
    """
    try:
        logger.info(f"[Job {job_id}] Iniciando processamento")

        # 1. Buscar job no banco
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} não encontrado")

        # Atualizar status
        job.status = "PROCESSING"
        job.started_at = now()
        job.progress = 0.1
        self.db.commit()

        logger.info(f"[Job {job_id}] Status atualizado para PROCESSING")

        # 2. Criar URL pré-assinada para o Azure acessar
        logger.info(f"[Job {job_id}] Criando PAR para Azure Speech")

        # Extrair object_name da URL
        # URL format: uploads/{user_id}/{timestamp}_{filename}
        object_name = file_url.split("/o/")[-1] if "/o/" in file_url else file_url

        presigned_url = oci_storage_service.create_presigned_url(
            object_name,
            access_type="ObjectRead",
            expiration_hours=48
        )

        job.progress = 0.2
        self.db.commit()

        # 3. Criar job de transcrição no Azure Speech
        logger.info(f"[Job {job_id}] Criando job no Azure Speech Batch API")

        azure_job = asyncio.run(azure_speech_service.create_transcription_job(
            audio_url=presigned_url,
            locale="pt-BR",
            display_name=f"Audia - {job.filename}"
        ))

        azure_job_id = azure_job["job_id"]
        job.azure_job_id = azure_job_id
        job.progress = 0.3
        self.db.commit()

        logger.info(f"[Job {job_id}] Azure job criado: {azure_job_id}")

        # 4. Aguardar conclusão com polling
        logger.info(f"[Job {job_id}] Aguardando conclusão do Azure Speech")

        # Polling com atualização de progresso
        async def poll_with_progress():
            max_wait = 3600  # 1 hora
            poll_interval = 15  # 15 segundos
            elapsed = 0

            while elapsed < max_wait:
                status_data = await azure_speech_service.get_transcription_status(
                    azure_job_id
                )
                status = status_data["status"]

                # Atualizar progresso (0.3 a 0.8)
                progress = 0.3 + (elapsed / max_wait) * 0.5
                job.progress = min(progress, 0.8)
                self.db.commit()

                logger.info(
                    f"[Job {job_id}] Azure status: {status}, "
                    f"Progress: {job.progress:.2f}"
                )

                if status == "Succeeded":
                    return status_data
                elif status == "Failed":
                    error = status_data.get("error", "Erro desconhecido")
                    raise Exception(f"Azure Speech falhou: {error}")

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            raise TimeoutError(f"Job não completou em {max_wait} segundos")

        # Executar polling
        azure_result = asyncio.run(poll_with_progress())

        # 5. Baixar resultado JSON do Azure
        logger.info(f"[Job {job_id}] Baixando resultado da transcrição")

        transcription_json = asyncio.run(
            azure_speech_service.download_transcription_result(azure_job_id)
        )

        job.progress = 0.85
        self.db.commit()

        # 6. Parsear transcrição
        logger.info(f"[Job {job_id}] Parseando transcrição com diarização")

        parsed = azure_speech_service.parse_transcription_with_diarization(
            transcription_json
        )

        full_text = parsed["full_text"]
        duration_seconds = parsed["duration_seconds"]

        # 7. Salvar resultado no OCI
        logger.info(f"[Job {job_id}] Salvando resultado no OCI")

        # Salvar JSON completo
        result_json_path = oci_storage_service.generate_result_path(
            job_id,
            "transcription.json"
        )

        oci_storage_service.upload_file(
            file_content=json.dumps(parsed, ensure_ascii=False, indent=2).encode(),
            object_name=result_json_path,
            content_type="application/json"
        )

        transcription_url = oci_storage_service.get_object_url(result_json_path)

        # Salvar texto puro
        text_path = oci_storage_service.generate_result_path(
            job_id,
            "transcription.txt"
        )

        oci_storage_service.upload_file(
            file_content=full_text.encode("utf-8"),
            object_name=text_path,
            content_type="text/plain"
        )

        job.progress = 0.9
        self.db.commit()

        # 8. Gerar embeddings e indexar no FAISS
        logger.info(f"[Job {job_id}] Criando índice FAISS")

        embeddings_service.create_index_for_job(
            job_id=job_id,
            text=full_text,
            metadata={
                "filename": job.filename,
                "duration": duration_seconds,
                "speakers": len(parsed["speakers"])
            }
        )

        # 9. Atualizar job com sucesso
        job.status = "COMPLETED"
        job.progress = 1.0
        job.completed_at = now()
        job.transcription_url = transcription_url
        job.transcription_text = full_text
        job.duration_seconds = duration_seconds
        self.db.commit()

        logger.info(f"[Job {job_id}] Processamento concluído com sucesso!")

        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "duration_seconds": duration_seconds,
            "num_speakers": len(parsed["speakers"]),
            "text_length": len(full_text)
        }

    except Exception as e:
        logger.error(f"[Job {job_id}] Erro no processamento: {str(e)}")

        # Atualizar job com erro
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
            job.completed_at = now()
            self.db.commit()

        # Retry se não excedeu tentativas
        raise self.retry(exc=e, countdown=60)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="generate_summary",
    max_retries=2
)
def generate_summary_task(
    self,
    job_id: str,
    max_tokens: int = 500,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """
    Task para gerar resumo de uma transcrição.

    Args:
        job_id: ID do job
        max_tokens: Máximo de tokens no resumo
        temperature: Criatividade (0-1)

    Returns:
        Dict com resumo gerado
    """
    try:
        logger.info(f"[Job {job_id}] Gerando resumo")

        # Buscar job
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} não encontrado")

        if job.status != "COMPLETED":
            raise ValueError(f"Job {job_id} não está completo")

        # Verificar se já tem resumo
        if job.summary:
            logger.info(f"[Job {job_id}] Resumo já existe, retornando cached")
            return {
                "job_id": job_id,
                "summary": job.summary,
                "cached": True
            }

        # Gerar resumo
        transcript = job.transcription_text
        if not transcript:
            raise ValueError("Transcrição não disponível")

        summary = azure_openai_service.summarize(
            transcript=transcript,
            max_tokens=max_tokens,
            temperature=temperature
        )

        # Salvar no banco
        job.summary = summary
        self.db.commit()

        logger.info(f"[Job {job_id}] Resumo gerado e salvo")

        return {
            "job_id": job_id,
            "summary": summary,
            "cached": False
        }

    except Exception as e:
        logger.error(f"[Job {job_id}] Erro ao gerar resumo: {str(e)}")
        raise self.retry(exc=e, countdown=30)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="generate_meeting_minutes",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def generate_meeting_minutes_task(
    self,
    job_id: str,
    max_tokens: int = 1500,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """
    Task para gerar ata de reunião de uma transcrição.

    Args:
        job_id: ID do job
        max_tokens: Máximo de tokens na ata
        temperature: Criatividade (0-1)

    Returns:
        Dict com ata gerada
    """
    try:
        logger.info(f"[Job {job_id}] Gerando ata de reunião")

        # Buscar job
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} não encontrado")

        if job.status != "COMPLETED":
            raise ValueError(f"Job {job_id} não está completo")

        # Verificar se já tem ata
        if job.meeting_minutes:
            logger.info(f"[Job {job_id}] Ata já existe, retornando cached")
            import json
            return {
                "job_id": job_id,
                "meeting_minutes": json.loads(job.meeting_minutes),
                "cached": True
            }

        # Gerar ata
        transcript = job.transcription_text
        if not transcript:
            raise ValueError("Transcrição não disponível")

        minutes = azure_openai_service.generate_meeting_minutes(
            transcript=transcript,
            max_tokens=max_tokens,
            temperature=temperature
        )

        # Salvar no banco como JSON string
        import json
        job.meeting_minutes = json.dumps(minutes, ensure_ascii=False)
        self.db.commit()

        logger.info(f"[Job {job_id}] Ata de reunião gerada e salva")

        return {
            "job_id": job_id,
            "meeting_minutes": minutes,
            "cached": False
        }

    except Exception as e:
        logger.error(f"[Job {job_id}] Erro ao gerar ata de reunião: {str(e)}")
        raise self.retry(exc=e, countdown=30)


@celery_app.task(name="cleanup_old_jobs")
def cleanup_old_jobs_task(days: int = 90) -> Dict[str, int]:
    """
    Task de limpeza de jobs antigos (chamada periodicamente).

    Args:
        days: Deletar jobs com mais de N dias

    Returns:
        Dict com contadores de limpeza
    """
    from datetime import timedelta

    logger.info(f"Iniciando limpeza de jobs com mais de {days} dias")

    db = SessionLocal()
    try:
        cutoff_date = now() - timedelta(days=days)

        # Buscar jobs antigos
        old_jobs = db.query(Job).filter(
            Job.created_at < cutoff_date,
            Job.status.in_(["COMPLETED", "FAILED"])
        ).all()

        deleted_files = 0
        deleted_indices = 0

        for job in old_jobs:
            try:
                # Deletar arquivos do OCI
                if job.file_url:
                    object_name = job.file_url.split("/o/")[-1]
                    oci_storage_service.delete_file(object_name)
                    deleted_files += 1

                # Deletar índice FAISS
                if embeddings_service.index_exists(job.id):
                    embeddings_service.delete_index(job.id)
                    deleted_indices += 1

                # Deletar job do banco
                db.delete(job)

            except Exception as e:
                logger.error(f"Erro ao deletar job {job.id}: {str(e)}")

        db.commit()

        result = {
            "jobs_deleted": len(old_jobs),
            "files_deleted": deleted_files,
            "indices_deleted": deleted_indices
        }

        logger.info(f"Limpeza concluída: {result}")

        return result

    except Exception as e:
        logger.error(f"Erro na limpeza: {str(e)}")
        db.rollback()
        raise

    finally:
        db.close()
