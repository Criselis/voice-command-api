"""Executes a routing instruction against the in-memory task store."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from src.app.schemas.voice import InstructionPayload, Task, TaskCreate, TaskReplace, TaskUpdate
from src.app.services import task_store
from src.app.services.task_store import TaskNotFoundError


def execute_instruction(instruction: InstructionPayload) -> Any:
    """Run the same operation the matching /tasks endpoint would run."""
    method = instruction.method.upper()
    params = instruction.params
    try:
        if method == "GET":
            return [Task(**task).model_dump() for task in task_store.list_tasks()]
        if method == "POST":
            body = TaskCreate.model_validate(params)
            return task_store.create_task(body.title, body.done)

        task_id = int(instruction.endpoint.rsplit("/", 1)[1])
        if method == "PUT":
            body = TaskReplace.model_validate(params)
            return task_store.replace_task(task_id, body.title, body.done)
        if method == "PATCH":
            body = TaskUpdate.model_validate(params)
            return task_store.update_task(task_id, body.title, body.done)
        if method == "DELETE":
            task = task_store.delete_task(task_id)
            return {"message": f"Task {task['id']} '{task['title']}' deleted"}
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"instruction": instruction.model_dump(), "errors": exc.errors()},
        ) from exc
    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {exc.task_id} not found",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported method {method}",
    )
