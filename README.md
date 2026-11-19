# Voice Command API at 4Geeks Academy

## ✅ Solution overview

Voice → transcription → routing (Groq LLM) → task action, all in memory.

| Endpoint | What it does |
|---|---|
| `GET /tasks` | List all tasks (200) |
| `POST /tasks` | Create `{title, done=false}`, returns the task with a unique id (201) |
| `PUT /tasks/{task_id}` | Replace `title` and `done` (200, 404 if missing) |
| `PATCH /tasks/{task_id}` | Update `title` and/or `done` (200, 404 if missing, 422 if empty) |
| `DELETE /tasks/{task_id}` | Delete and return a confirmation message (200, 404 if missing) |
| `POST /instruction` | `{"transcription": "..."}` → Groq → `{"endpoint", "method", "params"}`. Only routes, never executes |
| `POST /transcribe` | Audio (`multipart/form-data`, field `file`, optional `language`) or JSON `{"transcription"}` → Whisper on Groq → same routing as `/instruction` → executes the action → `{transcription, instruction, result}` |

**How it is built** (`src/app/services/`):

- `task_store.py` — module-level `tasks` list; ids come from a counter, so they stay unique after deletes.
- `instruction_router.py` — system prompt that forces a single JSON object, Groq JSON mode (`response_format={"type": "json_object"}`, `temperature=0`) and the current task list sent as context so the model can resolve "mark buy milk as done" to the right id. The answer is validated (allowed methods, `/tasks` vs `/tasks/<id>`) and retried once if malformed. There is no keyword matching on the transcription: every routing decision comes from the LLM.
- `speech_to_text.py` — Groq Whisper (`GROQ_TRANSCRIPTION_MODEL`).
- `task_executor.py` — runs the routed instruction against the store, with the same validation as the `/tasks` endpoints.

**Run it**

```bash
cp .env.example .env          # set GROQ_API_KEY (never commit .env; it is in .gitignore)
uv sync
uv run uvicorn src.main:app --reload
uv run pytest                 # 19 tests; Groq is mocked, no API key needed
```

```bash
cd frontend && cp .env.example .env && npm install && npm run dev   # http://localhost:5173
```

CORS origins come from `ALLOWED_ORIGINS` in `.env` (defaults allow the Vite dev server on port 5173).

---

<!-- hide -->

