import httpx
import logging
import os

logger = logging.getLogger(__name__)

# Best speaker voice per language for Sarvam bulbul:v3
SARVAM_SPEAKERS = {
    "hi-IN": "ritu",
    "en-IN": "ritu",
    "ta-IN": "pavithra",
    "te-IN": "arvind",
    "kn-IN": "suresh",
    "bn-IN": "amartya",
    "mr-IN": "ritu",
    "gu-IN": "ritu",
}


class TTSService:
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        self.base_url = "https://api.sarvam.ai/text-to-speech"

        if not self.api_key:
            logger.warning("SARVAM_API_KEY not set! TTS will fail.")

    async def synthesize(self, text: str, target_lang: str) -> str:
        """
        Returns base64-encoded WAV audio string from Sarvam TTS.
        """
        if not text.strip():
            return ""

        speaker = SARVAM_SPEAKERS.get(target_lang, "ritu")

        payload = {
            "inputs": [text[:500]],          # Sarvam max input length
            "target_language_code": target_lang,
            "speaker": speaker,
            "model": "bulbul:v3",
            "pace": 1.05,
            "speech_sample_rate": 22050,
            "enable_preprocessing": True,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers={
                        "api-subscription-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                # Sarvam returns {"audios": ["<base64_wav>", ...]}
                audios = data.get("audios", [])
                if audios:
                    return audios[0]
                return ""

            except httpx.HTTPStatusError as e:
                logger.error(f"Sarvam TTS HTTP error {e.response.status_code}: {e.response.text}")
                return ""
            except Exception as e:
                logger.error(f"Sarvam TTS error: {e}")
                return ""
