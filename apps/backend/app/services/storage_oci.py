"""
Serviço de integração com Oracle Cloud Infrastructure (OCI) Object Storage.
Gerencia upload, download e geração de URLs pré-assinadas para arquivos de mídia.
"""

import os
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
from loguru import logger
import oci
from oci.object_storage import ObjectStorageClient
from oci.object_storage.models import CreatePreauthenticatedRequestDetails

from app.core.config import settings


class OCIStorageService:
    """Cliente para OCI Object Storage"""

    def __init__(self):
        """
        Inicializa o cliente OCI usando o config file.
        Espera arquivo de configuração em ~/.oci/config por padrão.
        """
        self.client = None
        self.namespace = None
        self.bucket_name = None
        self.compartment_id = None
        self._initialized = False

        try:
            # Carregar configuração do arquivo
            config = oci.config.from_file(
                file_location=os.path.expanduser(settings.OCI_CONFIG_PATH),
                profile_name=settings.OCI_PROFILE
            )

            # Inicializar cliente Object Storage
            self.client = ObjectStorageClient(config)
            self.namespace = settings.OCI_NAMESPACE
            self.bucket_name = settings.OCI_BUCKET
            self.compartment_id = settings.OCI_COMPARTMENT_OCID
            self._initialized = True

            logger.info(
                f"OCI Storage Service inicializado - "
                f"Namespace: {self.namespace}, Bucket: {self.bucket_name}"
            )

        except Exception as e:
            logger.warning(
                f"OCI Storage Service não inicializado: {str(e)}. "
                f"Funcionalidades de storage não estarão disponíveis."
            )

    def _check_initialized(self):
        """Verifica se o serviço está inicializado. Lança exceção se não estiver."""
        if not self._initialized:
            raise RuntimeError(
                "OCI Storage Service não está inicializado. "
                "Verifique suas credenciais OCI e configurações."
            )

    def upload_file(
        self,
        file_content: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Faz upload de um arquivo para o OCI Object Storage.

        Args:
            file_content: Conteúdo do arquivo (file-like object)
            object_name: Nome do objeto no bucket (ex: "uploads/audio_123.mp3")
            content_type: MIME type do arquivo (ex: "audio/mpeg")

        Returns:
            Nome completo do objeto no bucket

        Raises:
            Exception: Se o upload falhar
        """
        self._check_initialized()
        try:
            logger.info(f"Iniciando upload para OCI: {object_name}")

            # Preparar metadata
            kwargs = {}
            if content_type:
                kwargs["content_type"] = content_type

            # Upload
            self.client.put_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=object_name,
                put_object_body=file_content,
                **kwargs
            )

            logger.info(f"Upload concluído: {object_name}")

            return object_name

        except Exception as e:
            logger.error(f"Erro ao fazer upload para OCI: {str(e)}")
            raise

    def download_file(self, object_name: str) -> bytes:
        """
        Baixa um arquivo do OCI Object Storage.

        Args:
            object_name: Nome do objeto no bucket

        Returns:
            Conteúdo do arquivo em bytes

        Raises:
            Exception: Se o download falhar
        """
        self._check_initialized()
        try:
            logger.info(f"Baixando arquivo do OCI: {object_name}")

            response = self.client.get_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            content = response.data.content

            logger.info(f"Download concluído: {object_name} ({len(content)} bytes)")

            return content

        except Exception as e:
            logger.error(f"Erro ao baixar arquivo do OCI: {str(e)}")
            raise

    def get_object_url(self, object_name: str) -> str:
        """
        Retorna a URL pública de um objeto (se o bucket for público).

        Args:
            object_name: Nome do objeto no bucket

        Returns:
            URL completa do objeto
        """
        region = settings.OCI_REGION
        url = (
            f"https://objectstorage.{region}.oraclecloud.com"
            f"/n/{self.namespace}/b/{self.bucket_name}/o/{object_name}"
        )

        return url

    def create_presigned_url(
        self,
        object_name: str,
        access_type: str = "ObjectRead",
        expiration_hours: int = 24
    ) -> str:
        """
        Cria uma URL pré-assinada (PAR - Pre-Authenticated Request) para acesso temporário.

        Args:
            object_name: Nome do objeto no bucket
            access_type: Tipo de acesso ("ObjectRead", "ObjectWrite", "ObjectReadWrite")
            expiration_hours: Horas até a URL expirar (default: 24h)

        Returns:
            URL pré-assinada completa

        Raises:
            Exception: Se a criação falhar
        """
        self._check_initialized()
        try:
            logger.info(
                f"Criando PAR para {object_name} "
                f"({access_type}, {expiration_hours}h)"
            )

            # Calcular data de expiração
            expiration = datetime.utcnow() + timedelta(hours=expiration_hours)

            # Criar PAR
            par_details = CreatePreauthenticatedRequestDetails(
                name=f"audia-par-{datetime.utcnow().timestamp()}",
                object_name=object_name,
                access_type=access_type,
                time_expires=expiration
            )

            response = self.client.create_preauthenticated_request(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                create_preauthenticated_request_details=par_details
            )

            # Construir URL completa
            par_path = response.data.access_uri
            region = settings.OCI_REGION
            full_url = (
                f"https://objectstorage.{region}.oraclecloud.com"
                f"{par_path}"
            )

            logger.info(f"PAR criada com sucesso, expira em {expiration_hours}h")
            logger.info(f"URL gerada: {full_url}")

            return full_url

        except Exception as e:
            logger.error(f"Erro ao criar PAR: {str(e)}")
            raise

    def delete_file(self, object_name: str) -> bool:
        """
        Deleta um arquivo do OCI Object Storage.

        Args:
            object_name: Nome do objeto no bucket

        Returns:
            True se deletado com sucesso

        Raises:
            Exception: Se a deleção falhar
        """
        self._check_initialized()
        try:
            logger.info(f"Deletando arquivo do OCI: {object_name}")

            self.client.delete_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            logger.info(f"Arquivo deletado: {object_name}")

            return True

        except Exception as e:
            logger.error(f"Erro ao deletar arquivo: {str(e)}")
            raise

    def list_objects(self, prefix: Optional[str] = None, limit: int = 100) -> list:
        """
        Lista objetos no bucket.

        Args:
            prefix: Filtrar por prefixo (ex: "uploads/")
            limit: Número máximo de objetos a retornar

        Returns:
            Lista de objetos
        """
        try:
            logger.info(f"Listando objetos (prefix: {prefix}, limit: {limit})")

            response = self.client.list_objects(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                prefix=prefix,
                limit=limit
            )

            objects = [obj.name for obj in response.data.objects]

            logger.info(f"Encontrados {len(objects)} objetos")

            return objects

        except Exception as e:
            logger.error(f"Erro ao listar objetos: {str(e)}")
            raise

    def get_object_metadata(self, object_name: str) -> dict:
        """
        Obtém metadados de um objeto.

        Args:
            object_name: Nome do objeto

        Returns:
            Dict com metadados (size, content_type, last_modified, etc.)
        """
        try:
            response = self.client.head_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            metadata = {
                "name": object_name,
                "size": response.headers.get("content-length"),
                "content_type": response.headers.get("content-type"),
                "last_modified": response.headers.get("last-modified"),
                "etag": response.headers.get("etag")
            }

            return metadata

        except Exception as e:
            logger.error(f"Erro ao obter metadados: {str(e)}")
            raise

    def generate_upload_path(self, user_id: int, filename: str) -> str:
        """
        Gera um caminho único para upload baseado no user_id e timestamp.

        Args:
            user_id: ID do usuário
            filename: Nome original do arquivo

        Returns:
            Caminho no formato: "uploads/{user_id}/{timestamp}_{filename}"
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        # Sanitizar filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        path = f"uploads/{user_id}/{timestamp}_{safe_filename}"

        return path

    def generate_result_path(self, job_id: str, filename: str) -> str:
        """
        Gera caminho para armazenar resultados de transcrição.

        Args:
            job_id: ID do job
            filename: Nome do arquivo de resultado

        Returns:
            Caminho no formato: "results/{job_id}/{filename}"
        """
        path = f"results/{job_id}/{filename}"
        return path


# Instância global do serviço
oci_storage_service = OCIStorageService()
