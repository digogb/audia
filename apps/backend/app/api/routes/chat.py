"""
Rota de chat/RAG sobre transcrições.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db, User, Job
from app.core.auth import get_current_user
from app.services.embeddings import embeddings_service
from app.services.azure_openai import azure_openai_service
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/{job_id}", response_model=ChatResponse)
async def chat_with_transcription(
    job_id: str,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Faz uma pergunta sobre uma transcrição usando RAG (Retrieval Augmented Generation).

    Fluxo:
    1. Valida acesso ao job
    2. Busca chunks relevantes no FAISS
    3. Usa Azure OpenAI para gerar resposta baseada nos chunks

    Args:
        job_id: ID do job da transcrição
        chat_request: Pergunta e histórico de chat (opcional)
        current_user: Usuário autenticado
        db: Sessão do banco

    Returns:
        Resposta à pergunta com fontes (chunks usados)

    Raises:
        HTTPException 404: Se job não existir
        HTTPException 403: Se usuário não tiver acesso
        HTTPException 400: Se transcrição não estiver disponível
    """
    logger.info(f"Chat request para job {job_id}: {chat_request.question[:100]}...")

    # 1. Buscar e validar job
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

    # 2. Verificar se índice FAISS existe
    if not embeddings_service.index_exists(job_id):
        logger.warning(f"Índice FAISS não existe para job {job_id}, criando...")

        # Criar índice se não existir (fallback)
        try:
            embeddings_service.create_index_for_job(
                job_id=job_id,
                text=job.transcription_text,
                metadata={"filename": job.filename}
            )
        except Exception as e:
            logger.error(f"Erro ao criar índice: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao preparar busca semântica"
            )

    # 3. Buscar chunks relevantes
    try:
        search_results = embeddings_service.search(
            job_id=job_id,
            query=chat_request.question,
            top_k=5  # Top 5 chunks mais relevantes
        )

        if not search_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhum contexto relevante encontrado"
            )

        # Extrair textos dos chunks
        context_chunks = [result["chunk"] for result in search_results]

        logger.info(f"Encontrados {len(context_chunks)} chunks relevantes")

    except Exception as e:
        logger.error(f"Erro na busca semântica: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar contexto relevante"
        )

    # 4. Preparar histórico de chat (se houver)
    chat_history = None
    if chat_request.chat_history:
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in chat_request.chat_history
        ]

    # 5. Gerar resposta com Azure OpenAI
    try:
        answer = azure_openai_service.answer_question(
            question=chat_request.question,
            context_chunks=context_chunks,
            chat_history=chat_history,
            max_tokens=300,
            temperature=0.7
        )

        logger.info(f"Resposta gerada: {answer[:100]}...")

    except Exception as e:
        logger.error(f"Erro ao gerar resposta: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar resposta"
        )

    # 6. Preparar fontes (chunks usados)
    sources = [
        {
            "rank": result["rank"],
            "text": result["chunk"][:200] + "..." if len(result["chunk"]) > 200 else result["chunk"],
            "score": result["score"]
        }
        for result in search_results
    ]

    return ChatResponse(
        answer=answer,
        sources=sources,
        job_id=job_id
    )
