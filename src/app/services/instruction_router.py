"""Turns a transcription into a routing instruction using Groq.

All routing decisions come from the LLM. This module only builds the prompt and
checks that the answer has the required shape; it never inspects the words of
the transcription to pick an endpoint.
"""

import json
import re
from functools import lru_cache
from typing import Any

from fastapi import HTTPException, status
from groq import Groq, GroqError
from pydantic import ValidationError

from src.app.core.config import get_settings
from src.app.schemas.voice import InstructionPayload
from src.app.services import task_store

SYSTEM_PROMPT = """You are the routing layer of a voice-controlled to-do list API.
You receive a user's spoken instruction (Spanish or English) plus the current task list,
and you answer with the single API call that fulfils the instruction.

Respond with ONLY one JSON object, no prose, no markdown, exactly this shape:
{"endpoint": "<path>", "method": "<HTTP method>", "params": {<arguments>}}

Available API calls:
- List all tasks:          {"endpoint": "/tasks", "method": "GET", "params": {}}
- Create a task:           {"endpoint": "/tasks", "method": "POST", "params": {"title": "<text>"}}
                           ("done" is optional, default false)
- Replace a whole task:    {"endpoint": "/tasks/<id>", "method": "PUT", "params": {"title": "<text>", "done": <true|false>}}
- Update part of a task:   {"endpoint": "/tasks/<id>", "method": "PATCH", "params": {"title": "<text>"} and/or {"done": <true|false>}}
- Delete a task:           {"endpoint": "/tasks/<id>", "method": "DELETE", "params": {}}

Rules:
1. <id> is an integer taken from the current task list. Pick the task whose title best
   matches what the user mentions. Never invent an id that is not in the list.
2. Marking a task as done/completed/finished -> PATCH with {"done": true}.
   Marking it as pending/not done -> PATCH with {"done": false}.
   Renaming a task -> PATCH with {"title": "<new title>"}.
   Only use PUT when the user explicitly replaces both the title and the status.
3. Write task titles in the user's language, short, without filler like "add" or "to my list",
   starting with a capital letter (e.g. "add buy milk to my list" -> "Buy milk").
4. If the instruction mentions a task that is not in the list, or is unclear, answer the
   safest read-only call: {"endpoint": "/tasks", "method": "GET", "params": {}}.
5. params is always an object; use {} when there are no arguments.

Examples (task list: [{"id": 3, "title": "Comprar leche", "done": false}]):
"añade llamar al dentista" -> {"endpoint": "/tasks", "method": "POST", "params": {"title": "Llamar al dentista"}}
"qué tengo pendiente" -> {"endpoint": "/tasks", "method": "GET", "params": {}}
"marca comprar leche como hecha" -> {"endpoint": "/tasks/3", "method": "PATCH", "params": {"done": true}}
"cambia comprar leche por comprar pan" -> {"endpoint": "/tasks/3", "method": "PATCH", "params": {"title": "Comprar pan"}}
"borra la tarea de la leche" -> {"endpoint": "/tasks/3", "method": "DELETE", "params": {}}
"""

_COLLECTION = "/tasks"
_ITEM = re.compile(r"^/tasks/(\d+)$")
_ALLOWED = {
    "GET": "collection",
    "POST": "collection",
    "PUT": "item",
    "PATCH": "item",
    "DELETE": "item",
}
_MAX_ATTEMPTS = 2


@lru_cache
def get_groq_client() -> Groq:
    settings = get_settings()
    return Groq(api_key=settings.groq_api_key, timeout=settings.request_timeout_seconds)


def build_instruction(transcription: str) -> InstructionPayload:
    """Ask the LLM for the routing JSON and validate it (one retry on bad output)."""
    last_error = "empty response"
    for _ in range(_MAX_ATTEMPTS):
        raw = _ask_llm(transcription)
        try:
            return _validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"The language model did not return a valid routing instruction: {last_error}",
    )


def _ask_llm(transcription: str) -> str:
    settings = get_settings()
    context = {"current_tasks": task_store.list_tasks(), "instruction": transcription}
    try:
        completion = get_groq_client().chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except GroqError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq request failed: {exc}",
        ) from exc
    return completion.choices[0].message.content or ""


def _validate(data: Any) -> InstructionPayload:
    """Check the shape of the LLM answer; the routing itself is not changed here."""
    instruction = InstructionPayload.model_validate(data)
    method = instruction.method.upper()
    endpoint = instruction.endpoint.strip().rstrip("/") or "/"

    kind = _ALLOWED.get(method)
    if kind is None:
        raise ValueError(f"unsupported method {method!r}")
    if kind == "collection" and endpoint != _COLLECTION:
        raise ValueError(f"{method} must target {_COLLECTION}, got {endpoint!r}")
    if kind == "item" and not _ITEM.fullmatch(endpoint):
        raise ValueError(f"{method} must target /tasks/<id>, got {endpoint!r}")

    return InstructionPayload(endpoint=endpoint, method=method, params=instruction.params)
