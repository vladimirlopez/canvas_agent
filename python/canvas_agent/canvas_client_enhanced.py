"""Enhanced Canvas client with error handling, caching, and better API coverage.

This file relocated into the python/canvas_agent package during refactor.
"""
from __future__ import annotations
import requests
import time
from typing import Optional, Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CanvasClientEnhanced:
    def __init__(self, base_url: str, api_token: str, cache_ttl: int = 300):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'User-Agent': 'CanvasAgent/1.0'
        })
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = cache_ttl

    def _get_cache_key(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        key = f"GET:{path}"
        if params:
            key += f":{hash(str(sorted(params.items())))}"
        return key

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self.cache:
            return False
        return time.time() - self.cache[key]['timestamp'] < self.cache_ttl

    def _cache_response(self, key: str, data: Any) -> None:
        self.cache[key] = {'data': data, 'timestamp': time.time()}

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None,
                data: Optional[Dict[str, Any]] = None, files=None, use_cache: bool = True) -> Any:
        url = f"{self.base_url}{path}"
        if method == 'GET' and use_cache:
            cache_key = self._get_cache_key(path, params)
            if self._is_cache_valid(cache_key):
                logger.info(f"Cache hit for {path}")
                return self.cache[cache_key]['data']

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=30)
                elif method == 'POST':
                    response = self.session.post(url, data=data, files=files, timeout=60)
                elif method == 'PUT':
                    response = self.session.put(url, data=data, timeout=60)
                elif method == 'DELETE':
                    response = self.session.delete(url, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                result = response.json()
                if method == 'GET' and use_cache:
                    self._cache_response(cache_key, result)  # type: ignore[name-defined]
                return result
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                logger.error(f"HTTP error {getattr(e.response,'status_code', '?')}: {e}")
                raise
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
                time.sleep(1)
        raise requests.exceptions.RequestException("Max retries exceeded")

    # API methods (subset retained; reference original for full coverage)
    def list_courses(self, enrollment_type: str = 'teacher') -> List[Dict[str, Any]]:
        return self._request('GET', '/api/v1/courses', params={'enrollment_type': enrollment_type})

    def get_course(self, course_id: str) -> Dict[str, Any]:
        return self._request('GET', f'/api/v1/courses/{course_id}')

    def publish_course(self, course_id: str) -> Dict[str, Any]:
        return self._request('PUT', f'/api/v1/courses/{course_id}', data={'course[event]': 'offer'})

    def unpublish_course(self, course_id: str) -> Dict[str, Any]:
        return self._request('PUT', f'/api/v1/courses/{course_id}', data={'course[event]': 'claim'})

    def list_assignments(self, course_id: str, include: List[str] | None = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if include:
            params['include'] = include
        return self._request('GET', f'/api/v1/courses/{course_id}/assignments', params=params)

    def create_assignment(self, course_id: str, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('POST', f'/api/v1/courses/{course_id}/assignments', data=assignment_data)

    def list_modules(self, course_id: str, include: List[str] | None = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if include:
            params['include'] = include
        return self._request('GET', f'/api/v1/courses/{course_id}/modules', params=params)

    def create_module(self, course_id: str, name: str, position: int | None = None, publish: bool = True) -> Dict[str, Any]:
        data: Dict[str, Any] = {'module[name]': name}
        if position is not None:
            data['module[position]'] = str(position)
        if publish:
            data['module[published]'] = 'true'
        return self._request('POST', f'/api/v1/courses/{course_id}/modules', data=data)

    def list_module_items(self, course_id: str, module_id: str) -> List[Dict[str, Any]]:
        return self._request('GET', f'/api/v1/courses/{course_id}/modules/{module_id}/items')

    def create_module_item(self, course_id: str, module_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request('POST', f'/api/v1/courses/{course_id}/modules/{module_id}/items', data=item_data)

    def list_files(self, course_id: str) -> List[Dict[str, Any]]:
        return self._request('GET', f'/api/v1/courses/{course_id}/files')

    def list_announcements(self, course_id: str) -> List[Dict[str, Any]]:
        return self._request('GET', f'/api/v1/courses/{course_id}/discussion_topics', params={'only_announcements': True})

    def create_announcement(self, course_id: str, title: str, message: str, publish: bool = True) -> Dict[str, Any]:
        data = {'title': title, 'message': message, 'is_announcement': True, 'published': publish}
        return self._request('POST', f'/api/v1/courses/{course_id}/discussion_topics', data=data)

    def list_students(self, course_id: str) -> List[Dict[str, Any]]:
        return self._request('GET', f'/api/v1/courses/{course_id}/enrollments', params={'type': ['StudentEnrollment']})

    def get_user_profile(self, user_id: str = 'self') -> Dict[str, Any]:
        return self._request('GET', f'/api/v1/users/{user_id}/profile')

    def clear_cache(self) -> None:
        self.cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        total_entries = len(self.cache)
        expired_entries = sum(1 for key in self.cache if not self._is_cache_valid(key))
        return {
            'total_entries': total_entries,
            'valid_entries': total_entries - expired_entries,
            'expired_entries': expired_entries,
            'cache_ttl': self.cache_ttl
        }
