# CanvasAgent

CanvasAgent provides two complementary interfaces for working with Canvas LMS:

1. A Streamlit chat UI (Python) for interactive exploration and natural language Canvas actions.
2. A Model Context Protocol (MCP) server (TypeScript) exposing safe, structured Canvas tools (assignment creation, rubric attachment, etc.) usable from compatible AI clients (e.g. VS Code Copilot Chat, Claude Desktop).

The codebase has been refactored into a clearer structure:

```text
python/                 # Python package & Streamlit app
  canvas_agent/
    clients/            # Canvas client implementations
    ... (dispatchers, LLM helpers to migrate)
mcp-canvas/             # TypeScript MCP server
  src/                  # Tools & Canvas client wrapper
```

Legacy root scripts have been removed in favor of the packaged layout. Use the packaged Streamlit app under `python/canvas_agent/apps/streamlit_app.py`.

## Features

### Streamlit App

- Sidebar configuration (Canvas URL/token, Ollama model selection)
- Enhanced cached Canvas client (rate-limit resilience & simple caching)
- Natural language intent parsing with optional LLM assistance
- Quick action buttons (courses, modules, assignments, profile)

### MCP Server (`mcp-canvas`)

- Standard MCP stdio server (launches via `node dist/index.js`)
- Tools:
  - `create_assignment`
  - `attach_rubric_to_assignment`
- Robust Canvas REST client with retry, exponential backoff, and typed responses
- Environment fallback: supports `CANVAS_TOKEN` or legacy `CANVAS_API_TOKEN`

## Current Capabilities (Snapshot)

Implemented (Python Streamlit + Dispatcher):
- Courses: list, publish/unpublish
- Assignments: list, create, update (basic fields)
- Quizzes: real quiz creation (Classic) when explicitly requested as "real"/"graded" quiz
- Quiz surrogate via assignment heuristic (generic "create a quiz")
- Quiz questions: basic creation (multiple choice or short answer) via dispatcher action (manual param form or future NL)
- Modules & Items: list, create module, add assignment item
- Pages: list, create
- Files: list, upload (simplified two-step)
- Announcements: list, create
- Students: list
- User profile fetch
- Rubrics: create, list, attach to assignment/quiz

Heuristics:
- Fast parsing for assignment/quiz/page creation, file upload, assignment update, quiz (real vs surrogate) selection
- Due date phrases: tomorrow, next weekday (Mon..Sun), in N days/weeks, explicit YYYY-MM-DD, simple time (5pm)
- Topic extraction ("about X") for auto question/description

MCP Tools (subset):
- create_assignment
- attach_rubric_to_assignment

See `ROADMAP.md` for phased plan.

## Getting a Canvas LMS API Token (Free Teacher Account)

1. Go to the Canvas registration page: <https://canvas.instructure.com/register> and create a Free-for-Teacher account (choose "I'm a Teacher").
2. After confirming email & logging in, your base URL will typically be `https://canvas.instructure.com` (unless using a custom hosted instance). You can verify by looking at the address bar once inside Canvas.
3. Generate an API token:
   - Click **Account** (left global navigation) > **Settings**.
   - Scroll to the **Approved Integrations** section.
   - Click **+ New Access Token**.
   - Add a Purpose (e.g., "CanvasAgent Dev") and optional expiry.
   - Click **Generate Token**.
   - Copy the token immediately (you will not see it again). Store it in a secure place (e.g., `.env` file or Streamlit secrets). Treat it like a password.
4. (Optional) Restrict token scope by creating a Developer Key (institution instances). On Free-for-Teacher this is generally full account scope via token.

## Environment Variables / Secrets

Create a `.env` file (will be ignored by git) with:

```env
CANVAS_BASE_URL=https://canvas.instructure.com
CANVAS_API_TOKEN=YOUR_TOKEN_HERE
```

Or use Streamlit secrets by creating a `.streamlit/secrets.toml`:

```toml
CANVAS_BASE_URL = "https://canvas.instructure.com"
CANVAS_API_TOKEN = "YOUR_TOKEN_HERE"
```

You can copy `secrets.example.toml` to `.streamlit/secrets.toml` and edit.

## Requirements

- Python 3.10+
- Ollama installed locally and at least one model pulled (e.g., `llama3`, `mistral`, etc.)
  - Install site: <https://ollama.ai>
  - Pull a model: `ollama pull llama3`
- Streamlit

## Install & Run

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run python/canvas_agent/apps/streamlit_app.py
```

If you store credentials in `.env`, they will be auto-loaded via `python-dotenv` (included in requirements).

## Usage Flow

1. Start the app (`streamlit run python/canvas_agent/apps/streamlit_app.py`).
2. In the sidebar, confirm the detected Ollama models list. Select one.
3. Enter (or rely on loaded) Canvas Base URL & API Token.
4. Type a prompt like: "list courses" or "list assignments 123".
5. The app tries to match an action; otherwise it sends to the LLM.

## Example Natural Language Prompts

Try in the chat:
- "List courses"
- "Create a quiz about mitosis due in 2 weeks in course 123"
- "Create a real quiz titled 'Cell Cycle Check' about mitosis worth 5 points due tomorrow in course 123"
- "Create a page titled Class Policies about late work in course 123"
- "Upload file syllabus.pdf to course 123"
- "Update assignment 456 set due next Monday 5pm in course 123"
- "Attach rubric 555 to assignment 456 in course 123"

## Security Notes

- Tokens are kept in memory only during the session.
- Do NOT commit tokens to git.
- Add rate limiting or audit logging before production use.

## Project Structure (Simplified)

```text
python/
  canvas_agent/
    __init__.py
    clients/
      canvas_client_enhanced.py
  (legacy root .py scripts to be migrated)

mcp-canvas/
  src/
    index.ts            # MCP server entry
    canvas.ts           # Canvas REST client
    tools/
      create_assignment.ts
      attach_rubric.ts
```

Legacy root-level scripts have been removed; the maintained code lives inside the `python/canvas_agent` package.

## Extending

### Streamlit / Python
Add new Canvas operations to the enhanced client, then expose them through the dispatcher. For LLM-driven intent parsing, update the system prompt enumeration of supported actions.

### MCP Server
Create a new tool file under `mcp-canvas/src/tools/`, export a factory returning a `{ name, description, inputSchema, handler }` object, and register it in `index.ts` in the `tools` array.

## License

MIT (add LICENSE file as needed).
