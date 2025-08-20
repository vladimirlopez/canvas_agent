"""Enhanced action dispatcher with Canvas API coverage and LLM integration (refactored)."""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from .canvas_client_enhanced import CanvasClientEnhanced
from .llm_enhanced import ollama_chat_api
import json
import re
from datetime import datetime, timedelta

class CanvasActionDispatcher:
    def __init__(self, client: CanvasClientEnhanced, llm_model: str | None = None):
        self.client = client
        self.llm_model = llm_model
        # Track last created assignment for follow-up commands like "add the quiz to module 1"
        self._last_created_assignment: Dict[str, Any] | None = None
        self.action_registry = {
            'list_courses': self._list_courses,
            'get_course_info': self._get_course_info,
            'publish_course': self._publish_course,
            'unpublish_course': self._unpublish_course,
            'list_assignments': self._list_assignments,
            'create_assignment': self._create_assignment,
            'list_modules': self._list_modules,
            'create_module': self._create_module,
            'list_module_items': self._list_module_items,
            'add_module_item': self._add_module_item,
            'list_files': self._list_files,
            'list_announcements': self._list_announcements,
            'create_announcement': self._create_announcement,
            'list_students': self._list_students,
            'get_user_profile': self._get_user_profile,
        }

    def execute_natural_language_request(self, user_request: str, courses_cache: List[Dict] | None = None) -> str:
        # First attempt a fast deterministic parse for common creation intents (quiz/assignment)
        fast = self._fast_intent_parse(user_request, courses_cache)
        if fast.get('action'):
            action = fast['action']
            try:
                return self.action_registry[action](fast.get('params', {}))
            except Exception as e:  # pragma: no cover
                return f"Error executing {action}: {e}"

        intent_result = self._parse_intent_with_llm(user_request, courses_cache) if courses_cache is not None else {"action": None, "params": {}}
        action = intent_result.get('action')
        if action and action in self.action_registry:
            try:
                return self.action_registry[action](intent_result.get('params', {}))
            except Exception as e:  # pragma: no cover
                return f"Error executing {action}: {e}"
        return self._handle_conversational_request(user_request)

    # --------- Fast Heuristic Parsing (pre-LLM) --------- #
    def _fast_intent_parse(self, text: str, courses_cache: Optional[List[Dict]]) -> Dict[str, Any]:
        """Handle high-friction intents quickly (like user insisting on quiz creation).

        We map 'quiz' to an assignment (since Quizzes API not implemented yet) and embed
        the question into the description. Supports patterns like:
          "create a quiz named 'Quiz 1' with one multiple choice question asking '...'
           and answers are 'Yes' and 'No' worth 10 points due next Friday in course 123"
        """
        lower = text.lower()

        # Heuristic: add last created quiz/assignment to a module
        if ('add' in lower or 'put' in lower) and ('quiz' in lower or 'assignment' in lower) and 'module' in lower and 'to module' in lower:
            mod_match = re.search(r"module\s+(\d+)", lower)
            if mod_match and self._last_created_assignment:
                module_id = mod_match.group(1)
                params = {
                    'course_id': self._last_created_assignment.get('course_id'),
                    'module_id': module_id,
                    'title': self._last_created_assignment.get('name', 'Assignment'),
                    'type': 'Assignment',
                    'content_id': self._last_created_assignment.get('id')
                }
                return {"action": 'add_module_item', 'params': params}

        if 'create' in lower and ('quiz' in lower or 'assignment' in lower):
            # Extract name
            name_match = re.search(r"named\s+'([^']+)'|called\s+'([^']+)'|named\s+([\w \-]+)|called\s+([\w \-]+)", text, re.IGNORECASE)
            name = None
            if name_match:
                for grp in name_match.groups():
                    if grp:
                        name = grp.strip().strip('"')
                        break
            # Pattern: quiz 1 / quiz one
            if not name:
                simple_quiz = re.search(r"quiz\s+([\w\-]+)", lower)
                if simple_quiz:
                    token = simple_quiz.group(1)
                    # Avoid capturing generic words like 'with' or 'for'
                    if token not in {'with','for','about','on','in'}:
                        name = f"Quiz {token.title()}" if not token.lower().startswith('quiz') else token.title()
            # Fallback generic name
            if not name:
                name = 'Untitled Quiz'

            # Extract points
            points = 100
            pts_match = re.search(r"worth\s+(\d+)\s+points", lower)
            if pts_match:
                try:
                    points = int(pts_match.group(1))
                except ValueError:
                    pass

            # Extract question & answers (simple heuristic)
            question_match = re.search(r"question (?:asking|:)?\s*'([^']+)'|question (?:asking|:)?\s*\"([^\"]+)\"", text, re.IGNORECASE)
            question = None
            if question_match:
                question = next((g for g in question_match.groups() if g), None)
            if not question:
                # Another pattern: with one multiple choice question (.*?) and answers are
                q2 = re.search(r"multiple choice question .*?['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
                if q2:
                    question = q2.group(1)
            answers_match = re.search(r"answers? (?:are|:)\s*(['\"]?[^\n]+)", text, re.IGNORECASE)
            answers_raw = None
            if answers_match:
                answers_raw = answers_match.group(1)
            choices: List[str] = []
            if answers_raw:
                # Split on common delimiters
                for token in re.split(r"[,/]|\bor\b|\band\b", answers_raw):
                    t = token.strip().strip("'\"")
                    if t:
                        choices.append(t)
            # Provide a simple description embedding the question
            description_parts = ["Auto-created via CanvasAgent."]
            if question:
                description_parts.append(f"<p><strong>Question:</strong> {question}</p>")
            if choices:
                description_parts.append("<ul>" + "".join(f"<li>{c}</li>" for c in choices) + "</ul>")
            description = "\n".join(description_parts)

            # Extract course id or name
            course_id = self._infer_course_id(text, courses_cache)
            if not course_id:
                return {"action": None, "params": {}}

            # Due date basic parse (supports 'next friday', 'tomorrow')
            due_at_iso = None
            if 'next friday' in lower:
                due_at_iso = self._next_weekday_iso(4)  # 0=Mon ... 4=Fri
            if 'tomorrow' in lower:
                due_at_iso = (datetime.utcnow().date() + timedelta(days=1)).isoformat() + 'T23:59:00Z'
            due_match = re.search(r"due (\d{4}-\d{2}-\d{2})", lower)
            if due_match:
                due_at_iso = due_match.group(1) + "T23:59:00Z"

            params = {
                'course_id': course_id,
                'name': name,
                'description': description,
                'points_possible': points,
            }
            if due_at_iso:
                params['due_at'] = due_at_iso
            return {"action": 'create_assignment', 'params': params}
        return {"action": None, "params": {}}

    def _infer_course_id(self, text: str, courses_cache: Optional[List[Dict]]) -> Optional[str]:
        if not courses_cache:
            return None
        # Look for explicit numeric id
        id_match = re.search(r"course\s+(\d+)", text, re.IGNORECASE)
        if id_match:
            return id_match.group(1)
        # Match by name fragment
        lower = text.lower()
        for c in courses_cache:
            name = str(c.get('name',''))
            if name and name.lower() in lower:
                return str(c.get('id'))
            # Also match camel-case break or code
            code = str(c.get('course_code',''))
            if code and code.lower() in lower:
                return str(c.get('id'))
        # If only one course, assume it
        if len(courses_cache) == 1:
            return str(courses_cache[0].get('id'))
        return None

    def _next_weekday_iso(self, target_weekday: int) -> str:
        today = datetime.utcnow().date()
        days_ahead = (target_weekday - today.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        due_date = today + timedelta(days=days_ahead)
        # Set default due time to 23:59 UTC
        return due_date.isoformat() + 'T23:59:00Z'

    def _parse_intent_with_llm(self, user_request: str, courses_cache: List[Dict] | None) -> Dict[str, Any]:
        if not self.llm_model:
            return {"action": None, "params": {}}
        course_context = ""
        if courses_cache:
            course_context = "Available courses:\n" + "\n".join([f"- {c.get('id')}: {c.get('name')}" for c in courses_cache[:10]])
        system_prompt = f"""You are a Canvas LMS action parser. Parse the user's request and return JSON with action and parameters.
If the user says 'quiz' you should normally map it to create_assignment (we are using assignments as lightweight quizzes unless explicitly given a real quiz API context). Extract name, points, and if they supply a simple multiple choice question with answers, put it in the description HTML list.
Available actions and required parameters:
- list_courses: {{}}
- get_course_info: {{"course_id": "123"}}
- list_assignments: {{"course_id": "123"}}
- create_assignment: {{"course_id": "123", "name": "Assignment Name", "description": "...", "points_possible": 100}}
- list_modules: {{"course_id": "123"}}
- create_module: {{"course_id": "123", "name": "Module Name"}}
- list_module_items: {{"course_id": "123", "module_id": "456"}}
- add_module_item: {{"course_id": "123", "module_id": "456", "title": "Item Title", "type": "Page|Assignment|File|ExternalUrl", "content_id": "optional"}}
- list_files: {{"course_id": "123"}}
- download_file: {{"file_id": "456", "dest_path": "optional"}}
- list_announcements: {{"course_id": "123"}}
- create_announcement: {{"course_id": "123", "title": "Title", "message": "Content"}}
- list_students: {{"course_id": "123"}}
- get_user_profile: {{}}
{course_context}
Return only valid JSON in format: {{"action": "action_name", "params": {{...}}}}
If unclear, return {{"action": null, "params": {{}}}}."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_request},
            ]
            response = ollama_chat_api(self.llm_model, messages)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            return {"action": None, "params": {}}
        return {"action": None, "params": {}}

    def _handle_conversational_request(self, user_request: str) -> str:
        if not self.llm_model:
            return ("I can help with Canvas actions like listing courses, creating modules, managing files, etc. "
                    "Please be more specific.")
        system_prompt = ("You are a helpful Canvas LMS assistant. The user's request doesn't map to a specific action. "
                         "Provide helpful guidance about available actions or ask clarifying questions.")
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_request},
            ]
            return ollama_chat_api(self.llm_model, messages)
        except Exception as e:
            return f"Sorry, I encountered an error: {e}"

    # Action implementations (subset retained)
    def _list_courses(self, params: Dict[str, Any]) -> str:
        courses = self.client.list_courses()
        if not courses:
            return "No courses found."
        lines = [f"**{c.get('name')}** (ID: {c.get('id')})" for c in courses]
        return "**Your Courses:**\n" + "\n".join(lines)

    def _get_course_info(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID."
        course = self.client.get_course(course_id)
        return (f"**{course.get('name')}**\nCode: {course.get('course_code')}\nTerm: "
                f"{course.get('term', {}).get('name')}\nStudents: {course.get('total_students', 'N/A')}")

    def _list_assignments(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID."
        assignments = self.client.list_assignments(course_id, include=['submission_summary'])
        if not assignments:
            return f"No assignments found for course {course_id}."
        lines = [f"**{a.get('name')}** (ID: {a.get('id')}) - {a.get('points_possible', 0)} pts" for a in assignments]
        return f"**Assignments for Course {course_id}:**\n" + "\n".join(lines)

    def _create_assignment(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        name = params.get('name')
        if not course_id or not name:
            return "Please provide course_id and assignment name."
        assignment_data = {
            'assignment[name]': name,
            'assignment[description]': params.get('description', ''),
            'assignment[points_possible]': params.get('points_possible', 100),
            'assignment[published]': True,
        }
        if params.get('due_at'):
            assignment_data['assignment[due_at]'] = params['due_at']
        result = self.client.create_assignment(course_id, assignment_data)
        # Track last created assignment for follow-up actions
        self._last_created_assignment = {
            'id': result.get('id'),
            'course_id': course_id,
            'name': result.get('name')
        }
        return f"Created assignment: **{result.get('name')}** (ID: {result.get('id')})"

    def _list_modules(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID."
        modules = self.client.list_modules(course_id)
        if not modules:
            return f"No modules found for course {course_id}."
        lines = [f"**{m.get('name')}** (ID: {m.get('id')}) - {m.get('items_count', 0)} items" for m in modules]
        return f"**Modules for Course {course_id}:**\n" + "\n".join(lines)

    def _create_module(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        name = params.get('name')
        if not course_id or not name:
            return "Please provide course_id and module name."
        result = self.client.create_module(course_id, name)
        return f"Created module: **{result.get('name')}** (ID: {result.get('id')})"

    def _list_module_items(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        module_id = params.get('module_id')
        if not course_id or not module_id:
            return "Please provide course_id and module_id."
        items = self.client.list_module_items(course_id, module_id)
        if not items:
            return f"No items found in module {module_id}."
        lines = [f"**{item.get('title')}** ({item.get('type')})" for item in items]
        return f"**Items in Module {module_id}:**\n" + "\n".join(lines)

    def _add_module_item(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        module_id = params.get('module_id')
        title = params.get('title')
        item_type = params.get('type', 'Assignment')
        content_id = params.get('content_id')
        if not all([course_id, module_id, title, item_type]):
            return "Please provide course_id, module_id, title, and type."
        data: Dict[str, Any] = {
            'module_item[type]': item_type,
            'module_item[title]': title,
        }
        if content_id:
            data['module_item[content_id]'] = content_id
        try:
            result = self.client.create_module_item(course_id, module_id, data)
            return f"Added module item: **{result.get('title', title)}** to module {module_id}"
        except Exception as e:
            return f"Failed to add module item: {e}"

    def _list_files(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID."
        files = self.client.list_files(course_id)
        if not files:
            return f"No files found for course {course_id}."
        lines = [f"**{f.get('filename')}** (ID: {f.get('id')}) - {f.get('size', 0)} bytes" for f in files[:20]]
        return f"**Files for Course {course_id}:**\n" + "\n".join(lines)

    def _list_announcements(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID."
        announcements = self.client.list_announcements(course_id)
        if not announcements:
            return f"No announcements found for course {course_id}."
        lines = [f"**{a.get('title')}** - {a.get('posted_at', 'No date')}" for a in announcements[:10]]
        return f"**Announcements for Course {course_id}:**\n" + "\n".join(lines)

    def _create_announcement(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        title = params.get('title')
        message = params.get('message')
        if not all([course_id, title, message]):
            return "Please provide course_id, title, and message."
        result = self.client.create_announcement(course_id, title, message)
        return f"Created announcement: **{result.get('title')}**"

    def _list_students(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID."
        students = self.client.list_students(course_id)
        if not students:
            return f"No students found for course {course_id}."
        lines = [f"**{s.get('user', {}).get('name')}** (ID: {s.get('user_id')})" for s in students[:20]]
        return f"**Students in Course {course_id}:**\n" + "\n".join(lines)

    def _get_user_profile(self, params: Dict[str, Any]) -> str:
        user_id = params.get('user_id', 'self')
        profile = self.client.get_user_profile(user_id)
        return f"**{profile.get('name')}**\nEmail: {profile.get('primary_email')}\nRole: {profile.get('bio', 'N/A')}"

    def _publish_course(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID to publish."
        try:
            result = self.client.publish_course(course_id)
            return f"✅ Successfully published course: **{result.get('name', 'Unknown Course')}** (ID: {course_id})"
        except Exception as e:
            return f"❌ Failed to publish course {course_id}: {e}"

    def _unpublish_course(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID to unpublish."
        try:
            result = self.client.unpublish_course(course_id)
            return f"✅ Successfully unpublished course: **{result.get('name', 'Unknown Course')}** (ID: {course_id})"
        except Exception as e:
            return f"❌ Failed to unpublish course {course_id}: {e}"
