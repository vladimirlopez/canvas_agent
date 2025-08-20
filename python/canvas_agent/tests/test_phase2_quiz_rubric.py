import pytest
import sys, os
pkg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'python'))
if pkg_path not in sys.path:
    sys.path.insert(0, pkg_path)
from canvas_agent.action_dispatcher import CanvasActionDispatcher
from canvas_agent.canvas_client_enhanced import CanvasClientEnhanced

class DummyClient2(CanvasClientEnhanced):
    def __init__(self):
        self.base_url = "https://example.com"
        self.session = None  # type: ignore
    def create_quiz(self, course_id, quiz_data):
        return {'id': 321, 'title': quiz_data.get('quiz[title]')}
    def create_rubric(self, course_id, rubric_data):
        return {'id': 555, 'title': rubric_data.get('rubric[title]')}
    def attach_rubric(self, course_id, rubric_id, association_id, association_type='Assignment', use_for_grading=True):
        return {'id': 777}
    def list_rubrics(self, course_id):
        return [{'id': 555, 'title': 'Quality'}]
    def create_quiz_question(self, course_id, quiz_id, question_data):
        return {'id': 999}

@pytest.fixture
def dispatcher():
    return CanvasActionDispatcher(DummyClient2())

COURSES = [{'id': 123, 'name': 'Biology 101'}]

def test_real_quiz_creation(dispatcher):
    req = "Create a real quiz titled 'Cell Cycle Check' about mitosis worth 5 points due tomorrow in course 123"
    out = dispatcher.execute_natural_language_request(req, COURSES)
    assert 'Created quiz' in out

def test_rubric_creation(dispatcher):
    params = {'course_id': 123, 'title': 'Quality', 'criteria': [{'description': 'Clarity', 'points': 5}]}
    out = dispatcher._create_rubric(params)
    assert 'Created rubric' in out

def test_attach_rubric(dispatcher):
    params = {'course_id': 123, 'rubric_id': 555, 'association_id': 999, 'association_type': 'Assignment'}
    out = dispatcher._attach_rubric(params)
    assert 'Attached rubric' in out
