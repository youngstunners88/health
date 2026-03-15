import json, os
from pathlib import Path
_DEFAULT_STORE_PATH = Path(os.getenv("PERSISTENT_AGENT_MEMORY_PATH", "/root/.openclaw/workspace/memory/persistent_store.json"))
_DEFAULT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

def _read_store():
    if not _DEFAULT_STORE_PATH.is_file():
        return {}
    try:
        with _DEFAULT_STORE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_store(data):
    with _DEFAULT_STORE_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def save_memory(key, value):
    data = _read_store()
    data[key] = value
    _write_store(data)

def load_memory(key, default=None):
    return _read_store().get(key, default)

def clear_memory():
    _write_store({})