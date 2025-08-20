"""Generate MCP JSON Schemas from single Python ACTION_METADATA source.

Output file: mcp-canvas/generated_action_schemas.json

Heuristics:
- *_id, points_possible, module_id, quiz_id, rubric_id, content_id -> number
- due_at -> string (date-time format)
- answers -> array of strings
- criteria / rubric_criteria -> array (items object with description, points)
- question -> string
- booleans: published, confirm (not included as param), use_for_grading
- fallback type: string
"""
from __future__ import annotations
import json, re, pathlib, sys
from typing import Dict, Any

# Path bootstrap (similar to docs generator)
APP_FILE = pathlib.Path(__file__).resolve()
PROJECT_ROOT = APP_FILE.parents[3]
PYTHON_DIR = PROJECT_ROOT / 'python'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from canvas_agent.action_metadata import ACTION_METADATA  # type: ignore

NUMERIC_KEYS = {"course_id","assignment_id","module_id","quiz_id","rubric_id","association_id","content_id","points_possible"}
BOOLEAN_KEYS = {"published","use_for_grading"}
ARRAY_STRING_KEYS = {"answers"}
ARRAY_CRITERIA_KEYS = {"criteria","rubric_criteria"}
DATE_KEYS = {"due_at"}


def _infer_property_schema(name: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    desc = meta.get("description", "")
    if name in NUMERIC_KEYS or name.endswith('_id'):
        return {"type": "number", "description": desc}
    if name in BOOLEAN_KEYS:
        return {"type": "boolean", "description": desc}
    if name in DATE_KEYS:
        return {"type": "string", "format": "date-time", "description": desc}
    if name in ARRAY_STRING_KEYS:
        return {"type": "array", "items": {"type": "string"}, "description": desc or "List of strings"}
    if name in ARRAY_CRITERIA_KEYS:
        return {"type": "array", "items": {"type": "object", "properties": {"description": {"type":"string"}, "points": {"type":"number"}}, "required": ["description","points"]}, "description": desc or "List of criteria"}
    # Default string
    return {"type": "string", "description": desc}


def build_json_schemas(actions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"actions": {}}
    for name, info in sorted(actions.items()):
        params = info.get("params", {})
        properties = {}
        required = []
        for p, pmeta in params.items():
            properties[p] = _infer_property_schema(p, pmeta)
            if pmeta.get("required"):
                required.append(p)
        schema: Dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        out["actions"][name] = schema
    return out


def main() -> None:
    schemas = build_json_schemas(ACTION_METADATA)
    target = PROJECT_ROOT / 'mcp-canvas' / 'generated_action_schemas.json'
    target.write_text(json.dumps(schemas, indent=2))
    print(f"Wrote {target}")

if __name__ == "__main__":
    main()
