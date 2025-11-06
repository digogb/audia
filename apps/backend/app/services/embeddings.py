"""
Serviço de gerenciamento de embeddings e busca semântica com FAISS.
Indexa chunks de transcrições para permitir RAG (Retrieval Augmented Generation).
"""

import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss
from loguru import logger

from app.core.config import settings
from app.services.azure_openai import azure_openai_service


class EmbeddingsService:
    """Gerencia índices FAISS para busca semântica em transcrições"""

    def __init__(self, base_path: Optional[str] = None):
        """
        Inicializa o serviço de embeddings.

        Args:
            base_path: Caminho base para armazenar índices (default: settings.FAISS_PATH)
        """
        self.base_path = base_path or settings.FAISS_PATH
        self.dimension = 1536  # Dimensão dos embeddings ada-002

        # Garantir que o diretório existe
        os.makedirs(self.base_path, exist_ok=True)

        logger.info(f"Embeddings Service inicializado em: {self.base_path}")

    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ) -> List[str]:
        """
        Divide um texto em chunks com overlap para melhor contexto.

        Args:
            text: Texto completo a ser dividido
            chunk_size: Tamanho aproximado de cada chunk em tokens
            overlap: Número de tokens de overlap entre chunks

        Returns:
            Lista de chunks de texto
        """
        chunk_size = chunk_size or settings.CHUNK_SIZE_TOKENS
        overlap = overlap or settings.CHUNK_OVERLAP_TOKENS

        # Conversão aproximada: 1 token ≈ 4 caracteres em português
        chars_per_chunk = chunk_size * 4
        chars_overlap = overlap * 4

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chars_per_chunk

            # Pegar chunk
            chunk = text[start:end]

            # Tentar quebrar em fim de sentença se possível
            if end < text_len:
                # Procurar último ponto final no chunk
                last_period = chunk.rfind(". ")
                if last_period > chars_per_chunk * 0.7:  # Só se for > 70% do chunk
                    chunk = chunk[:last_period + 1]
                    end = start + last_period + 1

            chunks.append(chunk.strip())

            # Próximo chunk com overlap
            start = end - chars_overlap

            # Evitar loop infinito
            if start <= 0:
                start = end

        logger.info(f"Texto dividido em {len(chunks)} chunks")

        return chunks

    def create_index_for_job(
        self,
        job_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria um índice FAISS para uma transcrição específica.

        Args:
            job_id: ID do job de transcrição
            text: Texto completo da transcrição
            metadata: Metadados adicionais (opcional)

        Returns:
            Dict com estatísticas do índice criado
        """
        logger.info(f"Criando índice FAISS para job {job_id}")

        # Dividir texto em chunks
        chunks = self.chunk_text(text)

        if not chunks:
            raise ValueError("Nenhum chunk gerado do texto")

        # Gerar embeddings para cada chunk
        logger.info(f"Gerando embeddings para {len(chunks)} chunks")
        embeddings = azure_openai_service.generate_embeddings_batch(chunks)

        # Converter para numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # Criar índice FAISS
        # Usando IndexFlatIP (Inner Product) para busca de similaridade
        index = faiss.IndexFlatIP(self.dimension)

        # Normalizar vetores para usar produto interno como cosine similarity
        faiss.normalize_L2(embeddings_array)

        # Adicionar vetores ao índice
        index.add(embeddings_array)

        logger.info(f"Índice criado com {index.ntotal} vetores")

        # Preparar metadados
        index_metadata = {
            "job_id": job_id,
            "chunks": chunks,
            "num_chunks": len(chunks),
            "dimension": self.dimension,
            "metadata": metadata or {}
        }

        # Salvar índice e metadados
        self._save_index(job_id, index, index_metadata)

        return {
            "job_id": job_id,
            "num_chunks": len(chunks),
            "dimension": self.dimension,
            "index_size_mb": index.ntotal * self.dimension * 4 / (1024 * 1024)
        }

    def search(
        self,
        job_id: str,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca chunks mais relevantes para uma query.

        Args:
            job_id: ID do job
            query: Texto da query/pergunta
            top_k: Número de resultados a retornar

        Returns:
            Lista de chunks com scores de similaridade
        """
        top_k = top_k or settings.MAX_CONTEXT_CHUNKS

        logger.info(f"Buscando chunks para query: {query[:100]}...")

        # Carregar índice
        index, metadata = self._load_index(job_id)

        if index is None:
            raise ValueError(f"Índice não encontrado para job {job_id}")

        # Gerar embedding da query
        query_embedding = azure_openai_service.generate_embeddings(query)
        query_vector = np.array([query_embedding], dtype=np.float32)

        # Normalizar
        faiss.normalize_L2(query_vector)

        # Buscar
        scores, indices = index.search(query_vector, min(top_k, index.ntotal))

        # Preparar resultados
        results = []
        chunks = metadata.get("chunks", [])

        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(chunks):
                results.append({
                    "rank": i + 1,
                    "chunk": chunks[idx],
                    "score": float(score),
                    "index": int(idx)
                })

        logger.info(f"Encontrados {len(results)} chunks relevantes")

        return results

    def update_index(self, job_id: str, new_text: str) -> bool:
        """
        Atualiza um índice existente com novo texto.

        Args:
            job_id: ID do job
            new_text: Novo texto a ser adicionado

        Returns:
            True se atualizado com sucesso
        """
        logger.info(f"Atualizando índice para job {job_id}")

        # Carregar índice existente
        index, metadata = self._load_index(job_id)

        if index is None:
            logger.warning(f"Índice não existe, criando novo")
            self.create_index_for_job(job_id, new_text, metadata.get("metadata"))
            return True

        # Adicionar novos chunks
        new_chunks = self.chunk_text(new_text)
        new_embeddings = azure_openai_service.generate_embeddings_batch(new_chunks)

        embeddings_array = np.array(new_embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings_array)

        index.add(embeddings_array)

        # Atualizar metadados
        metadata["chunks"].extend(new_chunks)
        metadata["num_chunks"] = len(metadata["chunks"])

        # Salvar
        self._save_index(job_id, index, metadata)

        logger.info(f"Índice atualizado: {index.ntotal} vetores totais")

        return True

    def delete_index(self, job_id: str) -> bool:
        """
        Deleta um índice do disco.

        Args:
            job_id: ID do job

        Returns:
            True se deletado com sucesso
        """
        try:
            index_path = self._get_index_path(job_id)
            metadata_path = self._get_metadata_path(job_id)

            if os.path.exists(index_path):
                os.remove(index_path)

            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            logger.info(f"Índice deletado para job {job_id}")

            return True

        except Exception as e:
            logger.error(f"Erro ao deletar índice: {str(e)}")
            return False

    def index_exists(self, job_id: str) -> bool:
        """Verifica se um índice existe para um job"""
        index_path = self._get_index_path(job_id)
        return os.path.exists(index_path)

    def _get_index_path(self, job_id: str) -> str:
        """Retorna o caminho do arquivo de índice"""
        return os.path.join(self.base_path, f"{job_id}.index")

    def _get_metadata_path(self, job_id: str) -> str:
        """Retorna o caminho do arquivo de metadados"""
        return os.path.join(self.base_path, f"{job_id}.meta")

    def _save_index(
        self,
        job_id: str,
        index: faiss.Index,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Salva índice FAISS e metadados no disco.

        Args:
            job_id: ID do job
            index: Índice FAISS
            metadata: Metadados associados
        """
        try:
            index_path = self._get_index_path(job_id)
            metadata_path = self._get_metadata_path(job_id)

            # Salvar índice
            faiss.write_index(index, index_path)

            # Salvar metadados
            with open(metadata_path, "wb") as f:
                pickle.dump(metadata, f)

            logger.info(f"Índice salvo em: {index_path}")

        except Exception as e:
            logger.error(f"Erro ao salvar índice: {str(e)}")
            raise

    def _load_index(self, job_id: str) -> Tuple[Optional[faiss.Index], Dict[str, Any]]:
        """
        Carrega índice FAISS e metadados do disco.

        Args:
            job_id: ID do job

        Returns:
            Tupla (index, metadata) ou (None, {}) se não existir
        """
        try:
            index_path = self._get_index_path(job_id)
            metadata_path = self._get_metadata_path(job_id)

            if not os.path.exists(index_path):
                logger.warning(f"Índice não encontrado: {index_path}")
                return None, {}

            # Carregar índice
            index = faiss.read_index(index_path)

            # Carregar metadados
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, "rb") as f:
                    metadata = pickle.load(f)

            logger.info(f"Índice carregado: {index.ntotal} vetores")

            return index, metadata

        except Exception as e:
            logger.error(f"Erro ao carregar índice: {str(e)}")
            return None, {}

    def get_index_stats(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém estatísticas de um índice.

        Args:
            job_id: ID do job

        Returns:
            Dict com estatísticas ou None se não existir
        """
        index, metadata = self._load_index(job_id)

        if index is None:
            return None

        return {
            "job_id": job_id,
            "num_vectors": index.ntotal,
            "dimension": self.dimension,
            "num_chunks": metadata.get("num_chunks", 0),
            "size_mb": index.ntotal * self.dimension * 4 / (1024 * 1024)
        }


# Instância global do serviço
embeddings_service = EmbeddingsService()
