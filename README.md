# CanvasAgent

A Streamlit chat interface that lets you:

1. Select a local Ollama LLM model from a dropdown and chat.
2. Connect to a Canvas LMS test/teacher (Free for Teachers) account via API.
3. Ask the LLM to perform Canvas actions (list courses, list assignments, download/upload files, etc.).
4. Download course files locally and upload new files to Canvas.

> NOTE: This is an initial scaffold. Further refinement, authentication hardening, and function/tool grounding for complex multi-step actions can be added incrementally.

## Features (Initial Scope)

- Streamlit UI with sidebar for settings
  - Enter Canvas Base URL & API Token (securely via `st.secrets` or sidebar inputs)
  - Select Ollama model (auto-detected via `ollama list`)
- Conversational memory stored in `st.session_state`
- Canvas helper client wrapping common endpoints (Courses, Assignments, Files)
- Basic tool functions exposed to the LLM via a simple pattern (non-agentic baseline)

## Roadmap (Suggested Next Steps)

- Add function-calling / tool routing (e.g., with OpenAI-compatible schema or custom planner)
- Add retry & rate limiting logic
- Add caching of Canvas responses
- Add multi-user auth & per-user secret storage
- Add unit tests & CI pipeline

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

## Project Structure

```text
app.py                # Streamlit UI & chat loop
canvas_client.py      # Canvas API wrapper
llm.py                # Ollama interaction utilities
actions.py            # Mapping from user intents to Canvas actions
requirements.txt
README.md
```

## Extending Actions

Add new functions in `actions.py` that accept `(client, params)` and register them in the ACTIONS dict. Provide a better intent parser or integrate structured function calling.

## License

MIT (add LICENSE file as needed).
