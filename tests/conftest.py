import json
import os
from types import SimpleNamespace

import pytest

# Settings require a key at import time; tests never call the real Groq API.
os.environ.setdefault("GROQ_API_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402

from src.app.main import app  # noqa: E402
from src.app.services import instruction_router, task_store  # noqa: E402


class FakeGroq:
    """Stands in for the Groq client: returns queued chat answers and a fixed transcription."""

    def __init__(self) -> None:
        self.answers: list[str] = []
        self.requests: list[dict] = []
        self.transcription = "add buy milk to my list"
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=self._transcribe))

    def answer(self, payload: dict | str) -> None:
        self.answers.append(payload if isinstance(payload, str) else json.dumps(payload))

    def _chat(self, **kwargs):
        self.requests.append(kwargs)
        content = self.answers.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    def _transcribe(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(text=self.transcription)


@pytest.fixture(autouse=True)
def clean_store():
    task_store.reset()
    yield
    task_store.reset()


@pytest.fixture()
def fake_groq(monkeypatch):
    fake = FakeGroq()
    monkeypatch.setattr(instruction_router, "get_groq_client", lambda: fake)
    monkeypatch.setattr("src.app.services.speech_to_text.get_groq_client", lambda: fake)
    return fake


@pytest.fixture()
def client():
    return TestClient(app)
