"""
Aplicação FastAPI principal.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import auth, upload, jobs, transcriptions, chat, summary, meeting_minutes

# Configurar logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL
)

# Criar app FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para transcrição de áudio/vídeo com IA",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global de exceções"""
    logger.error(f"Erro não tratado: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Events
@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar a aplicação"""
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")

    # Inicializar banco de dados
    logger.info("Inicializando banco de dados...")
    init_db()

    logger.info("Aplicação iniciada com sucesso!")


@app.on_event("shutdown")
async def shutdown_event():
    """Executado ao desligar a aplicação"""
    logger.info("Desligando aplicação...")


# Health Check
@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME
    }


@app.get("/ready")
async def readiness_check():
    """Endpoint de readiness check"""
    # TODO: Verificar conexões (Redis, etc.)
    return {
        "ready": True,
        "services": {
            "database": True,
            "redis": True  # TODO: verificar de verdade
        }
    }


# Incluir routers
app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/v1", tags=["Upload"])
app.include_router(jobs.router, prefix="/v1/jobs", tags=["Jobs"])
app.include_router(
    transcriptions.router,
    prefix="/v1/transcriptions",
    tags=["Transcriptions"]
)
app.include_router(chat.router, prefix="/v1/chat", tags=["Chat"])
app.include_router(summary.router, prefix="/v1/summary", tags=["Summary"])
app.include_router(
    meeting_minutes.router,
    prefix="/v1/meeting-minutes",
    tags=["Meeting Minutes"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
