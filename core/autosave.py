#!/usr/bin/env python3
"""
Auto-save mechanism for Solomon's Chamber Healthcare Platform.
Automatically saves all work to the vault with proper routing.

Usage:
    from healthcare_autosave import autosave
    autosave.save("risk-scoring-algorithm.md", "# Risk Scoring\n...", tags=["clinical", "algorithm"])
    autosave.route_and_save("patient-portal-api.py", "from fastapi import...", module="patient_portal")
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.router import router as healthcare_router


class HealthcareAutoSave:
    """
    Automatically saves all healthcare platform work to Solomon's Chamber.

    Every save is:
    1. Routed to the correct module based on content/tags
    2. Backed up if file already exists
    3. Logged with metadata
    4. Synced to the vault's state
    """

    def __init__(self):
        self.router = healthcare_router
        self.save_log = []

    def save(
        self,
        filename: str,
        content: str,
        tags: list[str] | None = None,
        module: str | None = None,
    ) -> str:
        """Save a file with auto-routing."""
        dest = self.router.save_file(filename, content, tags=tags, module=module)

        entry = {
            "filename": filename,
            "destination": dest,
            "tags": tags or [],
            "module": module or "auto-detected",
            "size_bytes": len(content),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save_log.append(entry)

        print(f"  ✓ Saved: {filename} → {dest}")
        return dest

    def save_module(
        self, module: str, filename: str, content: str, tags: list[str] | None = None
    ) -> str:
        """Save directly to a specific module."""
        module_dir = PROJECT_ROOT / "modules" / module
        module_dir.mkdir(parents=True, exist_ok=True)

        dest_file = module_dir / filename
        if dest_file.exists():
            backup = module_dir / f"{dest_file.stem}.bak{dest_file.suffix}"
            import shutil

            shutil.copy2(dest_file, backup)

        dest_file.write_text(content)

        entry = {
            "filename": filename,
            "destination": str(dest_file),
            "module": module,
            "tags": tags or [],
            "size_bytes": len(content),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save_log.append(entry)

        print(f"  ✓ Module save: {module}/{filename}")
        return str(dest_file)

    def save_core(self, filename: str, content: str) -> str:
        """Save to core layer."""
        return self.save_module("core", filename, content, tags=["core"])

    def save_shared(self, filename: str, content: str) -> str:
        """Save to shared layer."""
        return self.save_module("shared", filename, content, tags=["shared"])

    def save_skill(self, skill_name: str, filename: str, content: str) -> str:
        """Save to a skill."""
        skill_dir = PROJECT_ROOT / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        dest_file = skill_dir / filename
        dest_file.write_text(content)

        print(f"  ✓ Skill save: {skill_name}/{filename}")
        return str(dest_file)

    def save_session_log(self, session_content: str) -> str:
        """Save a session log to the docs folder."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M")
        filename = f"session-{timestamp}.md"
        docs_dir = PROJECT_ROOT / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        dest_file = docs_dir / filename
        dest_file.write_text(session_content)

        print(f"  ✓ Session log: {filename}")
        return str(dest_file)

    def get_stats(self) -> dict:
        """Get save statistics."""
        module_counts = {}
        for entry in self.save_log:
            mod = entry.get("module", "unknown")
            module_counts[mod] = module_counts.get(mod, 0) + 1

        return {
            "total_saves": len(self.save_log),
            "module_counts": module_counts,
            "total_bytes": sum(e.get("size_bytes", 0) for e in self.save_log),
        }


# Singleton
autosave = HealthcareAutoSave()


if __name__ == "__main__":
    # Test auto-save
    print("Testing auto-save...")
    autosave.save("test-note.md", "# Test\nThis is a test note.", tags=["test"])
    autosave.save_module("patient_portal", "test-api.py", "# Test API", tags=["test"])
    stats = autosave.get_stats()
    print(f"\nStats: {stats}")
