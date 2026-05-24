import asyncio
import tempfile
import os
import subprocess
import logging
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Map our language codes to Whisper language codes
WHISPER_LANG_MAP = {
    "hi-IN": "hi",
    "en-IN": "en",
    "ta-IN": "ta",
    "te-IN": "te",
    "kn-IN": "kn",
    "bn-IN": "bn",
    "mr-IN": "mr",
    "gu-IN": "gu",
}


class STTService:
    def __init__(self, model_size: str = "medium"):
        logger.info(f"Loading Whisper model: {model_size} ...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Whisper model loaded.")

    async def transcribe(self, audio_bytes: bytes, source_lang: str) -> str:
        whisper_lang = WHISPER_LANG_MAP.get(source_lang, "hi")
        loop = asyncio.get_event_loop()
        transcript = await loop.run_in_executor(
            None, self._transcribe_sync, audio_bytes, whisper_lang
        )
        return transcript

    def _transcribe_sync(self, audio_bytes: bytes, lang: str) -> str:
        webm_path = None
        wav_path = None
        try:
            # Write incoming WebM bytes to temp file
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_bytes)
                webm_path = f.name

            wav_path = webm_path.replace(".webm", ".wav")

            # Convert WebM/Opus → 16kHz mono WAV using ffmpeg
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", webm_path,
                    "-ar", "16000",
                    "-ac", "1",
                    "-f", "wav",
                    wav_path,
                ],
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg error: {result.stderr.decode()}")
                return ""

            # Run Whisper
            segments, info = self.model.transcribe(
                wav_path,
                language=lang,
                beam_size=5,
                best_of=5,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=False,
            )

            transcript = " ".join(seg.text for seg in segments).strip()
            logger.info(f"STT [{lang}]: {transcript}")
            return transcript

        except Exception as e:
            logger.error(f"STT error: {e}")
            return ""
        finally:
            if webm_path and os.path.exists(webm_path):
                os.unlink(webm_path)
            if wav_path and os.path.exists(wav_path):
                os.unlink(wav_path)
