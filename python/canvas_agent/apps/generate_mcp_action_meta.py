"""Generate confirmation/action metadata JSON for MCP server from ACTION_METADATA.
Output: mcp-canvas/generated_action_meta.json
Structure: {"actions": { action_name: {"confirm": true/false } }}
"""
from __future__ import annotations
import json, pathlib, sys

APP_FILE = pathlib.Path(__file__).resolve()
PROJECT_ROOT = APP_FILE.parents[3]
PYTHON_DIR = PROJECT_ROOT / 'python'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from canvas_agent.action_metadata import ACTION_METADATA  # type: ignore

def main():
    out = {"actions": {}}
    for name, meta in ACTION_METADATA.items():
        if meta.get('confirm'):
            out['actions'][name] = {"confirm": True}
    target = PROJECT_ROOT / 'mcp-canvas' / 'generated_action_meta.json'
    target.write_text(json.dumps(out, indent=2))
    print(f"Wrote {target}")

if __name__ == '__main__':
    main()
