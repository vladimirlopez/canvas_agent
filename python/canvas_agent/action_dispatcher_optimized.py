"""Optimized action dispatcher with improved performance and error handling."""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from functools import lru_cache
import json
import re
from datetime import datetime, timedelta, timezone

from .canvas_client_enhanced import CanvasClientEnhanced
from .llm_enhanced import ollama_chat_api
from .action_metadata import ACTION_METADATA

class CanvasActionDispatcher:
    """Enhanced Canvas action dispatcher with caching and validation."""
    
    def __init__(self, client: CanvasClientEnhanced, llm_model: str | None = None):
        self.client = client
        self.llm_model = llm_model
        self._last_created_assignment: Optional[Dict[str, Any]] = None
        self._course_cache: Optional[List[Dict]] = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes
        
        # Pre-compile regex patterns for better performance
        self._patterns = self._compile_patterns()
        
        # Action registry with optimized lookups
        self.action_registry = self._build_action_registry()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Pre-compile regex patterns for performance."""
        return {
            'course_id': re.compile(r'\bcourse\s+(\d+)\b', re.IGNORECASE),
            'points': re.compile(r'\b(\d+)\s*points?\b', re.IGNORECASE),
            'due_tomorrow': re.compile(r'\b(due\s+)?tomorrow\b', re.IGNORECASE),
            'due_next_week': re.compile(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.IGNORECASE),
            'quiz_indicator': re.compile(r'\b(quiz|test|exam)\b', re.IGNORECASE),
            'assignment_indicator': re.compile(r'\b(assignment|homework|hw)\b', re.IGNORECASE),
        }
    
    def _build_action_registry(self) -> Dict[str, callable]:
        """Build optimized action registry."""
        return {
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
    
    @lru_cache(maxsize=128)
    def _parse_due_date_cached(self, due_phrase: str) -> Optional[str]:
        """Cached version of due date parsing."""
        return self._parse_due_date(due_phrase)
    
    def _get_courses_cached(self) -> List[Dict]:
        """Get courses with caching."""
        now = datetime.now().timestamp()
        if self._course_cache is None or (now - self._cache_timestamp) > self._cache_ttl:
            self._course_cache = self.client.list_courses()
            self._cache_timestamp = now
        return self._course_cache
    
    def execute_natural_language_request(self, user_request: str, courses_cache: Optional[List[Dict]] = None) -> str:
        """Execute request with optimized parsing."""
        try:
            # Use cached courses if not provided
            if courses_cache is None:
                courses_cache = self._get_courses_cached()
            
            # Fast intent parsing first
            fast_result = self._fast_intent_parse_optimized(user_request, courses_cache)
            
            if fast_result.get('action'):
                action = fast_result['action']
                params = fast_result.get('params', {})
                
                # Validate inputs
                validation_error = self._validate_action_inputs(action, params)
                if validation_error:
                    return validation_error
                
                # Execute action
                result = self._execute_action(action, params)
                return self._format_result(result, action)
            
            # Fallback to LLM if fast parsing fails
            return self._llm_fallback(user_request, courses_cache)
            
        except Exception as e:
            return f"Error processing request: {str(e)}"
    
    def _fast_intent_parse_optimized(self, request: str, courses_cache: List[Dict]) -> Dict[str, Any]:
        """Optimized fast intent parsing with pre-compiled patterns."""
        request_lower = request.lower()
        
        # Check for creation intents
        if 'create' in request_lower or 'make' in request_lower or 'add' in request_lower:
            
            # Quiz/Assignment detection
            if self._patterns['quiz_indicator'].search(request):
                return self._parse_quiz_creation(request, courses_cache)
            elif self._patterns['assignment_indicator'].search(request):
                return self._parse_assignment_creation(request, courses_cache)
            elif 'page' in request_lower:
                return self._parse_page_creation(request, courses_cache)
            elif 'module' in request_lower:
                return self._parse_module_creation(request, courses_cache)
        
        # List operations
        if 'list' in request_lower or 'show' in request_lower:
            return self._parse_list_operation(request, courses_cache)
        
        return {}
    
    def _parse_quiz_creation(self, request: str, courses_cache: List[Dict]) -> Dict[str, Any]:
        """Parse quiz creation with optimized pattern matching."""
        # Extract course ID
        course_match = self._patterns['course_id'].search(request)
        if not course_match:
            return {}
        
        course_id = int(course_match.group(1))
        
        # Extract points
        points_match = self._patterns['points'].search(request)
        points = int(points_match.group(1)) if points_match else 10
        
        # Extract title (simplified)
        title_pattern = re.compile(r'(?:quiz|test|exam)\s+(?:about\s+|on\s+)?["\']?([^"\'.\n]+)["\']?', re.IGNORECASE)
        title_match = title_pattern.search(request)
        title = title_match.group(1).strip() if title_match else "Quiz"
        
        # Parse due date
        due_at = None
        if self._patterns['due_tomorrow'].search(request):
            due_at = self._parse_due_date_cached("tomorrow")
        elif self._patterns['due_next_week'].search(request):
            day_match = self._patterns['due_next_week'].search(request)
            if day_match:
                due_at = self._parse_due_date_cached(f"next {day_match.group(1)}")
        
        return {
            'action': 'create_quiz',
            'params': {
                'course_id': course_id,
                'name': title,
                'points_possible': points,
                'due_at': due_at
            }
        }
    
    def _execute_action(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute action with error handling."""
        handler = self.action_registry.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
        
        return handler(**params)
    
    def _format_result(self, result: Any, action: str) -> str:
        """Format action result for user display."""
        if isinstance(result, dict):
            if 'id' in result and 'name' in result:
                return f"✅ Created {result['name']} (ID: {result['id']})"
            elif 'id' in result:
                return f"✅ {action} completed (ID: {result['id']})"
        elif isinstance(result, list):
            return f"✅ Found {len(result)} items"
        
        return f"✅ {action} completed successfully"
    
    # Rest of the methods would be optimized versions of the existing ones...
    # [Previous method implementations would go here, but optimized]
