"""
Configuração do Celery para processamento assíncrono de jobs.
"""

from celery import Celery
from app.core.config import settings

# Criar instância do Celery
celery_app = Celery(
    "audia",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)

# Configurações do Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    worker_prefetch_multiplier=1,  # Processar uma task por vez
    worker_max_tasks_per_child=10,  # Reiniciar worker após N tasks (evitar memory leaks)
)

if __name__ == "__main__":
    celery_app.start()
