"""
Serviço de conversão de áudio para formatos compatíveis com Azure Speech.
Usa FFmpeg para converter qualquer formato de áudio/vídeo para WAV.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import BinaryIO, Tuple
from loguru import logger


class AudioConverterService:
    """Serviço para converter áudios para formato compatível com Azure Speech"""

    # Configurações do WAV de saída
    # Azure Speech recomenda: 16kHz, mono, 16-bit PCM
    OUTPUT_FORMAT = "wav"
    SAMPLE_RATE = 16000
    CHANNELS = 1
    AUDIO_CODEC = "pcm_s16le"  # 16-bit PCM

    def convert_to_wav(
        self,
        input_file: BinaryIO,
        input_filename: str
    ) -> Tuple[bytes, str]:
        """
        Converte qualquer arquivo de áudio/vídeo para WAV compatível com Azure Speech.

        Args:
            input_file: Arquivo de entrada (BytesIO ou similar)
            input_filename: Nome original do arquivo (para detectar extensão)

        Returns:
            Tuple[bytes, str]: (conteúdo WAV em bytes, novo nome do arquivo)

        Raises:
            Exception: Se a conversão falhar
        """
        input_ext = Path(input_filename).suffix.lower()
        output_filename = Path(input_filename).stem + ".wav"

        logger.info(
            f"Convertendo {input_filename} ({input_ext}) para WAV "
            f"({self.SAMPLE_RATE}Hz, {self.CHANNELS} canal)"
        )

        # Criar arquivos temporários
        with tempfile.NamedTemporaryFile(
            suffix=input_ext,
            delete=False
        ) as temp_input:
            temp_input_path = temp_input.name
            temp_input.write(input_file.read())

        output_path = tempfile.mktemp(suffix=".wav")

        try:
            # Executar FFmpeg
            command = [
                "ffmpeg",
                "-i", temp_input_path,           # Arquivo de entrada
                "-ar", str(self.SAMPLE_RATE),    # Sample rate
                "-ac", str(self.CHANNELS),       # Canais (mono)
                "-acodec", self.AUDIO_CODEC,     # Codec de áudio
                "-y",                             # Sobrescrever output
                output_path                       # Arquivo de saída
            ]

            logger.debug(f"Executando comando: {' '.join(command)}")

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos max
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg stderr: {result.stderr}")
                raise Exception(f"Erro na conversão FFmpeg: {result.stderr}")

            # Ler arquivo convertido
            with open(output_path, "rb") as f:
                wav_content = f.read()

            original_size = os.path.getsize(temp_input_path)
            converted_size = len(wav_content)

            logger.info(
                f"Conversão concluída: {input_filename} -> {output_filename} "
                f"({original_size / 1024:.2f}KB -> {converted_size / 1024:.2f}KB)"
            )

            return wav_content, output_filename

        except subprocess.TimeoutExpired:
            logger.error("Timeout na conversão de áudio")
            raise Exception("Conversão de áudio excedeu tempo limite de 5 minutos")

        except Exception as e:
            logger.error(f"Erro na conversão de áudio: {str(e)}")
            raise

        finally:
            # Limpar arquivos temporários
            try:
                os.unlink(temp_input_path)
            except:
                pass

            try:
                os.unlink(output_path)
            except:
                pass

    def is_conversion_needed(self, filename: str) -> bool:
        """
        Verifica se o arquivo precisa ser convertido.

        Args:
            filename: Nome do arquivo

        Returns:
            True se precisa conversão, False se já é WAV
        """
        ext = Path(filename).suffix.lower()
        return ext != ".wav"

    def get_audio_info(self, file_path: str) -> dict:
        """
        Obtém informações sobre um arquivo de áudio usando FFprobe.

        Args:
            file_path: Caminho do arquivo

        Returns:
            Dict com informações do áudio (duração, codec, sample_rate, etc.)
        """
        try:
            command = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
            else:
                logger.warning(f"Erro ao obter info do áudio: {result.stderr}")
                return {}

        except Exception as e:
            logger.error(f"Erro ao executar ffprobe: {str(e)}")
            return {}


# Instância global do serviço
audio_converter_service = AudioConverterService()
