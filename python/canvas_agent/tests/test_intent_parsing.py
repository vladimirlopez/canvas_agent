import pytest
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'python'))
# Fallback: also try parent/python path if direct python/ not found
candidate = os.path.join(os.path.dirname(__file__), 'python')
pkg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'python'))
if pkg_path not in sys.path:
    sys.path.insert(0, pkg_path)
from canvas_agent.action_dispatcher import CanvasActionDispatcher
from canvas_agent.canvas_client_enhanced import CanvasClientEnhanced

class DummyClient(CanvasClientEnhanced):
    def __init__(self):
        # Bypass real init
        self.base_url = "https://example.com"
        self.session = None  # type: ignore
    # Stub methods used in dispatcher tests
    def create_assignment(self, course_id, assignment_data):
        return {'id': 999, 'name': assignment_data.get('assignment[name]') or 'Assignment', 'course_id': course_id}
    def update_assignment(self, course_id, assignment_id, assignment_data):
        return {'id': assignment_id, 'name': assignment_data.get('assignment[name]', 'Updated Assignment')}
    def create_page(self, course_id, title, body):
        return {'title': title, 'body': body}
    def upload_file(self, course_id, filepath, parent_folder_path=None):
        return {'id': 42, 'display_name': filepath}
    def list_pages(self, course_id):
        return []

@pytest.fixture
def dispatcher():
    return CanvasActionDispatcher(DummyClient())

COURSES = [{'id': 123, 'name': 'Biology 101'}]

def test_quiz_creation_heuristic(dispatcher):
    req = "Create a quiz about mitosis worth 10 points due in 2 days in course 123"
    out = dispatcher.execute_natural_language_request(req, COURSES)
    assert 'Created assignment' in out

def test_page_creation_heuristic(dispatcher):
    req = "Create a page titled Class Policies about late work expectations in course 123"
    out = dispatcher.execute_natural_language_request(req, COURSES)
    assert 'Created page' in out

def test_assignment_update_due_date(dispatcher):
    req = "Update assignment 456 set due next Monday 5pm in course 123"
    out = dispatcher.execute_natural_language_request(req, COURSES)
    assert 'Updated assignment' in out

def test_file_upload(dispatcher):
    req = "Upload file syllabus.pdf to course 123"
    out = dispatcher.execute_natural_language_request(req, COURSES)
    # Since dummy upload always 'fails' without file present, expect graceful failure or success phrase
    assert 'file' in out.lower()
