from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
# request.form() yields Starlette's UploadFile (fastapi.UploadFile is a subclass of it)
from starlette.datastructures import UploadFile

from src.app.schemas.voice import InstructionRequest, TranscribeFlowResponse
from src.app.services.instruction_router import build_instruction
from src.app.services.speech_to_text import transcribe_audio
from src.app.services.task_executor import execute_instruction
from src.app.utils.language import normalize_transcription_language

router = APIRouter(tags=["transcribe"])


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    """Audio (multipart 'file' + optional 'language') or JSON {"transcription"} ->
    text -> routing instruction (same logic as /instruction) -> executed action."""
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Send the recording in a multipart field named 'file'.",
            )
        language = normalize_transcription_language(form.get("language"))
        audio = await upload.read()
        transcription = await run_in_threadpool(
            transcribe_audio, upload.filename or "audio.webm", audio, language
        )
    elif content_type.startswith("application/json"):
        try:
            transcription = InstructionRequest.model_validate(await request.json()).transcription
        except (ValidationError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='Send JSON like {"transcription": "add buy milk"}.',
            ) from exc
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Use multipart/form-data with an audio 'file' or application/json with 'transcription'.",
        )

    instruction = await run_in_threadpool(build_instruction, transcription)
    result = execute_instruction(instruction)
    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )
