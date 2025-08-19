"""LLM integration utilities (refactored)."""
from __future__ import annotations
import subprocess
import requests
from typing import List, Dict, Any, Optional, Union


def list_ollama_models() -> List[str]:
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        models: List[str] = []
        for line in result.stdout.splitlines()[1:]:
            if line.strip():
                models.append(line.split()[0])
        return models
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def ollama_chat_api(model: str, messages: List[Dict[str, str]], stream: bool = False,
                    options: Optional[Dict[str, Any]] = None) -> str:
    try:
        payload = {"model": model, "messages": messages, "stream": stream, "options": options or {}}
        response = requests.post("http://localhost:11434/api/chat", json=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "No response")
    except requests.exceptions.RequestException as e:  # pragma: no cover
        return f"[LLM API Error] {e}"
    except Exception as e:  # pragma: no cover
        return f"[LLM Error] {e}"


def check_ollama_service() -> Dict[str, Union[bool, str]]:
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = [model["name"] for model in response.json().get("models", [])]
            return {"running": True, "message": f"Service active, {len(models)} models available"}
        return {"running": False, "message": f"Service responded with status {response.status_code}"}
    except requests.exceptions.ConnectionError:  # pragma: no cover
        return {"running": False, "message": "Service not reachable (is Ollama running?)"}
    except Exception as e:  # pragma: no cover
        return {"running": False, "message": f"Service check failed: {e}"}
