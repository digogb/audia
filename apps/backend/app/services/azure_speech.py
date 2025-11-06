"""
Serviço de integração com Azure Speech Service - Batch Transcription API.
Suporta transcrição com diarização (identificação de speakers) e timestamps.
"""

import time
import httpx
from typing import Dict, Any, Optional, List
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class AzureSpeechService:
    """Cliente para Azure Speech Service Batch API"""

    def __init__(self):
        self.region = settings.AZURE_SPEECH_REGION
        self.subscription_key = settings.AZURE_SPEECH_KEY
        self.base_url = f"https://{self.region}.api.cognitive.microsoft.com/speechtotext/v3.1"
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_transcription_job(
        self,
        audio_url: str,
        locale: str = "pt-BR",
        display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria um job de transcrição batch no Azure Speech.

        Args:
            audio_url: URL pública do arquivo de áudio (ex: SAS URL do OCI)
            locale: Idioma do áudio (default: pt-BR)
            display_name: Nome descritivo do job

        Returns:
            Dict com informações do job criado, incluindo job_id

        Raises:
            httpx.HTTPError: Se a requisição falhar
        """
        endpoint = f"{self.base_url}/transcriptions"

        payload = {
            "contentUrls": [audio_url],
            "locale": locale,
            "displayName": display_name or f"Audia Transcription {time.time()}",
            "properties": {
                "diarizationEnabled": True,  # Habilita identificação de speakers
                "wordLevelTimestampsEnabled": True,  # Timestamps por palavra
                "punctuationMode": "DictatedAndAutomatic",
                "profanityFilterMode": "Masked",
                "timeToLive": "P1D"  # Job expira em 1 dia (formato ISO 8601)
            }
        }

        logger.info(f"Criando job de transcrição no Azure Speech para: {audio_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()

        job_data = response.json()
        job_id = job_data.get("self", "").split("/")[-1]

        logger.info(f"Job de transcrição criado com sucesso. ID: {job_id}")

        return {
            "job_id": job_id,
            "status": job_data.get("status"),
            "created_at": job_data.get("createdDateTime"),
            "self_url": job_data.get("self")
        }

    async def get_transcription_status(self, job_id: str) -> Dict[str, Any]:
        """
        Obtém o status atual de um job de transcrição.

        Args:
            job_id: ID do job retornado ao criar a transcrição

        Returns:
            Dict com status e informações do job

        Status possíveis:
            - NotStarted: Job criado mas não iniciou
            - Running: Processando
            - Succeeded: Concluído com sucesso
            - Failed: Falhou
        """
        endpoint = f"{self.base_url}/transcriptions/{job_id}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(endpoint, headers=self.headers)
            response.raise_for_status()

        job_data = response.json()

        return {
            "job_id": job_id,
            "status": job_data.get("status"),
            "created_at": job_data.get("createdDateTime"),
            "last_action_at": job_data.get("lastActionDateTime"),
            "duration": job_data.get("properties", {}).get("duration"),
            "error": job_data.get("properties", {}).get("error")
        }

    async def wait_for_completion(
        self,
        job_id: str,
        max_wait_seconds: int = 3600,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Aguarda a conclusão de um job de transcrição com polling.

        Args:
            job_id: ID do job
            max_wait_seconds: Tempo máximo de espera (default: 1 hora)
            poll_interval: Intervalo entre checks em segundos (default: 10s)

        Returns:
            Status final do job

        Raises:
            TimeoutError: Se exceder o tempo máximo
            Exception: Se o job falhar
        """
        start_time = time.time()
        logger.info(f"Iniciando polling do job {job_id}")

        while True:
            elapsed = time.time() - start_time

            if elapsed > max_wait_seconds:
                raise TimeoutError(
                    f"Job {job_id} não completou em {max_wait_seconds} segundos"
                )

            status_data = await self.get_transcription_status(job_id)
            status = status_data["status"]

            logger.info(
                f"Job {job_id} - Status: {status} - "
                f"Elapsed: {int(elapsed)}s / {max_wait_seconds}s"
            )

            if status == "Succeeded":
                logger.info(f"Job {job_id} concluído com sucesso!")
                return status_data

            elif status == "Failed":
                error = status_data.get("error", "Erro desconhecido")
                logger.error(f"Job {job_id} falhou: {error}")
                raise Exception(f"Transcrição falhou: {error}")

            elif status in ["NotStarted", "Running"]:
                # Continua aguardando
                await asyncio.sleep(poll_interval)

            else:
                logger.warning(f"Status desconhecido: {status}")
                await asyncio.sleep(poll_interval)

    async def get_transcription_files(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Lista os arquivos de resultado de uma transcrição completada.

        Args:
            job_id: ID do job

        Returns:
            Lista de arquivos disponíveis (transcription, report, etc.)
        """
        endpoint = f"{self.base_url}/transcriptions/{job_id}/files"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(endpoint, headers=self.headers)
            response.raise_for_status()

        files_data = response.json()
        return files_data.get("values", [])

    async def download_transcription_result(self, job_id: str) -> Dict[str, Any]:
        """
        Baixa o resultado completo da transcrição em formato JSON.

        Args:
            job_id: ID do job

        Returns:
            Dict com transcrição completa incluindo diarização e timestamps

        Estrutura do resultado:
            {
                "source": "url do áudio",
                "timestamp": "...",
                "durationInTicks": ...,
                "duration": "PT1H2M3.4S",
                "combinedRecognizedPhrases": [
                    {"channel": 0, "lexical": "...", "display": "..."}
                ],
                "recognizedPhrases": [
                    {
                        "channel": 0,
                        "speaker": 1,
                        "offset": "PT0.5S",
                        "duration": "PT5.2S",
                        "nBest": [
                            {
                                "lexical": "texto reconhecido",
                                "display": "Texto reconhecido.",
                                "words": [
                                    {
                                        "word": "texto",
                                        "offset": "PT0.5S",
                                        "duration": "PT0.3S"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        """
        files = await self.get_transcription_files(job_id)

        # Buscar arquivo de transcrição (kind: "Transcription")
        transcription_file = None
        for file in files:
            if file.get("kind") == "Transcription":
                transcription_file = file
                break

        if not transcription_file:
            raise Exception(f"Arquivo de transcrição não encontrado para job {job_id}")

        # Baixar conteúdo do arquivo
        content_url = transcription_file.get("links", {}).get("contentUrl")
        if not content_url:
            raise Exception("URL de conteúdo não encontrada")

        logger.info(f"Baixando resultado da transcrição de: {content_url}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(content_url)
            response.raise_for_status()

        return response.json()

    def parse_transcription_with_diarization(
        self,
        transcription_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parseia o JSON de transcrição do Azure e extrai informações estruturadas.

        Args:
            transcription_json: JSON retornado pelo Azure Speech

        Returns:
            Dict estruturado com:
                - full_text: texto completo
                - speakers: lista de trechos por speaker
                - duration_seconds: duração total
        """
        result = {
            "full_text": "",
            "speakers": [],
            "duration_seconds": 0.0,
            "phrases": []
        }

        # Extrair texto completo
        combined_phrases = transcription_json.get("combinedRecognizedPhrases", [])
        if combined_phrases:
            result["full_text"] = combined_phrases[0].get("display", "")

        # Extrair duração
        duration_str = transcription_json.get("duration", "PT0S")
        result["duration_seconds"] = self._parse_duration(duration_str)

        # Extrair frases com diarização
        recognized_phrases = transcription_json.get("recognizedPhrases", [])

        for phrase in recognized_phrases:
            speaker = phrase.get("speaker", 0)
            offset = self._parse_duration(phrase.get("offset", "PT0S"))
            duration = self._parse_duration(phrase.get("duration", "PT0S"))

            # Pegar melhor reconhecimento
            nbest = phrase.get("nBest", [])
            if not nbest:
                continue

            best_result = nbest[0]
            text = best_result.get("display", "")

            phrase_data = {
                "speaker": speaker,
                "text": text,
                "start_time": offset,
                "end_time": offset + duration,
                "duration": duration,
                "confidence": best_result.get("confidence", 0.0)
            }

            result["phrases"].append(phrase_data)

            # Agregar por speaker
            speaker_entry = next(
                (s for s in result["speakers"] if s["speaker_id"] == speaker),
                None
            )

            if not speaker_entry:
                speaker_entry = {
                    "speaker_id": speaker,
                    "texts": []
                }
                result["speakers"].append(speaker_entry)

            speaker_entry["texts"].append(text)

        return result

    def _parse_duration(self, duration_str: str) -> float:
        """
        Converte string de duração ISO 8601 para segundos.

        Ex: "PT1H2M3.4S" -> 3723.4 segundos
        """
        import re

        if not duration_str or duration_str == "PT0S":
            return 0.0

        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?'
        match = re.match(pattern, duration_str)

        if not match:
            return 0.0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = float(match.group(3) or 0)

        return hours * 3600 + minutes * 60 + seconds


# Instância global do serviço
import asyncio
azure_speech_service = AzureSpeechService()
