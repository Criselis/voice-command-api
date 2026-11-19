"""Speech-to-text with Groq Whisper."""

from fastapi import HTTPException, status
from groq import GroqError

from src.app.core.config import get_settings
from src.app.services.instruction_router import get_groq_client


def transcribe_audio(filename: str, audio: bytes, language: str | None) -> str:
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The audio file is empty.",
        )
    try:
        result = get_groq_client().audio.transcriptions.create(
            model=get_settings().groq_transcription_model,
            file=(filename, audio),
            language=language,
            temperature=0,
        )
    except GroqError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq transcription failed: {exc}",
        ) from exc

    text = (result.text or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No speech was detected in the audio. Try speaking closer to the microphone.",
        )
    return text
