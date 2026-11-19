def test_list_starts_empty(client):
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_create_task_assigns_incremental_ids(client):
    first = client.post("/tasks", json={"title": "Buy milk"})
    second = client.post("/tasks", json={"title": "Call mom", "done": True})

    assert first.status_code == 201
    assert first.json() == {"id": 1, "title": "Buy milk", "done": False}
    assert second.json() == {"id": 2, "title": "Call mom", "done": True}
    assert len(client.get("/tasks").json()) == 2


def test_ids_stay_unique_after_delete(client):
    client.post("/tasks", json={"title": "A"})
    client.post("/tasks", json={"title": "B"})
    client.delete("/tasks/2")

    created = client.post("/tasks", json={"title": "C"})
    assert created.json()["id"] == 3


def test_create_requires_title(client):
    assert client.post("/tasks", json={}).status_code == 422
    assert client.post("/tasks", json={"title": ""}).status_code == 422


def test_replace_task(client):
    client.post("/tasks", json={"title": "Old"})
    response = client.put("/tasks/1", json={"title": "New", "done": True})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "New", "done": True}


def test_replace_requires_full_object(client):
    client.post("/tasks", json={"title": "Old"})
    assert client.put("/tasks/1", json={"title": "New"}).status_code == 422


def test_patch_updates_only_given_fields(client):
    client.post("/tasks", json={"title": "Buy milk"})

    done = client.patch("/tasks/1", json={"done": True})
    assert done.json() == {"id": 1, "title": "Buy milk", "done": True}

    renamed = client.patch("/tasks/1", json={"title": "Buy bread"})
    assert renamed.json() == {"id": 1, "title": "Buy bread", "done": True}


def test_patch_with_empty_body_is_rejected(client):
    client.post("/tasks", json={"title": "Buy milk"})
    assert client.patch("/tasks/1", json={}).status_code == 422


def test_delete_task(client):
    client.post("/tasks", json={"title": "Buy milk"})
    response = client.delete("/tasks/1")

    assert response.status_code == 200
    assert "deleted" in response.json()["message"]
    assert client.get("/tasks").json() == []


def test_missing_task_returns_404(client):
    assert client.put("/tasks/99", json={"title": "X", "done": False}).status_code == 404
    assert client.patch("/tasks/99", json={"done": True}).status_code == 404
    assert client.delete("/tasks/99").status_code == 404
