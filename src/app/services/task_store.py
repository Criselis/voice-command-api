"""In-memory task storage. Data lives in this module and resets on restart."""

from typing import Any

# Module-level data store required by the project: no database, no files.
tasks: list[dict[str, Any]] = []

# IDs come from a counter (not len(tasks)) so they stay unique after deletes.
_next_id = 1


class TaskNotFoundError(Exception):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task {task_id} not found")
        self.task_id = task_id


def list_tasks() -> list[dict[str, Any]]:
    return [task.copy() for task in tasks]


def get_task(task_id: int) -> dict[str, Any]:
    return _find(task_id).copy()


def create_task(title: str, done: bool = False) -> dict[str, Any]:
    global _next_id
    task = {"id": _next_id, "title": title, "done": done}
    _next_id += 1
    tasks.append(task)
    return task.copy()


def replace_task(task_id: int, title: str, done: bool) -> dict[str, Any]:
    task = _find(task_id)
    task["title"] = title
    task["done"] = done
    return task.copy()


def update_task(task_id: int, title: str | None = None, done: bool | None = None) -> dict[str, Any]:
    task = _find(task_id)
    if title is not None:
        task["title"] = title
    if done is not None:
        task["done"] = done
    return task.copy()


def delete_task(task_id: int) -> dict[str, Any]:
    task = _find(task_id)
    tasks.remove(task)
    return task.copy()


def reset() -> None:
    """Empty the store and restart IDs (used by tests)."""
    global _next_id
    tasks.clear()
    _next_id = 1


def _find(task_id: int) -> dict[str, Any]:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise TaskNotFoundError(task_id)
