import os
import json
import logging
import subprocess
import base64
from typing import Dict, Any

logger = logging.getLogger("tts")

CHARSIU_CMD = os.getenv(
    "CHARSIU_CMD", "charsiu"
)  # expects `charsiu predict --model <model> --input <text>`
ESPEAK_CMD = os.getenv(
    "ESPEAK_CMD", "espeak-ng"
)  # expects `espeak-ng -v <voice> -w <out.wav> --phonetize=<phoneme_file>`

DEFAULT_CHARSIU_MODEL = os.getenv(
    "CHARSIU_MODEL", "eng"
)  # adjust per language
DEFAULT_ESPEAK_VOICE = os.getenv("ESPEAK_VOICE", "en")

def _run_charsiu(text: str) -> str:
    """
    Returns phoneme string (one line). Adjust arguments for your model.
    """
    proc = subprocess.run(
        [CHARSIU_CMD, "predict", "--model", DEFAULT_CHARSIU_MODEL, "--input", text],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        logger.error(f"Charsiu failed: {proc.stderr}")
        raise RuntimeError("CharsiuG2P execution failed")
    return proc.stdout.strip()

def _run_espeak(phonemes: str, out_wav: str) -> None:
    """
    Calls eSpeak‑NG to turn phoneme string into a WAV file.
    """
    # Write phonemes to a temp file because espeak expects a file for --phonetize
    with open("/tmp/phonemes.txt", "w", encoding="utf-8") as f:
        f.write(phonemes + "\n")
    proc = subprocess.run(
        [
            ESPEAK_CMD,
            "-v",
            DEFAULT_ESPEAK_VOICE,
            "-w",
            out_wav,
            "--phonetize",
            "/tmp/phonemes.txt",
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        logger.error(f"eSpeak‑NG failed: {proc.stderr}")
        raise RuntimeError("eSpeak‑NG execution failed")

def synthesize(
    text: str,
    out_path: str = "/tmp/tts_output.wav",
) -> Dict[str, Any]:
    """
    Returns {wav_base64, sample_rate_hz, duration_sec, text_input}
    """
    logger.info(f"Synthesizing TTS for {len(text)} chars")
    phonemes = _run_charsiu(text)
    _run_espeak(phonemes, out_path)

    with open(out_path, "rb") as f:
        wav_bytes = f.read()
    wav_b64 = base64.b64encode(wav_bytes).decode("ascii")

    # Very rough duration estimate: len(wav) / (sample_rate * bytes_per_sample)
    # Assuming 16‑bit mono, 22050 Hz (default eSpeak‑NG)
    sample_rate = 22050
    bytes_per_sample = 2
    duration_sec = len(wav_bytes) / (sample_rate * bytes_per_sample)

    return {
        "wav_base64": wav_b64,
        "sample_rate_hz": sample_rate,
        "duration_sec": round(duration_sec, 3),
        "text_input": text,
        "phonemes": phonemes,
    }

__all__ = ["synthesize"]