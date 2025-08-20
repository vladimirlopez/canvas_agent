import os
import requests
from typing import Optional, Dict, Any, List

# DEPRECATED: Use canvas_agent.canvas_client_enhanced.CanvasClientEnhanced instead.
class CanvasClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}'
        })

    # Basic helper
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None):
        url = f"{self.base_url}{path}"
        r = self.session.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: Optional[Dict[str, Any]] = None, files=None):
        url = f"{self.base_url}{path}"
        r = self.session.post(url, data=data, files=files, timeout=60)
        r.raise_for_status()
        return r.json()

    # Canvas endpoints
    def list_courses(self) -> List[Dict[str, Any]]:
        return self._get('/api/v1/courses')

    def list_assignments(self, course_id: str) -> List[Dict[str, Any]]:
        return self._get(f'/api/v1/courses/{course_id}/assignments')

    def list_files(self, course_id: str) -> List[Dict[str, Any]]:
        return self._get(f'/api/v1/courses/{course_id}/files')

    def download_file(self, file_id: str, dest_path: str) -> str:
        # Need file details first
        file_meta = self._get(f'/api/v1/files/{file_id}')
        url = file_meta.get('url') or file_meta.get('download_url')
        if not url:
            raise ValueError('Download URL not found for file')
        r = self.session.get(url, timeout=120)
        r.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'wb') as f:
            f.write(r.content)
        return dest_path

    def upload_file_to_course(self, course_id: str, filepath: str) -> Dict[str, Any]:
        # Simplified upload (2-step process usually). Canvas has a file upload workflow.
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        init_resp = self._post(f'/api/v1/courses/{course_id}/files', data={
            'name': filename,
            'size': size,
            'parent_folder_path': '/',
            'on_duplicate': 'overwrite'
        })
        upload_url = init_resp['upload_url']
        upload_params = init_resp['upload_params']
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f)}
            r = requests.post(upload_url, data=upload_params, files=files, timeout=120)
            r.raise_for_status()
            finish = r.json()
        return finish

    # Modules
    def list_modules(self, course_id: str):
        return self._get(f'/api/v1/courses/{course_id}/modules')

    def create_module(self, course_id: str, name: str, position: int | None = None, publish: bool = True):
        data = {'module[name]': name}
        if position is not None:
            data['module[position]'] = str(position)
        if publish:
            data['module[published]'] = 'true'
        return self._post(f'/api/v1/courses/{course_id}/modules', data=data)
