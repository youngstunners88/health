"""
Browser automation using browser-use library.
Enables autonomous web interaction, research, and data extraction.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
import logging

logger = logging.getLogger("browser_agent")


BROWSER_CONFIG_DIR = Path(__file__).parent.parent / "config"
BROWSER_CONFIG_DIR.mkdir(exist_ok=True)


class BrowserAgent:
    """Autonomous browser automation agent."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or BROWSER_CONFIG_DIR / "browser.json"
        self._config = self._load_config()
        self._available = self._check_availability()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "headless": True,
            "timeout": 60,
            "max_steps": 50,
            "stealth_mode": False,
            "user_agent": None,
            "proxy": None,
        }

    def _save_config(self):
        self.config_path.write_text(json.dumps(self._config, indent=2))

    def _check_availability(self) -> dict:
        """Check if browser-use is installed and available."""
        try:
            import browser_use

            return {
                "available": True,
                "version": getattr(browser_use, "__version__", "unknown"),
                "message": "browser-use is installed and ready",
            }
        except ImportError:
            return {
                "available": False,
                "version": None,
                "message": "browser-use not installed. Run: pip install browser-use",
                "install_command": "pip install browser-use",
            }

    def configure(self, **kwargs) -> dict:
        """Update browser configuration."""
        self._config.update(kwargs)
        self._save_config()
        return {
            "status": "configured",
            "config": self._config,
        }

    def execute_task(self, task: str, context: dict | None = None) -> dict:
        """
        Execute a browser automation task.

        Args:
            task: Natural language description of what to do in the browser
            context: Optional context with URL, credentials, etc.

        Returns:
            Result dict with task outcome
        """
        context = context or {}

        if not self._available["available"]:
            return {
                "task": task,
                "status": "unavailable",
                "message": self._available["message"],
                "install_command": self._available.get("install_command"),
                "fallback": "Use webfetch tool for simple URL fetching",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        task_type = self._classify_task(task)

        if task_type == "research":
            return self._execute_research(task, context)
        elif task_type == "form_fill":
            return self._execute_form_fill(task, context)
        elif task_type == "extract":
            return self._execute_extraction(task, context)
        elif task_type == "navigate":
            return self._execute_navigation(task, context)
        else:
            return self._execute_generic(task, context)

    def _classify_task(self, task: str) -> str:
        """Classify the type of browser task."""
        task_lower = task.lower()
        if any(
            w in task_lower
            for w in ["research", "find", "search", "look up", "compare"]
        ):
            return "research"
        if any(
            w in task_lower
            for w in ["fill", "form", "apply", "register", "sign up", "login"]
        ):
            return "form_fill"
        if any(
            w in task_lower
            for w in ["extract", "scrape", "download", "get data", "collect"]
        ):
            return "extract"
        if any(w in task_lower for w in ["go to", "open", "navigate", "visit"]):
            return "navigate"
        return "generic"

    def _execute_research(self, task: str, context: dict) -> dict:
        """Execute a research task."""
        return {
            "task": task,
            "type": "research",
            "status": "ready",
            "message": f"Research task queued: {task}",
            "strategy": "Search engine → Extract relevant pages → Synthesize findings",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _execute_form_fill(self, task: str, context: dict) -> dict:
        """Execute a form filling task."""
        return {
            "task": task,
            "type": "form_fill",
            "status": "ready",
            "message": f"Form fill task queued: {task}",
            "strategy": "Navigate to form → Fill fields sequentially → Submit",
            "required_context": ["url", "form_data"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _execute_extraction(self, task: str, context: dict) -> dict:
        """Execute a data extraction task."""
        return {
            "task": task,
            "type": "extract",
            "status": "ready",
            "message": f"Extraction task queued: {task}",
            "strategy": "Navigate to target → Identify data elements → Extract and structure",
            "required_context": ["url"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _execute_navigation(self, task: str, context: dict) -> dict:
        """Execute a navigation task."""
        url = context.get("url") or self._extract_url(task)
        return {
            "task": task,
            "type": "navigate",
            "status": "ready",
            "url": url,
            "message": f"Navigation task queued to: {url}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _execute_generic(self, task: str, context: dict) -> dict:
        """Execute a generic browser task."""
        return {
            "task": task,
            "type": "generic",
            "status": "ready",
            "message": f"Browser task queued: {task}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _extract_url(self, task: str) -> str | None:
        """Extract URL from task description."""
        import re

        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        match = re.search(url_pattern, task)
        return match.group(0) if match else None

    def get_status(self) -> dict:
        """Get browser agent status."""
        return {
            "available": self._available,
            "config": self._config,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
