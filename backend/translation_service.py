import asyncio
import logging
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

logger = logging.getLogger(__name__)

# Map our language codes to NLLB-200 language codes
NLLB_LANG_MAP = {
    "hi-IN": "hin_Deva",
    "en-IN": "eng_Latn",
    "ta-IN": "tam_Taml",
    "te-IN": "tel_Telu",
    "kn-IN": "kan_Knda",
    "bn-IN": "ben_Beng",
    "mr-IN": "mar_Deva",
    "gu-IN": "guj_Gujr",
}

MODEL_NAME = "facebook/nllb-200-distilled-600M"


class TranslationService:
    def __init__(self):
        logger.info(f"Loading translation model: {MODEL_NAME} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        self.model.eval()
        logger.info("Translation model loaded.")

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text.strip():
            return text

        src_code = NLLB_LANG_MAP.get(source_lang, "hin_Deva")
        tgt_code = NLLB_LANG_MAP.get(target_lang, "eng_Latn")

        # No translation needed if same language
        if src_code == tgt_code:
            return text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._translate_sync, text, src_code, tgt_code
        )

    def _translate_sync(self, text: str, src_code: str, tgt_code: str) -> str:
        try:
            self.tokenizer.src_lang = src_code
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=512,
                truncation=True,
            )

            target_lang_id = self.tokenizer.convert_tokens_to_ids(tgt_code)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    forced_bos_token_id=target_lang_id,
                    max_length=512,
                    num_beams=4,
                    early_stopping=True,
                )

            translated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            logger.info(f"Translation [{src_code} → {tgt_code}]: {translated}")
            return translated

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Fallback to original text
