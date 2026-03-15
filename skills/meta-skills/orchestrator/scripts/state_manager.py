"""
Cross-session state management for meta-skills.
Persists state, tracks task progress, and maintains execution history.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


STATE_DIR = Path(__file__).parent.parent / "state"
STATE_DIR.mkdir(exist_ok=True)


class StateManager:
    """Manages state across meta-skill sessions."""

    def __init__(self, state_dir: Path | None = None):
        self.state_dir = state_dir or STATE_DIR
        self.state_dir.mkdir(exist_ok=True)
        self._cache = {}

    def save_state(self, key: str, value: Any, skill: str | None = None) -> str:
        """Save state with optional skill namespace."""
        if skill:
            full_key = f"{skill}:{key}"
        else:
            full_key = f"meta:{key}"

        state_file = self.state_dir / f"{full_key.replace(':', '_')}.json"
        data = {
            "key": full_key,
            "value": value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        state_file.write_text(json.dumps(data, indent=2, default=str))
        self._cache[full_key] = data
        return full_key

    def load_state(self, key: str, skill: str | None = None) -> Any | None:
        """Load state by key with optional skill namespace."""
        if skill:
            full_key = f"{skill}:{key}"
        else:
            full_key = f"meta:{key}"

        if full_key in self._cache:
            return self._cache[full_key].get("value")

        state_file = self.state_dir / f"{full_key.replace(':', '_')}.json"
        if not state_file.exists():
            return None

        try:
            data = json.loads(state_file.read_text())
            self._cache[full_key] = data
            return data.get("value")
        except (json.JSONDecodeError, KeyError):
            return None

    def get_task_history(self, skill: str | None = None, limit: int = 20) -> list[dict]:
        """Get recent task execution history."""
        history_file = self.state_dir / "task_history.json"
        if not history_file.exists():
            return []

        try:
            history = json.loads(history_file.read_text())
        except json.JSONDecodeError:
            return []

        if skill:
            history = [h for h in history if h.get("skill") == skill]

        return history[-limit:]

    def record_task_execution(
        self,
        skill: str,
        task: str,
        status: str,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """Record a task execution in history."""
        history_file = self.state_dir / "task_history.json"
        history = []
        if history_file.exists():
            try:
                history = json.loads(history_file.read_text())
            except json.JSONDecodeError:
                history = []

        history.append(
            {
                "skill": skill,
                "task": task,
                "status": status,
                "result": result,
                "error": error,
                "executed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        history_file.write_text(json.dumps(history[-100:], indent=2, default=str))

    def get_active_tasks(self) -> dict[str, dict]:
        """Get all currently active/in-progress tasks."""
        active = {}
        for state_file in self.state_dir.glob("active_*.json"):
            try:
                data = json.loads(state_file.read_text())
                key = state_file.stem.replace("active_", "")
                active[key] = data
            except (json.JSONDecodeError, KeyError):
                continue
        return active

    def clear_skill_state(self, skill: str) -> int:
        """Clear all state for a specific skill."""
        count = 0
        for state_file in self.state_dir.glob(f"{skill}_*.json"):
            state_file.unlink()
            count += 1
        return count

    def get_state_summary(self) -> dict:
        """Get summary of all managed state."""
        files = list(self.state_dir.glob("*.json"))
        skills = set()
        for f in files:
            parts = f.stem.split("_", 1)
            if len(parts) > 1:
                skills.add(parts[0])

        return {
            "total_state_files": len(files),
            "skills_with_state": list(skills),
            "state_directory": str(self.state_dir),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
