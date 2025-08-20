"""Enhanced action dispatcher with Canvas API coverage and LLM integration (refactored)."""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from .canvas_client_enhanced import CanvasClientEnhanced
from .llm_enhanced import ollama_chat_api
import json
import re
from datetime import datetime, timedelta, timezone
from .action_metadata import ACTION_METADATA

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
            'update_assignment': self._update_assignment,
            'create_quiz': self._create_quiz,
            'create_quiz_question': self._create_quiz_question,
            'list_rubrics': self._list_rubrics,
            'create_rubric': self._create_rubric,
            'attach_rubric': self._attach_rubric,
            'list_modules': self._list_modules,
            'create_module': self._create_module,
            'list_module_items': self._list_module_items,
            'add_module_item': self._add_module_item,
            'list_files': self._list_files,
            'upload_file': self._upload_file,
            'list_pages': self._list_pages,
            'create_page': self._create_page,
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
                params = fast.get('params', {})
                validation_error = self._validate_action_inputs(action, params)
                if validation_error:
                    return validation_error
                return self.action_registry[action](params)
            except Exception as e:  # pragma: no cover
                return f"Error executing {action}: {e}"

        intent_result = self._parse_intent_with_llm(user_request, courses_cache) if courses_cache is not None else {"action": None, "params": {}}
        action = intent_result.get('action')
        if action and action in self.action_registry:
            try:
                params = intent_result.get('params', {})
                validation_error = self._validate_action_inputs(action, params)
                if validation_error:
                    return validation_error
                return self.action_registry[action](params)
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

        # Page creation heuristic
        if 'create' in lower and 'page' in lower:
            # Title extraction
            title_match = re.search(r"page (?:titled|called|named) '([^']+)'|page (?:titled|called|named) \"([^\"]+)\"", text, re.IGNORECASE)
            title = None
            if title_match:
                title = next((g for g in title_match.groups() if g), None)
            if not title:
                # Fallback: "create a page X" capturing next few words until stop words
                simple_title = re.search(r"create (?:a |one )?page ([a-zA-Z0-9 \-]{3,60})", lower)
                if simple_title:
                    cand = simple_title.group(1).strip()
                    cand = re.split(r" about | with | for | in course | on ", cand)[0]
                    title = cand.title()
            # Body content from 'about <topic>' or 'with content <...>'
            body = "<p>Created via CanvasAgent.</p>"
            about_match = re.search(r"about ([a-zA-Z0-9 ,.-]{3,120})", text, re.IGNORECASE)
            if about_match:
                topic = about_match.group(1).strip().rstrip('.')
                body += f"<p>{topic}</p>"
            content_match = re.search(r"with content ['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
            if content_match:
                body += f"<p>{content_match.group(1)}</p>"
            course_id = self._infer_course_id(text, courses_cache)
            if not course_id:
                return {"action": None, "params": {}}
            if not title:
                title = "New Page"
            return {"action": 'create_page', 'params': {'course_id': course_id, 'title': title, 'body': body}}

        # File upload heuristic
        if ('upload' in lower or 'add' in lower) and 'file' in lower:
            # Look for explicit filename (common extensions)
            file_match = re.search(r"file ([\w\-.]+\.(?:pdf|docx?|pptx?|xlsx?|csv|txt|md|png|jpg|jpeg))", lower)
            if file_match:
                filename = file_match.group(1)
                course_id = self._infer_course_id(text, courses_cache)
                if not course_id:
                    return {"action": None, "params": {}}
                return {"action": 'upload_file', 'params': {'course_id': course_id, 'filepath': filename}}

        if 'update' in lower and 'assignment' in lower:
            # Update assignment (due date or description)
            assign_id_match = re.search(r"assignment (\d+)", lower)
            if assign_id_match:
                assignment_id = assign_id_match.group(1)
                course_id = self._infer_course_id(text, courses_cache)
                if not course_id:
                    return {"action": None, "params": {}}
                due_at = self._parse_due_date(text)
                desc_match = re.search(r"description to ['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
                update: Dict[str, Any] = {'course_id': course_id, 'assignment_id': assignment_id}
                if due_at:
                    update['due_at'] = due_at
                if desc_match:
                    update['description'] = desc_match.group(1)
                if len(update) > 2:
                    return {"action": 'update_assignment', 'params': update}

        # Real quiz creation (Phase 2): detect explicit "real quiz" or "graded quiz"
        if 'create' in lower and 'quiz' in lower and ('real' in lower or 'graded' in lower):
            course_id = self._infer_course_id(text, courses_cache)
            if not course_id:
                return {"action": None, "params": {}}
            name_match = re.search(r"quiz (?:named|titled|called) ['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
            name = name_match.group(1) if name_match else 'New Quiz'
            points = 0
            pts = re.search(r"worth (\d+) points", lower)
            if pts:
                points = int(pts.group(1))
            due_at = self._parse_due_date(text)
            desc = ''
            about = re.search(r"about ([a-zA-Z0-9 ,.-]{3,120})", text, re.IGNORECASE)
            if about:
                desc = f"<p>Quiz about {about.group(1).strip()}</p>"
            # Extract optional single question and answers
            q_match = re.search(r"question ['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
            question = q_match.group(1).strip() if q_match else None
            answers: List[str] = []
            ans_match = re.search(r"answers? (?:are|:)?\s*([^\n]+)", text, re.IGNORECASE)
            if ans_match:
                raw = ans_match.group(1)
                raw = re.split(r"\s+rubric\b|\s+with criteria\b", raw)[0]
                for token in re.split(r"[,/]|\bor\b|\band\b", raw):
                    t = token.strip().strip("'\"")
                    if t:
                        answers.append(t)
            # Rubric criteria parsing: rubric with criteria Clarity 5, Accuracy 5
            rubric_criteria: List[Dict[str, Any]] = []
            rub_block = re.search(r"rubric with criteria (.+)", lower)
            if rub_block:
                crit_text = rub_block.group(1)
                for piece in re.split(r"[,;]", crit_text):
                    m = re.search(r"([a-zA-Z0-9 \-]{2,60})\s+(\d+)", piece.strip())
                    if m:
                        rubric_criteria.append({'description': m.group(1).strip().title(), 'points': int(m.group(2))})
            params = {'course_id': course_id, 'name': name, 'description': desc, 'points_possible': points}
            if due_at:
                params['due_at'] = due_at
            if question:
                params['question'] = question
            if answers:
                params['answers'] = answers
            if rubric_criteria:
                params['rubric_criteria'] = rubric_criteria
            return {"action": 'create_quiz', 'params': params}

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
            # Topic-only phrasing: "quiz for tomorrow about inertia ..."
            if not question:
                about_match = re.search(r"about\s+([a-zA-Z0-9 \-]+?)(?:\s+with|\s+worth|\s+answers|$)", text, re.IGNORECASE)
                if about_match:
                    topic = about_match.group(1).strip().strip('.').title()
                    question = f"Quick check on {topic}"  # Placeholder question derived from topic
                    # If name is still generic, improve it using topic
                    if name == 'Untitled Quiz':
                        name = f"Quiz {topic}"[:60]
            answers_match = re.search(r"answers? (?:are|:)\s*(['\"]?[^\n]+)", text, re.IGNORECASE)
            answers_raw = None
            if answers_match:
                answers_raw = answers_match.group(1)
            if not answers_raw:
                # Support pattern without 'are' or ':' e.g. "answers yes,no" or "answers yes, no"
                answers_simple = re.search(r"answers\s+([^\n]+)", text, re.IGNORECASE)
                if answers_simple:
                    # Stop at common trailing words
                    temp = answers_simple.group(1)
                    temp = re.split(r"\s+due\b|\s+worth\b|\s+points?\b", temp)[0]
                    answers_raw = temp.strip()
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

            # Due date advanced parse
            due_at_iso = self._parse_due_date(text)

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

    def _parse_due_date(self, text: str) -> Optional[str]:
        """Parse a variety of simple natural language due date expressions.

        Supported examples:
          - next friday
          - tomorrow
          - in 2 days / in 3 weeks
          - due 2025-09-05
          - next monday 5pm
          - in 10 days at 4pm
        Returns ISO8601 UTC with fallback time 23:59Z if time omitted.
        """
        lower = text.lower()
        # Explicit date
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", lower)
        base_date: Optional[datetime] = None
        if date_match:
            try:
                base_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
            except ValueError:
                pass
        # relative 'tomorrow'
        if 'tomorrow' in lower:
            base_date = datetime.now(timezone.utc) + timedelta(days=1)
        # next weekday
        weekdays = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
        for idx, wd in enumerate(weekdays):
            if f"next {wd}" in lower:
                base_date = datetime.now(timezone.utc)
                days_ahead = (idx - base_date.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                base_date = base_date + timedelta(days=days_ahead)
                break
        # in N days/weeks
        rel_match = re.search(r"in (\d+) (day|days|week|weeks)", lower)
        if rel_match:
            qty = int(rel_match.group(1))
            unit = rel_match.group(2)
            delta_days = qty * (7 if unit.startswith('week') else 1)
            base_date = datetime.now(timezone.utc) + timedelta(days=delta_days)
        if not base_date:
            return None
        # time component
        time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lower)
        hour = 23
        minute = 59
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3)
            if ampm:
                if ampm == 'pm' and hour < 12:
                    hour += 12
                if ampm == 'am' and hour == 12:
                    hour = 0
            # Basic sanity
            if hour > 23:
                hour = 23
            if minute > 59:
                minute = 59
        dt = datetime(base_date.year, base_date.month, base_date.day, hour, minute, tzinfo=timezone.utc)
        return dt.strftime('%Y-%m-%dT%H:%M:00Z')

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
        today = datetime.now(timezone.utc).date()
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

    # --------- Validation --------- #
    def _validate_action_inputs(self, action: str, params: Dict[str, Any]) -> Optional[str]:
        meta = ACTION_METADATA.get(action)
        if not meta:
            return None
        missing = []
        for p, info in meta.get('params', {}).items():
            if info.get('required') and (p not in params or params.get(p) in (None, '')):
                missing.append(p)
        if missing:
            return f"Missing required parameters for {action}: {', '.join(missing)}"
        # Confirmation stub (future interactive flow)
        if meta.get('confirm'):
            # In a future interactive version, we'd return a prompt asking for confirmation.
            pass
        return None

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

    def _update_assignment(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        assignment_id = params.get('assignment_id')
        if not course_id or not assignment_id:
            return "Please provide course_id and assignment_id."
        data: Dict[str, Any] = {}
        if 'name' in params:
            data['assignment[name]'] = params['name']
        if 'description' in params:
            data['assignment[description]'] = params['description']
        if 'due_at' in params:
            data['assignment[due_at]'] = params['due_at']
        if not data:
            return "No updatable fields provided."
        result = self.client.update_assignment(course_id, assignment_id, data)
        return f"Updated assignment {assignment_id}: **{result.get('name','(name)')}**"

    def _create_quiz(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        name = params.get('name')
        if not course_id or not name:
            return "Please provide course_id and quiz name."
        quiz_data = {
            'quiz[title]': name,
            'quiz[description]': params.get('description',''),
            'quiz[quiz_type]': 'assignment',  # graded quiz
            'quiz[points_possible]': params.get('points_possible', 0),
            'quiz[published]': True,
        }
        if params.get('due_at'):
            quiz_data['quiz[due_at]'] = params['due_at']
        result = self.client.create_quiz(course_id, quiz_data)
        output = [f"Created quiz: **{result.get('title', name)}** (ID: {result.get('id')})"]
        # Auto add question if provided
        if 'question' in params:
            q_payload = self._build_question_payload({
                'name': 'Auto Question',
                'question': params['question'],
                'answers': params.get('answers', []),
                'points': params.get('points_possible', 1)
            })
            try:
                q_res = self.client.create_quiz_question(course_id, str(result.get('id')), q_payload)
                output.append(f"Added quiz question (ID: {q_res.get('id')})")
            except Exception as e:  # pragma: no cover
                output.append(f"Failed to add question: {e}")
        # Auto create rubric if criteria present
        if params.get('rubric_criteria'):
            try:
                rubric_data: Dict[str, Any] = {
                    'rubric[title]': f"Rubric for {name}",
                    'rubric[free_form_criterion_comments]': 'true'
                }
                for idx, c in enumerate(params['rubric_criteria']):
                    rubric_data[f'rubric[criteria][{idx}][description]'] = c['description']
                    rubric_data[f'rubric[criteria][{idx}][points]'] = c['points']
                rub = self.client.create_rubric(course_id, rubric_data)
                try:
                    self.client.attach_rubric(course_id, str(rub.get('id')), str(result.get('id')), association_type='Quiz')
                    output.append(f"Created and attached rubric (ID: {rub.get('id')})")
                except Exception as e:  # pragma: no cover
                    output.append(f"Rubric attach failed: {e}")
            except Exception as e:  # pragma: no cover
                output.append(f"Rubric creation failed: {e}")
        return " \n".join(output)

    def _build_question_payload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        answers: List[str] = params.get('answers', [])
        question_data: Dict[str, Any] = {
            'question[question_name]': params.get('name','Question'),
            'question[question_text]': params.get('question'),
            'question[points_possible]': params.get('points', 1),
            'question[question_type]': 'multiple_choice_question' if answers else 'short_answer_question'
        }
        if answers:
            for idx, ans in enumerate(answers):
                question_data[f'question[answers][{idx}][text]'] = ans
                question_data[f'question[answers][{idx}][weight]'] = 100 if idx == 0 else 0
        return question_data

    def _create_quiz_question(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        quiz_id = params.get('quiz_id')
        question_text = params.get('question')
        if not all([course_id, quiz_id, question_text]):
            return "Please provide course_id, quiz_id, and question text."
        result = self.client.create_quiz_question(course_id, quiz_id, self._build_question_payload(params))
        return f"Added quiz question (ID: {result.get('id')})"

    def _list_rubrics(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID."
        rubrics = self.client.list_rubrics(course_id)
        if not rubrics:
            return f"No rubrics found for course {course_id}."
        lines = [f"**{r.get('title','(no title)')}** (ID: {r.get('id')})" for r in rubrics[:20]]
        return f"**Rubrics for Course {course_id}:**\n" + "\n".join(lines)

    def _create_rubric(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        title = params.get('title')
        if not course_id or not title:
            return "Please provide course_id and title."
        criteria: List[Dict[str, Any]] = params.get('criteria', [])
        rubric_data: Dict[str, Any] = {
            'rubric[title]': title,
            'rubric[free_form_criterion_comments]': 'true'
        }
        for idx, c in enumerate(criteria):
            rubric_data[f'rubric[criteria][{idx}][description]'] = c.get('description','Criterion')
            rubric_data[f'rubric[criteria][{idx}][points]'] = c.get('points', 1)
        result = self.client.create_rubric(course_id, rubric_data)
        return f"Created rubric: **{result.get('title', title)}** (ID: {result.get('id')})"

    def _attach_rubric(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        rubric_id = params.get('rubric_id')
        association_id = params.get('association_id')
        association_type = params.get('association_type','Assignment')
        if not all([course_id, rubric_id, association_id]):
            return "Please provide course_id, rubric_id, and association_id."
        result = self.client.attach_rubric(course_id, rubric_id, association_id, association_type)
        return f"Attached rubric {rubric_id} to {association_type} {association_id} (ID: {result.get('id','?')})"

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

    def _upload_file(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        filepath = params.get('filepath')
        if not course_id or not filepath:
            return "Please provide course_id and filepath (local filename)."
        try:
            result = self.client.upload_file(course_id, filepath)
            return f"Uploaded file: **{result.get('display_name', result.get('filename', filepath))}** (ID: {result.get('id')})"
        except Exception as e:
            return f"Failed to upload file: {e}"

    def _list_pages(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        if not course_id:
            return "Please provide a course ID."
        pages = self.client.list_pages(course_id)
        if not pages:
            return f"No pages found for course {course_id}."
        lines = [f"**{p.get('title')}** (URL: {p.get('url')})" for p in pages[:20]]
        return f"**Pages for Course {course_id}:**\n" + "\n".join(lines)

    def _create_page(self, params: Dict[str, Any]) -> str:
        course_id = params.get('course_id')
        title = params.get('title')
        body = params.get('body','')
        if not course_id or not title:
            return "Please provide course_id and title."
        result = self.client.create_page(course_id, title, body)
        return f"Created page: **{result.get('title', title)}**"

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
