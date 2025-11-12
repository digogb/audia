"""
Rota de chat/RAG sobre transcrições.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger
import json

from app.core.database import get_db, User, Job
from app.core.auth import get_current_user
from app.services.embeddings import embeddings_service
from app.services.azure_openai import azure_openai_service
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter()


def get_transcription_text_with_custom_names(job: Job) -> str:
    """
    Retorna o texto da transcrição com nomes customizados aplicados.

    Usa edited_transcription se existir, senão usa transcription_text.
    Se houver speaker_names customizados, aplica as substituições.
    """
    # Usar texto editado se existir, caso contrário usar o original
    text = job.edited_transcription if job.edited_transcription else job.transcription_text

    # Aplicar nomes customizados de speakers se existirem
    if job.speaker_names:
        try:
            custom_names = json.loads(job.speaker_names)
            logger.info(f"Aplicando nomes customizados ao contexto do chat: {custom_names}")

            # Substituir "Speaker X" pelos nomes customizados
            for speaker_id_str, custom_name in custom_names.items():
                old_name = f"Speaker {speaker_id_str}"
                text = text.replace(old_name, custom_name)
                logger.debug(f"Substituído '{old_name}' por '{custom_name}' no contexto")
        except json.JSONDecodeError:
            logger.warning(f"Erro ao parsear speaker_names para job {job.id}")

    return text


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

    # 2. Obter texto da transcrição com nomes customizados aplicados
    transcription_text = get_transcription_text_with_custom_names(job)

    # 3. Verificar se índice FAISS existe
    if not embeddings_service.index_exists(job_id):
        logger.warning(f"Índice FAISS não existe para job {job_id}, criando...")

        # Criar índice se não existir (fallback)
        try:
            embeddings_service.create_index_for_job(
                job_id=job_id,
                text=transcription_text,
                metadata={"filename": job.filename}
            )
        except Exception as e:
            logger.error(f"Erro ao criar índice: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao preparar busca semântica"
            )

    # 4. Buscar chunks relevantes
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

    # 5. Preparar histórico de chat (se houver)
    chat_history = None
    if chat_request.chat_history:
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in chat_request.chat_history
        ]

    # 6. Gerar resposta com Azure OpenAI
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

    # 7. Preparar fontes (chunks usados)
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
