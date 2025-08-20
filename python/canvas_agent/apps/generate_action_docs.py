"""Utility script to regenerate action reference markdown using action_metadata.
Run manually when actions change.
"""
import pathlib, sys
APP_FILE = pathlib.Path(__file__).resolve()
PROJECT_ROOT = APP_FILE.parents[3]  # .../CanvasAgent
PYTHON_DIR = PROJECT_ROOT / 'python'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))
from canvas_agent.action_metadata import generate_actions_markdown

def main():
    md = generate_actions_markdown()
    out = pathlib.Path(__file__).resolve().parent.parent / "ACTION_REFERENCE.md"
    out.write_text(md, encoding='utf-8')
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