By [@ehiber](https://github.com/ehiber) and [other contributors](https://github.com/4GeeksAcademy/voice-command-api/graphs/contributors) at [4Geeks Academy](https://4geeksacademy.com/)

[![build by developers](https://img.shields.io/badge/build_by-Developers-blue)](https://4geeks.com)
[![4Geeks Academy](https://img.shields.io/twitter/follow/4geeksacademy?style=social&logo=x)](https://x.com/4geeksacademy)

_Estas instrucciones tambien estan disponibles en [espanol](./README.es.md)._

**Before you start**: Read the [how to start a coding project](https://4geeks.com/lesson/how-to-start-a-project) guide before writing code.

> We need you! These exercises are built and maintained in collaboration with people like you. If you find any bug 🐞 or typo, please contribute and/or report it.

<!-- endhide -->

---

## 🎯 Your challenge

This repository is the starter template for the **Voice Command API** project.

The frontend is already built. It records up to **20 seconds** of audio in the browser, sends that audio to your backend, and shows:

- the transcription returned by the API
- the final task response returned by the API

Your job is to implement the backend so the full voice-to-action flow works end to end.

---

## How the project works

The frontend uses a single public entry point:

- `POST /transcribe`

The frontend does **not** resolve intents with the Web Speech API. It only captures audio (up to 20 seconds), sends the file to `POST /transcribe`, and shows the backend transcription to make debugging easier.

That endpoint must:

1. receive recorded audio from the frontend
2. transcribe it to text
3. reuse the same routing logic as `POST /instruction`
4. execute the corresponding task action in memory
5. return the transcription, the instruction payload, and the final result

Your backend must also expose:

- `POST /instruction`
- `GET /tasks`
- `POST /tasks`
- `PUT /tasks/{task_id}`
- `PATCH /tasks/{task_id}`
- `DELETE /tasks/{task_id}`

Important:

- Use **in-memory storage only**. No database and no files.
- The frontend is provided and should not be modified as part of the exercise.
- The backend included in this repository is only a template. You must implement the missing logic.

---

## Repository structure

```text
voice-command-api/
|-- .devcontainer/           # Codespaces setup
|-- frontend/                # Ready-made frontend
|   |-- public/
|   `-- src/
|-- src/
|   `-- app/
|       |-- api/routes/      # /transcribe, /instruction, /tasks
|       |-- core/            # Settings and config
|       |-- schemas/         # Request and response contracts
|       |-- services/        # Your implementation goes here
|       `-- utils/
|-- pyproject.toml
|-- README.md
`-- README.es.md
```

---

## 🌱 How to start the project

You can open this project in [GitHub Codespaces](https://codespaces.new/4GeeksAcademy/voice-command-api) or clone it locally.

If you use Codespaces, the repository already includes a `.devcontainer` prepared for Python, Node, FastAPI, and Vite.

### Option A: GitHub Codespaces

1. Open the repository in Codespaces.
2. Wait for the dev container to finish installing dependencies.
3. Create `.env` from `.env.example`.
4. Create `frontend/.env` from `frontend/.env.example`.
5. Run the backend and frontend from the terminal tabs.

### Option B: Local setup

```bash
git clone https://github.com/4GeeksAcademy/voice-command-api
cd voice-command-api
```

Create your own repository and update the remote:

```bash
git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY
```

### Backend setup

Create a `.env` file from `.env.example` and fill in your Groq credentials.

Install dependencies and run the API:

```bash
uv sync
uv run uvicorn src.main:app --reload
```

### Frontend setup

Create `frontend/.env` from `frontend/.env.example`.

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

---

## 💻 What you need to do

- [ ] Create a module-level `tasks` list with `id`, `title`, and `done`, using unique incremental IDs.
- [ ] Implement `GET /tasks`, `POST /tasks`, `PUT /tasks/{task_id}`, `PATCH /tasks/{task_id}`, and `DELETE /tasks/{task_id}` using in-memory state.
- [ ] Implement `POST /instruction` to receive `{ "transcription": "..." }`, call Groq, and return **only** routing JSON (no task execution):

```json
{
  "endpoint": "/tasks",
  "method": "POST",
  "params": { "title": "Buy groceries" }
}
```

- [ ] Implement `POST /transcribe` to accept `multipart/form-data`, convert audio to text, reuse `/instruction` logic, execute the selected action, and return `transcription`, `instruction`, and `result`.
- [ ] Do not hardcode intent matching with manual rules such as `if "add" in text`.

⚠️ **IMPORTANT:** The frontend does not resolve intents with Web Speech API. It only captures audio (up to 20 seconds), sends it to `POST /transcribe`, and shows backend transcription to debug STT vs. routing issues.

```json
{
  "transcription": "add buy groceries to my list",
  "instruction": {
    "endpoint": "/tasks",
    "method": "POST",
    "params": {
      "title": "Buy groceries"
    }
  },
  "result": {
    "id": 1,
    "title": "Buy groceries",
    "done": false
  }
}
```

---

## Debugging tip

If the transcription shown in the frontend is already wrong, the problem is in the audio capture or speech-to-text step.

If the transcription is correct but the action is wrong, the problem is in `/instruction`.

---

## ✅ What we will evaluate

- [ ] `POST /transcribe` accepts audio, transcribes it, and reuses `/instruction` routing logic.
- [ ] `POST /instruction` receives plain text and returns only routing JSON (no action execution).
- [ ] `GET /tasks`, `POST /tasks`, `PUT /tasks/{task_id}`, `PATCH /tasks/{task_id}`, and `DELETE /tasks/{task_id}` work correctly with in-memory state.
- [ ] The frontend displays the transcription returned by the backend to help distinguish STT errors from routing errors.

---

## 📦 How to submit this project

1. Push your solution to your GitHub repository.
2. Make sure backend and frontend are included and runnable locally.
3. Share the repository URL and a short video/GIF showing:
   - audio recording (20 seconds max),
   - transcription visible in the frontend,
   - correct task action execution.

---

This and many other projects are built by students as part of the [Coding Bootcamps](https://4geeksacademy.com/) at 4Geeks Academy. Learn more about the [Full-Stack Software Developer](https://4geeksacademy.com/en/career-programs/full-stack), [Data Science & Machine Learning](https://4geeksacademy.com/en/career-programs/data-science-ml), [Cybersecurity](https://4geeksacademy.com/en/career-programs/cybersecurity), and [AI Engineering](https://4geeksacademy.com/en/career-programs/ai-engineering) programs.
