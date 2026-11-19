import json


def test_instruction_returns_llm_routing_without_executing(client, fake_groq):
    fake_groq.answer({"endpoint": "/tasks", "method": "post", "params": {"title": "Buy milk"}})

    response = client.post("/instruction", json={"transcription": "add buy milk to my list"})

    assert response.status_code == 200
    assert response.json() == {"endpoint": "/tasks", "method": "POST", "params": {"title": "Buy milk"}}
    # /instruction only routes: nothing was created
    assert client.get("/tasks").json() == []


def test_instruction_sends_json_mode_and_current_tasks(client, fake_groq):
    client.post("/tasks", json={"title": "Comprar leche"})
    fake_groq.answer({"endpoint": "/tasks/1", "method": "PATCH", "params": {"done": True}})

    client.post("/instruction", json={"transcription": "marca comprar leche como hecha"})

    request = fake_groq.requests[0]
    assert request["response_format"] == {"type": "json_object"}
    assert request["messages"][0]["role"] == "system"
    user_payload = json.loads(request["messages"][1]["content"])
    assert user_payload["current_tasks"] == [{"id": 1, "title": "Comprar leche", "done": False}]
    assert user_payload["instruction"] == "marca comprar leche como hecha"


def test_instruction_retries_once_on_invalid_json(client, fake_groq):
    fake_groq.answer("Sure! Here is your task.")
    fake_groq.answer({"endpoint": "/tasks", "method": "GET", "params": {}})

    response = client.post("/instruction", json={"transcription": "what do I have to do"})

    assert response.status_code == 200
    assert response.json()["method"] == "GET"


def test_instruction_rejects_malformed_routing(client, fake_groq):
    fake_groq.answer({"endpoint": "/tasks", "method": "DELETE", "params": {}})
    fake_groq.answer({"endpoint": "/users", "method": "GET", "params": {}})

    response = client.post("/instruction", json={"transcription": "delete everything"})

    assert response.status_code == 502


def test_instruction_requires_transcription(client):
    assert client.post("/instruction", json={"transcription": ""}).status_code == 422


def test_transcribe_audio_creates_task(client, fake_groq):
    fake_groq.answer({"endpoint": "/tasks", "method": "POST", "params": {"title": "Buy milk"}})

    response = client.post(
        "/transcribe",
        files={"file": ("recording.webm", b"fake-audio", "audio/webm")},
        data={"language": "en"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "transcription": "add buy milk to my list",
        "instruction": {"endpoint": "/tasks", "method": "POST", "params": {"title": "Buy milk"}},
        "result": {"id": 1, "title": "Buy milk", "done": False},
    }
    transcription_request = fake_groq.requests[0]
    assert transcription_request["file"] == ("recording.webm", b"fake-audio")
    assert transcription_request["language"] == "en"


def test_transcribe_manual_text_runs_update_and_delete(client, fake_groq):
    client.post("/tasks", json={"title": "Comprar leche"})

    fake_groq.answer({"endpoint": "/tasks/1", "method": "PATCH", "params": {"done": True}})
    updated = client.post("/transcribe", json={"transcription": "marca comprar leche como hecha"})
    assert updated.json()["result"] == {"id": 1, "title": "Comprar leche", "done": True}

    fake_groq.answer({"endpoint": "/tasks", "method": "GET", "params": {}})
    listed = client.post("/transcribe", json={"transcription": "qué tengo pendiente"})
    assert listed.json()["result"] == [{"id": 1, "title": "Comprar leche", "done": True}]

    fake_groq.answer({"endpoint": "/tasks/1", "method": "DELETE", "params": {}})
    deleted = client.post("/transcribe", json={"transcription": "borra la tarea de la leche"})
    assert deleted.status_code == 200
    assert client.get("/tasks").json() == []


def test_transcribe_unknown_task_returns_404(client, fake_groq):
    fake_groq.answer({"endpoint": "/tasks/7", "method": "DELETE", "params": {}})
    response = client.post("/transcribe", json={"transcription": "borra la tarea siete"})
    assert response.status_code == 404


def test_transcribe_requires_file_field(client):
    response = client.post("/transcribe", files={"audio": ("a.webm", b"x", "audio/webm")})
    assert response.status_code == 400
