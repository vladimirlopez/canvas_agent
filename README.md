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

Legacy root scripts remain temporarily for backward compatibility and will be migrated / deprecated in subsequent passes.

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

## Roadmap (Next Refactor Steps)

- Finish migrating Python modules into `python/canvas_agent/` package (dispatcher, LLM helpers)
- Replace duplicate legacy clients with single maintained enhanced client
- Add tests for MCP tools (mock Canvas responses)
- Introduce unified configuration loader (Python + Node share .env contract)
- Optional: Add additional MCP tools (module creation, file upload)

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
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

If you store credentials in `.env`, they will be auto-loaded via `python-dotenv` (included in requirements).

## Usage Flow

1. Start the app.
2. In the sidebar, confirm the detected Ollama models list. Select one.
3. Enter (or rely on loaded) Canvas Base URL & API Token.
4. Type a prompt like: "list courses" or "list assignments 123".
5. The app tries to match an action; otherwise it sends to the LLM.

## Supported Action Commands (naive parsing)

- `list courses`
- `list assignments <course_id>`
- `list files <course_id>`
- `download file <file_id>` (saved to `downloads/<file_id>`)
- `upload file <course_id> <local_path>`

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

Root-level scripts like `app.py`, `app_enhanced.py`, and helpers will gradually move under `python/canvas_agent/`.

## Extending

### Streamlit / Python
Add new Canvas operations to the enhanced client, then expose them through the dispatcher. For LLM-driven intent parsing, update the system prompt enumeration of supported actions.

### MCP Server
Create a new tool file under `mcp-canvas/src/tools/`, export a factory returning a `{ name, description, inputSchema, handler }` object, and register it in `index.ts` in the `tools` array.

## License

MIT (add LICENSE file as needed).
