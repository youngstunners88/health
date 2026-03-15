import os
import json
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger("translate")

LIBRETRANSLATE_URL = os.getenv(
    "LIBRETRANSLATE_URL", "https://libretranslate.de/translate"
)  # public demo; replace with your own instance
LIBRETRANSLATE_API_KEY = os.getenv("LIBRETRANSLATE_API_KEY")  # optional

def translate(
    text: str,
    source_lang: str = "en",
    target_lang: str = "es",
    format: str = "text",
) -> Dict[str, Any]:
    """
    Returns {translated_text, source, target, raw_response}.
    """
    payload = {
        "q": text,
        "source": source_lang,
        "target": target_lang,
        "format": format,
    }
    headers = {"Content-Type": "application/json"}
    if LIBRETRANSLATE_API_KEY:
        headers["X-Api-Key"] = LIBRETRANSLATE_API_KEY

    logger.info(f"Translating {len(text)} chars from {source_lang}→{target_lang}")
    resp = requests.post(LIBRETRANSLATE_URL, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    translated = data.get("translatedText", "")
    logger.debug(f"Translation result: {translated[:80]}...")
    return {
        "translated_text": translated,
        "source": source_lang,
        "target": target_lang,
        "raw": data,
    }

__all__ = ["translate"]