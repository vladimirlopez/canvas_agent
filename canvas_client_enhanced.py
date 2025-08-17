"""Enhanced Canvas client with error handling, caching, and better API coverage."""
import os
import requests
import time
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
import logging

# Configure logging
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
        self.cache = {}
        self.cache_ttl = cache_ttl
        
    def _get_cache_key(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for request."""
        key = f"GET:{path}"
        if params:
            key += f":{hash(str(sorted(params.items())))}"
        return key
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self.cache:
            return False
        return time.time() - self.cache[key]['timestamp'] < self.cache_ttl
    
    def _cache_response(self, key: str, data: Any) -> None:
        """Cache response data."""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, 
                data: Optional[Dict[str, Any]] = None, files=None, use_cache: bool = True) -> Any:
        """Enhanced request with caching, retries, and error handling."""
        url = f"{self.base_url}{path}"
        
        # Check cache for GET requests
        if method == 'GET' and use_cache:
            cache_key = self._get_cache_key(path, params)
            if self._is_cache_valid(cache_key):
                logger.info(f"Cache hit for {path}")
                return self.cache[cache_key]['data']
        
        # Make request with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=30)
                elif method == 'POST':
                    response = self.session.post(url, data=data, files=files, timeout=60)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                result = response.json()
                
                # Cache successful GET requests
                if method == 'GET' and use_cache:
                    self._cache_response(cache_key, result)
                
                return result
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"HTTP error {e.response.status_code}: {e}")
                    raise
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
                time.sleep(1)
        
        raise requests.exceptions.RequestException("Max retries exceeded")
    
    # Canvas API methods
    def list_courses(self, enrollment_type: str = 'teacher') -> List[Dict[str, Any]]:
        """List courses with optional enrollment filtering."""
        params = {'enrollment_type': enrollment_type, 'state': 'available'}
        return self._request('GET', '/api/v1/courses', params=params)
    
    def get_course(self, course_id: str) -> Dict[str, Any]:
        """Get detailed course information."""
        return self._request('GET', f'/api/v1/courses/{course_id}')
    
    def list_assignments(self, course_id: str, include: List[str] = None) -> List[Dict[str, Any]]:
        """List assignments with optional includes."""
        params = {}
        if include:
            params['include'] = include
        return self._request('GET', f'/api/v1/courses/{course_id}/assignments', params=params)
    
    def create_assignment(self, course_id: str, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new assignment."""
        return self._request('POST', f'/api/v1/courses/{course_id}/assignments', data=assignment_data)
    
    def list_modules(self, course_id: str, include: List[str] = None) -> List[Dict[str, Any]]:
        """List course modules."""
        params = {}
        if include:
            params['include'] = include
        return self._request('GET', f'/api/v1/courses/{course_id}/modules', params=params)
    
    def create_module(self, course_id: str, name: str, position: Optional[int] = None, 
                     publish: bool = True) -> Dict[str, Any]:
        """Create a new module."""
        data = {'module[name]': name}
        if position is not None:
            data['module[position]'] = str(position)
        if publish:
            data['module[published]'] = 'true'
        return self._request('POST', f'/api/v1/courses/{course_id}/modules', data=data)
    
    def list_module_items(self, course_id: str, module_id: str) -> List[Dict[str, Any]]:
        """List items in a module."""
        return self._request('GET', f'/api/v1/courses/{course_id}/modules/{module_id}/items')
    
    def create_module_item(self, course_id: str, module_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new module item."""
        return self._request('POST', f'/api/v1/courses/{course_id}/modules/{module_id}/items', data=item_data)
    
    def list_files(self, course_id: str, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files in course or specific folder."""
        if folder_id:
            path = f'/api/v1/folders/{folder_id}/files'
        else:
            path = f'/api/v1/courses/{course_id}/files'
        return self._request('GET', path)
    
    def list_folders(self, course_id: str) -> List[Dict[str, Any]]:
        """List folders in course."""
        return self._request('GET', f'/api/v1/courses/{course_id}/folders')
    
    def download_file(self, file_id: str, dest_path: str) -> str:
        """Download a file."""
        file_meta = self._request('GET', f'/api/v1/files/{file_id}')
        download_url = file_meta.get('url') or file_meta.get('download_url')
        if not download_url:
            raise ValueError('Download URL not found for file')
        
        response = self.session.get(download_url, timeout=120, stream=True)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return dest_path
    
    def upload_file_to_course(self, course_id: str, filepath: str, 
                             folder_path: str = '/') -> Dict[str, Any]:
        """Upload a file to course."""
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        
        # Step 1: Initiate upload
        init_data = {
            'name': filename,
            'size': size,
            'parent_folder_path': folder_path,
            'on_duplicate': 'overwrite'
        }
        init_resp = self._request('POST', f'/api/v1/courses/{course_id}/files', data=init_data)
        
        # Step 2: Upload file
        upload_url = init_resp['upload_url']
        upload_params = init_resp['upload_params']
        
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f)}
            response = requests.post(upload_url, data=upload_params, files=files, timeout=120)
            response.raise_for_status()
            return response.json()
    
    def list_announcements(self, course_id: str) -> List[Dict[str, Any]]:
        """List course announcements."""
        return self._request('GET', f'/api/v1/courses/{course_id}/discussion_topics', 
                           params={'only_announcements': True})
    
    def create_announcement(self, course_id: str, title: str, message: str, 
                          publish: bool = True) -> Dict[str, Any]:
        """Create a new announcement."""
        data = {
            'title': title,
            'message': message,
            'is_announcement': True,
            'published': publish
        }
        return self._request('POST', f'/api/v1/courses/{course_id}/discussion_topics', data=data)
    
    def list_students(self, course_id: str) -> List[Dict[str, Any]]:
        """List students enrolled in course."""
        return self._request('GET', f'/api/v1/courses/{course_id}/enrollments', 
                           params={'type': ['StudentEnrollment']})
    
    def get_user_profile(self, user_id: str = 'self') -> Dict[str, Any]:
        """Get user profile information."""
        return self._request('GET', f'/api/v1/users/{user_id}/profile')
    
    def clear_cache(self) -> None:
        """Clear the request cache."""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        expired_entries = sum(1 for key in self.cache if not self._is_cache_valid(key))
        return {
            'total_entries': total_entries,
            'valid_entries': total_entries - expired_entries,
            'expired_entries': expired_entries,
            'cache_ttl': self.cache_ttl
        }
