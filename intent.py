"""Lightweight natural language intent parser for Canvas actions.

Heuristic approach (no external LLM call here):
1. Normalize text
2. Look for keywords indicating action (list, show, create, upload, download)
3. Extract course name fragments and map to course id (requires provided course cache)
4. Extract file/module names or ids

This can be replaced later with a model-based function calling system.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import re


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def find_course_id_by_name(courses: List[Dict[str, Any]], name_fragment: str) -> Optional[str]:
    fragment = name_fragment.lower()
    for c in courses:
        n = (c.get('name') or '').lower()
        if fragment in n:
            return str(c.get('id'))
    return None


def parse_intent(text: str, courses: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    t = normalize(text)
    intent: Dict[str, Any] = {"action": None, "params": {}, "confidence": 0.0}

    # Patterns
    if any(w in t for w in ["list courses", "show courses", "all courses"]):
        intent.update(action="list courses", confidence=0.9)
        return intent

    # course id detection
    course_id_match = re.search(r"course(?: id)?\s*(\d+)", t)
    if course_id_match:
        intent['params']['course_id'] = course_id_match.group(1)

    # explicit number usage
    standalone_id = re.search(r"\b(\d{3,})\b", t)
    if standalone_id and 'course_id' not in intent['params']:
        intent['params']['course_id'] = standalone_id.group(1)

    # course name fragment if provided after 'in' or 'for'
    if courses and 'course_id' not in intent['params']:
        name_frag_match = re.search(r"(?:in|for) ([a-zA-Z0-9 _-]{3,})", t)
        if name_frag_match:
            cid = find_course_id_by_name(courses, name_frag_match.group(1).strip())
            if cid:
                intent['params']['course_id'] = cid

    # modules
    if 'module' in t:
        if any(w in t for w in ['create', 'add', 'new']):
            intent['action'] = 'create module'
            # module name after 'module' keyword
            mod_name_match = re.search(r"module(?: called| named)? ([a-zA-Z0-9 _-]{2,})", t)
            if mod_name_match:
                intent['params']['name'] = mod_name_match.group(1).strip()
            intent['confidence'] = 0.75
        elif any(w in t for w in ['list', 'show', 'get']):
            intent['action'] = 'list modules'
            intent['confidence'] = 0.7

    # files
    if not intent['action'] and 'file' in t and any(w in t for w in ['download', 'get']):
        fid = re.search(r"file\s*(\d+)", t)
        if fid:
            intent['action'] = 'download file'
            intent['params']['file_id'] = fid.group(1)
            intent['confidence'] = 0.7

    # listing assignments
    if not intent['action'] and 'assignment' in t and any(w in t for w in ['list', 'show', 'get']):
        intent['action'] = 'list assignments'
        intent['confidence'] = 0.6

    # listing files
    if not intent['action'] and 'file' in t and any(w in t for w in ['list', 'show']):
        intent['action'] = 'list files'
        intent['confidence'] = 0.55

    # fallback list courses if user just asks about courses
    if not intent['action'] and 'course' in t and any(w in t for w in ['list', 'show', 'what']):
        intent['action'] = 'list courses'
        intent['confidence'] = 0.5

    return intent
