"""Central action metadata registry for CanvasAgent.

Each action entry specifies:
- name: action key used by dispatcher
- description: brief summary
- params: {param_name: {required: bool, description: str}}
- confirm (optional): bool flag if user confirmation should be requested before execution
"""
from __future__ import annotations
from typing import Dict, Any

ACTION_METADATA: Dict[str, Dict[str, Any]] = {
    "list_courses": {
        "description": "List courses for the authenticated teacher",
        "params": {}
    },
    "get_course_info": {
        "description": "Get high level info for a course",
        "params": {"course_id": {"required": True, "description": "Canvas course numeric ID"}}
    },
    "publish_course": {
        "description": "Publish a course (make it available to students)",
        "params": {"course_id": {"required": True, "description": "Canvas course numeric ID"}},
        "confirm": True
    },
    "unpublish_course": {
        "description": "Unpublish a course (withdraw offering)",
        "params": {"course_id": {"required": True, "description": "Canvas course numeric ID"}},
        "confirm": True
    },
    "list_assignments": {
        "description": "List assignments for a course",
        "params": {"course_id": {"required": True, "description": "Course ID"}}
    },
    "create_assignment": {
        "description": "Create an assignment (also used for lightweight quizzes)",
        "params": {
            "course_id": {"required": True, "description": "Course ID"},
            "name": {"required": True, "description": "Assignment name"},
            "description": {"required": False, "description": "HTML description"},
            "points_possible": {"required": False, "description": "Points (default 100)"},
            "due_at": {"required": False, "description": "ISO8601 due date"}
        }
    },
    "update_assignment": {
        "description": "Update basic assignment fields (name, description, due date)",
        "params": {
            "course_id": {"required": True, "description": "Course ID"},
            "assignment_id": {"required": True, "description": "Assignment ID"},
            "name": {"required": False, "description": "New name"},
            "description": {"required": False, "description": "New description"},
            "due_at": {"required": False, "description": "New due date ISO"}
        }
    },
    "create_quiz": {
        "description": "Create a real (graded) quiz (Classic)",
        "params": {
            "course_id": {"required": True, "description": "Course ID"},
            "name": {"required": True, "description": "Quiz title"},
            "description": {"required": False, "description": "HTML description"},
            "points_possible": {"required": False, "description": "Points (sum of questions)"},
            "due_at": {"required": False, "description": "Due date ISO"},
            "question": {"required": False, "description": "Single question text (auto add)"},
            "answers": {"required": False, "description": "List of answers (first correct if provided)"},
            "rubric_criteria": {"required": False, "description": "List of {description, points}"}
        }
    },
    "create_quiz_question": {
        "description": "Add a question to an existing quiz",
        "params": {
            "course_id": {"required": True, "description": "Course ID"},
            "quiz_id": {"required": True, "description": "Quiz ID"},
            "question": {"required": True, "description": "Question text"},
            "answers": {"required": False, "description": "Answers (first treated correct)"}
        }
    },
    "list_rubrics": {
        "description": "List rubrics for a course",
        "params": {"course_id": {"required": True, "description": "Course ID"}}
    },
    "create_rubric": {
        "description": "Create a rubric with criteria",
        "params": {
            "course_id": {"required": True, "description": "Course ID"},
            "title": {"required": True, "description": "Rubric title"},
            "criteria": {"required": False, "description": "List of {description, points}"}
        }
    },
    "attach_rubric": {
        "description": "Attach existing rubric to an assignment or quiz",
        "params": {
            "course_id": {"required": True, "description": "Course ID"},
            "rubric_id": {"required": True, "description": "Rubric ID"},
            "association_id": {"required": True, "description": "Assignment or Quiz ID"},
            "association_type": {"required": False, "description": "Assignment or Quiz"}
        }
    },
    "list_modules": {
        "description": "List modules in a course",
        "params": {"course_id": {"required": True, "description": "Course ID"}}
    },
    "create_module": {
        "description": "Create a module",
        "params": {"course_id": {"required": True, "description": "Course ID"}, "name": {"required": True, "description": "Module name"}}
    },
    "list_module_items": {
        "description": "List items in a module",
        "params": {
            "course_id": {"required": True, "description": "Course ID"},
            "module_id": {"required": True, "description": "Module ID"}
        }
    },
    "add_module_item": {
        "description": "Add an item (assignment/page/file) to a module",
        "params": {
            "course_id": {"required": True},
            "module_id": {"required": True},
            "title": {"required": True},
            "type": {"required": True},
            "content_id": {"required": False}
        }
    },
    "list_files": {
        "description": "List course files",
        "params": {"course_id": {"required": True}}
    },
    "upload_file": {
        "description": "Upload a local file to the course",
        "params": {
            "course_id": {"required": True},
            "filepath": {"required": True, "description": "Relative or absolute path to file"}
        }
    },
    "list_pages": {
        "description": "List wiki pages",
        "params": {"course_id": {"required": True}}
    },
    "create_page": {
        "description": "Create a wiki page",
        "params": {
            "course_id": {"required": True},
            "title": {"required": True},
            "body": {"required": False}
        }
    },
    "list_announcements": {
        "description": "List announcements",
        "params": {"course_id": {"required": True}}
    },
    "create_announcement": {
        "description": "Create an announcement",
        "params": {
            "course_id": {"required": True},
            "title": {"required": True},
            "message": {"required": True}
        }
    },
    "list_students": {
        "description": "List students enrolled",
        "params": {"course_id": {"required": True}}
    },
    "get_user_profile": {
        "description": "Get profile for current or specified user",
        "params": {"user_id": {"required": False}}
    }
}


def generate_actions_markdown() -> str:
    lines = ["# CanvasAgent Actions", "", "Generated action reference (do not edit manually).", ""]
    for name, meta in sorted(ACTION_METADATA.items()):
        lines.append(f"## {name}\n")
        lines.append(f"{meta.get('description','')}\n")
        params = meta.get('params', {})
        if not params:
            lines.append("_No parameters._\n")
        else:
            lines.append("**Parameters:**\n")
            for p, info in params.items():
                req = info.get('required', False)
                desc = info.get('description','')
                lines.append(f"- `{p}` {'(required)' if req else '(optional)'} - {desc}")
            lines.append("")
        if meta.get('confirm'):
            lines.append("Requires confirmation before execution.\n")
    return "\n".join(lines) + "\n"
