from typing import Dict, Any
from canvas_client import CanvasClient

# Simple intent matching (very naive). In production use proper NLP or function calling.

def list_courses_action(client: CanvasClient, params: Dict[str, Any]):
    courses = client.list_courses()
    lines = [f"{c.get('id')}: {c.get('name')}" for c in courses]
    return "Courses:\n" + "\n".join(lines)


def list_assignments_action(client: CanvasClient, params: Dict[str, Any]):
    course_id = params.get('course_id')
    if not course_id:
        return 'Please specify a course_id.'
    assignments = client.list_assignments(course_id)
    lines = [f"{a.get('id')}: {a.get('name')} (due: {a.get('due_at')})" for a in assignments]
    return f"Assignments for course {course_id}:\n" + "\n".join(lines)


def list_files_action(client: CanvasClient, params: Dict[str, Any]):
    course_id = params.get('course_id')
    if not course_id:
        return 'Please specify a course_id.'
    files = client.list_files(course_id)
    lines = [f"{f.get('id')}: {f.get('filename')} ({f.get('size')} bytes)" for f in files]
    return f"Files for course {course_id}:\n" + "\n".join(lines)


def download_file_action(client: CanvasClient, params: Dict[str, Any]):
    file_id = params.get('file_id')
    dest = params.get('dest', f'downloads/{file_id}')
    if not file_id:
        return 'Please specify a file_id.'
    path = client.download_file(file_id, dest)
    return f"Downloaded file to {path}"


def upload_file_action(client: CanvasClient, params: Dict[str, Any]):
    course_id = params.get('course_id')
    filepath = params.get('filepath')
    if not course_id or not filepath:
        return 'Please specify course_id and filepath.'
    resp = client.upload_file_to_course(course_id, filepath)
    return f"Uploaded: {resp}"


def list_modules_action(client: CanvasClient, params: Dict[str, Any]):
    course_id = params.get('course_id')
    if not course_id:
        return 'Please specify a course_id.'
    modules = client.list_modules(course_id)
    if not modules:
        return f"No modules found for course {course_id}."
    lines = [f"{m.get('id')}: {m.get('name')} (items: {m.get('items_count')})" for m in modules]
    return f"Modules for course {course_id}:\n" + "\n".join(lines)


def create_module_action(client: CanvasClient, params: Dict[str, Any]):
    course_id = params.get('course_id')
    name = params.get('name')
    if not course_id or not name:
        return 'Usage: create module <course_id> <module name>'
    resp = client.create_module(course_id, name)
    return f"Created module: {resp.get('id')} - {resp.get('name')}"

ACTIONS = {
    'list courses': list_courses_action,
    'list assignments': list_assignments_action,
    'list files': list_files_action,
    'download file': download_file_action,
    'upload file': upload_file_action,
    'list modules': list_modules_action,
    'create module': create_module_action,
}


def dispatch_action(client: CanvasClient, user_text: str):
    lower = user_text.lower()
    for key, fn in ACTIONS.items():
        if lower.startswith(key):
            parts = user_text.split()
            params: Dict[str, Any] = {}
            if key == 'list assignments' and len(parts) >= 3:
                params['course_id'] = parts[2]
            elif key == 'list files' and len(parts) >= 3:
                params['course_id'] = parts[2]
            elif key == 'download file' and len(parts) >= 3:
                params['file_id'] = parts[2]
            elif key == 'upload file' and len(parts) >= 4:
                params['course_id'] = parts[2]
                params['filepath'] = parts[3]
            elif key == 'list modules' and len(parts) >= 3:
                params['course_id'] = parts[2]
            elif key == 'create module' and len(parts) >= 4:
                params['course_id'] = parts[2]
                params['name'] = " ".join(parts[3:])
            return fn(client, params)
    return None


def perform_action(client: CanvasClient, action_name: str, params: Dict[str, Any]):
    """Perform an action by canonical name (case-insensitive).

    Returns result string or error message.
    """
    key = action_name.lower().strip()
    fn = ACTIONS.get(key)
    if not fn:
        return f"Unknown action '{action_name}'."
    try:
        return fn(client, params)
    except Exception as e:
        return f"Action '{action_name}' failed: {e}"
