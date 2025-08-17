import subprocess
import json
from typing import List

def list_ollama_models() -> List[str]:
    try:
        output = subprocess.check_output(["ollama", "list"], text=True)
        models = []
        for line in output.splitlines()[1:]:  # skip header line 'NAME ...'
            if not line.strip():
                continue
            models.append(line.split()[0])
        return models
    except Exception:
        return []


def ollama_chat(model: str, prompt: str, system: str = None) -> str:
    cmd = ["ollama", "run", model]
    full_prompt = prompt if system is None else f"System: {system}\nUser: {prompt}"
    try:
        output = subprocess.check_output(cmd, input=full_prompt, text=True)
        return output.strip()
    except subprocess.CalledProcessError as e:
        return f"[LLM Error] {e.output}"
    except FileNotFoundError:
        return "[LLM Error] Ollama not installed or not in PATH."
