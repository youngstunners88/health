"""
Centralized State Management
Single source of truth for all platform state with persistence, caching, and pub/sub.
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable
from collections import defaultdict


STATE_DIR = Path(__file__).parent.parent.parent / "data" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


class StateStore:
    """
    Centralized state store with:
    - JSON file persistence
    - In-memory caching
    - Pub/sub event notifications on state changes
    - Namespaced keys (module:key)
    - TTL support
    """

    def __init__(self, state_dir: Path | None = None):
        self.state_dir = state_dir or STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}
        self._subscribers = defaultdict(list)
        self._ttl = {}

    def set(
        self, key: str, value: Any, namespace: str = "default", ttl: int | None = None
    ) -> str:
        """Set a state value with optional TTL (seconds)."""
        full_key = f"{namespace}:{key}"
        entry = {
            "value": value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "namespace": namespace,
        }
        if ttl:
            entry["expires_at"] = (
                datetime.now(timezone.utc).replace(microsecond=0)
                + __import__("datetime").timedelta(seconds=ttl)
            ).isoformat()

        self._cache[full_key] = entry
        self._persist(full_key, entry)
        self._notify(full_key, "set", value)
        return full_key

    def get(self, key: str, namespace: str = "default", default: Any = None) -> Any:
        """Get a state value, checking TTL expiry."""
        full_key = f"{namespace}:{key}"
        entry = self._cache.get(full_key)

        if entry is None:
            entry = self._load(full_key)
            if entry:
                self._cache[full_key] = entry

        if entry is None:
            return default

        if self._is_expired(entry):
            self.delete(key, namespace)
            return default

        return entry.get("value")

    def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete a state value."""
        full_key = f"{namespace}:{key}"
        self._cache.pop(full_key, None)
        state_file = self.state_dir / f"{full_key.replace(':', '_')}.json"
        if state_file.exists():
            state_file.unlink()
        self._notify(full_key, "delete", None)
        return True

    def keys(self, namespace: str | None = None, pattern: str = "*") -> list[str]:
        """List all keys, optionally filtered by namespace."""
        keys = []
        for f in self.state_dir.glob("*.json"):
            key = f.stem.replace("_", ":")
            if namespace and not key.startswith(f"{namespace}:"):
                continue
            keys.append(key)
        return keys

    def subscribe(self, namespace: str, callback: Callable):
        """Subscribe to state changes in a namespace."""
        self._subscribers[namespace].append(callback)

    def unsubscribe(self, namespace: str, callback: Callable):
        """Unsubscribe from state changes."""
        if callback in self._subscribers[namespace]:
            self._subscribers[namespace].remove(callback)

    def clear_namespace(self, namespace: str) -> int:
        """Delete all keys in a namespace."""
        count = 0
        for f in self.state_dir.glob(f"{namespace}_*.json"):
            f.unlink()
            count += 1
        self._cache = {
            k: v for k, v in self._cache.items() if not k.startswith(f"{namespace}:")
        }
        return count

    def get_stats(self) -> dict:
        """Get state store statistics."""
        files = list(self.state_dir.glob("*.json"))
        namespaces = defaultdict(int)
        for f in files:
            parts = f.stem.split("_", 1)
            if parts:
                namespaces[parts[0]] += 1

        return {
            "total_keys": len(files),
            "cache_size": len(self._cache),
            "namespaces": dict(namespaces),
            "state_directory": str(self.state_dir),
        }

    def _persist(self, full_key: str, entry: dict):
        """Persist entry to disk."""
        state_file = self.state_dir / f"{full_key.replace(':', '_')}.json"
        state_file.write_text(json.dumps(entry, indent=2, default=str))

    def _load(self, full_key: str) -> dict | None:
        """Load entry from disk."""
        state_file = self.state_dir / f"{full_key.replace(':', '_')}.json"
        if not state_file.exists():
            return None
        try:
            return json.loads(state_file.read_text())
        except (json.JSONDecodeError, KeyError):
            return None

    def _is_expired(self, entry: dict) -> bool:
        """Check if an entry has expired."""
        expires = entry.get("expires_at")
        if not expires:
            return False
        try:
            return datetime.fromisoformat(expires) < datetime.now(timezone.utc)
        except (ValueError, TypeError):
            return False

    def _notify(self, full_key: str, action: str, value: Any):
        """Notify subscribers of state changes."""
        namespace = full_key.split(":")[0] if ":" in full_key else "default"
        for callback in self._subscribers.get(namespace, []):
            try:
                callback(full_key, action, value)
            except Exception:
                pass


# Singleton
state_store = StateStore()
