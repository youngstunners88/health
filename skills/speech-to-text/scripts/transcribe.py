import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("speech_to_text")

# Lazy import to avoid heavy dependency if not used
def _get_whisper_model(model_size: str = "base"):
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        logger.error(f"faster-whisper not installed: {e}")
        raise RuntimeError("faster-whisper package required for speech-to-text skill")
    # Use CPU, int8 for speed; adjust as needed
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return model

def transcribe(audio_path: str, language: Optional[str] = None, model_size: str = "base") -> Dict[str, Any]:
    """
    Transcribe audio file to text.
    Returns {text, language, segments, audio_path}
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    model = _get_whisper_model(model_size)
    # transcription returns generator of segments and info
    segments, info = model.transcribe(audio_path, language=language, beam_size=5)
    text = " ".join([segment.text for segment in segments]).strip()
    logger.info(f"Transcribed {audio_path}: detected language {info.language} ({info.language_probability:.2f})")
    return {
        "text": text,
        "language": info.language,
        "language_probability": float(info.language_probability),
        "audio_path": audio_path,
        "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
    }

__all__ = ["transcribe"]