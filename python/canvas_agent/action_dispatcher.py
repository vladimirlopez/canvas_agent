"""Enhanced action dispatcher with Canvas API coverage and LLM integration (refactored)."""
from __future__ import annotations
from typing import Dict, Any, List
from .canvas_client_enhanced import CanvasClientEnhanced
from .llm_enhanced import ollama_chat_api
import json
import re

class CanvasActionDispatcher:
    def __init__(self, client: CanvasClientEnhanced, llm_model: str | None = None):
        self.client = client
        self.llm_model = llm_model
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
        intent_result = self._parse_intent_with_llm(user_request, courses_cache) if courses_cache is not None else {"action": None, "params": {}}
        action = intent_result.get('action')
        if action and action in self.action_registry:
            try:
                return self.action_registry[action](intent_result.get('params', {}))
            except Exception as e:  # pragma: no cover
                return f"Error executing {action}: {e}"
        return self._handle_conversational_request(user_request)

    def _parse_intent_with_llm(self, user_request: str, courses_cache: List[Dict] | None) -> Dict[str, Any]:
        if not self.llm_model:
            return {"action": None, "params": {}}
        course_context = ""
        if courses_cache:
            course_context = "Available courses:\n" + "\n".join([f"- {c.get('id')}: {c.get('name')}" for c in courses_cache[:10]])
        system_prompt = f"""You are a Canvas LMS action parser. Parse the user's request and return JSON with action and parameters.
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
        result = self.client.create_assignment(course_id, assignment_data)
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
        return "Add module item not implemented in refactored subset"

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
