"""
Serviço de integração com Azure OpenAI.
Fornece funcionalidades de:
- Geração de embeddings para busca semântica
- Resumo de transcrições
- Chat/RAG sobre conteúdo transcrito
"""

from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class AzureOpenAIService:
    """Cliente para Azure OpenAI Service"""

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.chat_deployment = settings.AZURE_OPENAI_DEPLOYMENT
        self.embedding_deployment = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_embeddings(self, text: str) -> List[float]:
        """
        Gera embeddings para um texto usando text-embedding-ada-002.

        Args:
            text: Texto para gerar embeddings (max ~8000 tokens)

        Returns:
            Lista de floats representando o vetor de embedding (1536 dimensões)

        Raises:
            Exception: Se a chamada à API falhar
        """
        try:
            logger.debug(f"Gerando embeddings para texto de {len(text)} caracteres")

            response = self.client.embeddings.create(
                input=text,
                model=self.embedding_deployment
            )

            embedding = response.data[0].embedding

            logger.debug(f"Embedding gerado com {len(embedding)} dimensões")

            return embedding

        except Exception as e:
            logger.error(f"Erro ao gerar embeddings: {str(e)}")
            raise

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 16
    ) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos em batch.

        Args:
            texts: Lista de textos
            batch_size: Tamanho do batch (default: 16)

        Returns:
            Lista de embeddings na mesma ordem dos textos
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.embedding_deployment
                )

                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

                logger.debug(
                    f"Batch {i // batch_size + 1}: "
                    f"{len(batch_embeddings)} embeddings gerados"
                )

            except Exception as e:
                logger.error(f"Erro no batch {i // batch_size + 1}: {str(e)}")
                raise

        return embeddings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def summarize(
        self,
        transcript: str,
        max_tokens: int = 500,
        temperature: float = 0.3
    ) -> str:
        """
        Gera um resumo conciso de uma transcrição.

        Args:
            transcript: Texto completo da transcrição
            max_tokens: Número máximo de tokens no resumo
            temperature: Criatividade (0.0 = determinístico, 1.0 = criativo)

        Returns:
            Resumo em linguagem natural
        """
        system_prompt = """Você é um assistente especializado em resumir transcrições de áudio.
Crie resumos concisos, informativos e bem estruturados.

Diretrizes:
- Use linguagem clara e objetiva
- Destaque os pontos principais
- Mantenha a ordem cronológica quando relevante
- Use bullet points se apropriado
- Seja neutro e factual"""

        user_prompt = f"""Por favor, resuma a seguinte transcrição:

{transcript}

Resumo:"""

        try:
            logger.info("Gerando resumo da transcrição")

            response = self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            summary = response.choices[0].message.content.strip()

            logger.info(f"Resumo gerado com {len(summary)} caracteres")

            return summary

        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def answer_question(
        self,
        question: str,
        context_chunks: List[str],
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 300,
        temperature: float = 0.7
    ) -> str:
        """
        Responde a uma pergunta baseada em chunks de contexto (RAG).

        Args:
            question: Pergunta do usuário
            context_chunks: Lista de chunks relevantes recuperados do FAISS
            chat_history: Histórico de mensagens anteriores (opcional)
            max_tokens: Número máximo de tokens na resposta
            temperature: Criatividade da resposta

        Returns:
            Resposta à pergunta baseada no contexto
        """
        # Concatenar contexto
        context = "\n\n".join([
            f"[Trecho {i+1}]\n{chunk}"
            for i, chunk in enumerate(context_chunks)
        ])

        system_prompt = """Você é um assistente que responde perguntas sobre transcrições de áudio.

Regras importantes:
- Responda APENAS com base no contexto fornecido
- Se a informação não estiver no contexto, diga "Não encontrei essa informação na transcrição"
- Seja conciso e direto
- Cite trechos relevantes quando apropriado
- Mantenha um tom profissional e amigável
- Se houver múltiplos speakers mencionados, identifique-os na resposta"""

        # Construir mensagens
        messages = [{"role": "system", "content": system_prompt}]

        # Adicionar histórico se existir
        if chat_history:
            messages.extend(chat_history)

        # Adicionar contexto e pergunta
        user_message = f"""Contexto da transcrição:
{context}

Pergunta: {question}

Resposta:"""

        messages.append({"role": "user", "content": user_message})

        try:
            logger.info(f"Respondendo pergunta: {question[:100]}...")

            response = self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            answer = response.choices[0].message.content.strip()

            logger.info(f"Resposta gerada com {len(answer)} caracteres")

            return answer

        except Exception as e:
            logger.error(f"Erro ao responder pergunta: {str(e)}")
            raise

    def generate_title(self, transcript_preview: str, max_tokens: int = 20) -> str:
        """
        Gera um título descritivo para a transcrição.

        Args:
            transcript_preview: Primeiras linhas da transcrição
            max_tokens: Máximo de tokens no título

        Returns:
            Título sugerido
        """
        system_prompt = "Você é um assistente que cria títulos descritivos e concisos."

        user_prompt = f"""Com base no início desta transcrição, sugira um título curto e descritivo:

{transcript_preview[:500]}

Título:"""

        try:
            response = self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.5
            )

            title = response.choices[0].message.content.strip()
            # Remover aspas se existirem
            title = title.strip('"\'')

            return title

        except Exception as e:
            logger.error(f"Erro ao gerar título: {str(e)}")
            return "Transcrição sem título"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_meeting_minutes(
        self,
        transcript: str,
        max_tokens: int = 1500,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Gera uma ata de reunião estruturada a partir de uma transcrição.

        Args:
            transcript: Texto completo da transcrição
            max_tokens: Número máximo de tokens na ata
            temperature: Criatividade (0.0 = determinístico, 1.0 = criativo)

        Returns:
            Dict com a estrutura da ata:
            {
                "title": str,
                "summary": str,
                "topics": [{"topic": str, "discussion": str}],
                "action_items": [{"item": str, "responsible": str, "deadline": str}],
                "decisions": [str],
                "next_steps": [str]
            }
        """
        system_prompt = """Você é um assistente especializado em criar atas de reunião profissionais.
Analise transcrições e gere atas estruturadas e organizadas.

IMPORTANTE: Sua resposta deve ser um JSON válido com a seguinte estrutura:
{
    "title": "Título descritivo da reunião",
    "summary": "Resumo executivo em 2-3 sentenças",
    "topics": [
        {"topic": "Nome do tópico", "discussion": "Resumo da discussão"}
    ],
    "action_items": [
        {"item": "Descrição da ação", "responsible": "Nome ou 'A definir'", "deadline": "Data ou 'A definir'"}
    ],
    "decisions": ["Decisão tomada 1", "Decisão tomada 2"],
    "next_steps": ["Próximo passo 1", "Próximo passo 2"]
}

Diretrizes:
- Identifique todos os itens de ação mencionados
- Extraia decisões importantes
- Liste próximos passos discutidos
- Use linguagem clara e profissional
- Se não houver informação para uma seção, use array vazio []
- Se responsável ou prazo não foram mencionados, use "A definir"
- Retorne APENAS o JSON, sem texto adicional"""

        user_prompt = f"""Por favor, gere uma ata de reunião para a seguinte transcrição:

{transcript}

Ata (JSON):"""

        try:
            logger.info("Gerando ata de reunião")

            response = self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON
            import json
            minutes = json.loads(content)

            logger.info(f"Ata de reunião gerada com {len(minutes.get('action_items', []))} itens de ação")

            return minutes

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON da ata: {str(e)}")
            logger.error(f"Conteúdo recebido: {content}")
            raise ValueError("Formato inválido de ata gerada")
        except Exception as e:
            logger.error(f"Erro ao gerar ata de reunião: {str(e)}")
            raise

    def estimate_tokens(self, text: str) -> int:
        """
        Estima número de tokens em um texto.
        Aproximação: 1 token ≈ 4 caracteres em português.

        Args:
            text: Texto para estimar

        Returns:
            Número estimado de tokens
        """
        return len(text) // 4


# Instância global do serviço
azure_openai_service = AzureOpenAIService()
