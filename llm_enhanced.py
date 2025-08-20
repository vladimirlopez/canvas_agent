# DEPRECATED: moved to python/canvas_agent/llm_enhanced.py
# Import from canvas_agent.llm_enhanced instead.

"""Enhanced LLM integration using Ollama API for better conversational flow."""
import subprocess
import json
import requests
from typing import List, Dict, Any, Optional, Union

def list_ollama_models() -> List[str]:
    """Get available Ollama models."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        models = []
        for line in result.stdout.splitlines()[1:]:  # skip header
            if line.strip():
                models.append(line.split()[0])
        return models
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

def ollama_chat_api(model: str, messages: List[Dict[str, str]], 
                   stream: bool = False, options: Optional[Dict[str, Any]] = None) -> str:
    """Use Ollama API endpoint for more reliable chat (avoids subprocess)."""
    try:
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": options or {}
        }
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "No response")
    except requests.exceptions.RequestException as e:
        return f"[LLM API Error] {e}"
    except Exception as e:
        return f"[LLM Error] {e}"

def ollama_chat(model: str, prompt: str, system: str = None, use_api: bool = True) -> str:
    """Chat with Ollama model. Prefer API over subprocess for stability."""
    if use_api:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return ollama_chat_api(model, messages)
    
    # Fallback to subprocess (legacy)
    cmd = ["ollama", "run", model]
    full_prompt = prompt if system is None else f"System: {system}\nUser: {prompt}"
    try:
        result = subprocess.run(cmd, input=full_prompt, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return f"[LLM Error] {result.stderr}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[LLM Error] Request timed out"
    except FileNotFoundError:
        return "[LLM Error] Ollama not installed or not in PATH"
    except Exception as e:
        return f"[LLM Error] {e}"

def check_ollama_service() -> Dict[str, Union[bool, str]]:
    """Check if Ollama service is running and responsive."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = [model["name"] for model in response.json().get("models", [])]
            return {"running": True, "message": f"Service active, {len(models)} models available"}
        else:
            return {"running": False, "message": f"Service responded with status {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"running": False, "message": "Service not reachable (is Ollama running?)"}
    except Exception as e:
        return {"running": False, "message": f"Service check failed: {e}"}
