"""
Healthcare Platform Router
Routes commands, data, and files to the appropriate module within Solomons Chamber.
"""

import re
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATE_DIR = DATA_DIR / "state"
STATE_FILE = STATE_DIR / "router_state.json"
STATE_DIR.mkdir(parents=True, exist_ok=True)


class HealthcareRouter:
    """
    Routes commands, files, and data to the correct healthcare module.

    Usage:
        router = HealthcareRouter()
        result = router.route("check patient PT-001 risk score")
        router.save_file("notes.md", "Patient meeting notes", tags=["patient", "meeting"])
    """

    ROUTING_RULES = [
        {
            "name": "patient_portal",
            "keywords": [
                "patient",
                "portal",
                "login",
                "discharge instructions",
                "medication schedule",
            ],
            "patterns": [
                r"patient\s+(portal|instructions|medications)",
                r"discharge\s+plan",
            ],
            "module": "modules/patient_portal",
            "priority": 100,
        },
        {
            "name": "care_dashboard",
            "keywords": [
                "dashboard",
                "care team",
                "provider",
                "monitor",
                "alert",
                "vitals",
            ],
            "patterns": [
                r"(care|provider)\s+dashboard",
                r"patient\s+monitor",
                r"vitals?\s+(alert|trend)",
            ],
            "module": "modules/care_dashboard",
            "priority": 95,
        },
        {
            "name": "prior_auth",
            "keywords": [
                "prior auth",
                "authorization",
                "payer",
                "insurance",
                "coverage",
            ],
            "patterns": [
                r"prior\s+(auth|authorization)",
                r"insurance\s+(check|coverage)",
                r"payer\s+rules",
            ],
            "module": "modules/prior_auth",
            "priority": 90,
        },
        {
            "name": "revenue_cycle",
            "keywords": [
                "claim",
                "billing",
                "revenue",
                "era",
                "remittance",
                "charge",
                "denial",
            ],
            "patterns": [
                r"(submit|process)\s+claim",
                r"revenue\s+cycle",
                r"denial\s+(management|appeal)",
            ],
            "module": "modules/revenue_cycle",
            "priority": 85,
        },
        {
            "name": "sdoh",
            "keywords": [
                "sdoh",
                "social determinants",
                "housing",
                "food security",
                "transportation",
                "referral",
            ],
            "patterns": [
                r"sdoh\s+screen",
                r"social\s+determinants",
                r"community\s+resource",
                r"auto.?referral",
            ],
            "module": "modules/sdoh",
            "priority": 80,
        },
        {
            "name": "wearables",
            "keywords": [
                "wearable",
                "device",
                "bluetooth",
                "fitbit",
                "apple health",
                "cgm",
                "sensor",
            ],
            "patterns": [
                r"(register|sync)\s+device",
                r"wearable\s+data",
                r"bluetooth\s+(bp|glucose|scale)",
            ],
            "module": "modules/wearables",
            "priority": 75,
        },
        {
            "name": "notifications",
            "keywords": [
                "sms",
                "whatsapp",
                "notification",
                "reminder",
                "twilio",
                "alert",
            ],
            "patterns": [
                r"send\s+(sms|whatsapp|notification)",
                r"medication\s+reminder",
                r"appointment\s+alert",
            ],
            "module": "modules/notifications",
            "priority": 70,
        },
        {
            "name": "clinical_trials",
            "keywords": [
                "clinical trial",
                "trial match",
                "eligibility",
                "research study",
            ],
            "patterns": [r"trial\s+match", r"clinical\s+trial", r"eligibility\s+check"],
            "module": "modules/clinical_trials",
            "priority": 65,
        },
        {
            "name": "marketplace",
            "keywords": ["skill", "plugin", "marketplace", "install", "publish"],
            "patterns": [r"(install|publish|search)\s+skill", r"skill\s+marketplace"],
            "module": "modules/marketplace",
            "priority": 60,
        },
        {
            "name": "compliance",
            "keywords": ["hipaa", "compliance", "audit", "soc2", "fda", "baa", "phi"],
            "patterns": [
                r"hipaa\s+(check|audit|compliance)",
                r"compliance\s+score",
                r"phi\s+encrypt",
            ],
            "module": "modules/compliance",
            "priority": 55,
        },
        {
            "name": "core",
            "keywords": ["state", "event", "config", "registry", "domain", "model"],
            "patterns": [
                r"state\s+(store|set|get)",
                r"emit\s+event",
                r"service\s+registry",
            ],
            "module": "core",
            "priority": 50,
        },
        {
            "name": "skills",
            "keywords": ["skill", "risk score", "medication", "discharge", "anomaly"],
            "patterns": [
                r"risk\s+(score|assessment)",
                r"medication\s+reconcil",
                r"discharge\s+planning",
            ],
            "module": "skills",
            "priority": 45,
        },
    ]

    def __init__(self):
        self._state = self._load_state()
        self._compiled_patterns = {}
        for rule in self.ROUTING_RULES:
            self._compiled_patterns[rule["name"]] = [
                re.compile(p, re.IGNORECASE) for p in rule.get("patterns", [])
            ]

    def route(self, command: str, context: dict | None = None) -> dict:
        """Route a command string to the appropriate module."""
        scores = {}
        command_lower = command.lower()

        for rule in self.ROUTING_RULES:
            score = 0
            matched_keywords = []
            matched_patterns = []

            for keyword in rule["keywords"]:
                if keyword.lower() in command_lower:
                    score += 1
                    matched_keywords.append(keyword)

            for pattern in self._compiled_patterns[rule["name"]]:
                if pattern.search(command_lower):
                    score += 3
                    matched_patterns.append(pattern.pattern)

            if score > 0:
                scores[rule["name"]] = {
                    "score": score,
                    "keywords": matched_keywords,
                    "patterns": matched_patterns,
                    "module": rule["module"],
                }

        if not scores:
            return {
                "module": "inbox",
                "confidence": 0.0,
                "reason": "No module matched — routed to inbox",
                "command": command,
            }

        best = max(scores, key=lambda s: scores[s]["score"])
        max_possible = (
            len(
                self.ROUTING_RULES[[r["name"] for r in self.ROUTING_RULES].index(best)][
                    "keywords"
                ]
            )
            + len(
                self.ROUTING_RULES[[r["name"] for r in self.ROUTING_RULES].index(best)][
                    "patterns"
                ]
            )
            * 3
        )
        confidence = min(scores[best]["score"] / max_possible, 1.0)

        result = {
            "module": best,
            "module_path": scores[best]["module"],
            "confidence": round(confidence, 2),
            "reason": f"Matched: {scores[best]['keywords']}",
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._log_route(result)
        return result

    def save_file(
        self,
        filename: str,
        content: str,
        tags: list[str] | None = None,
        module: str | None = None,
    ) -> str:
        """Save a file to the appropriate location based on module or auto-detect."""
        if module is None:
            route = self.route(filename + " " + content[:200])
            module = route.get("module", "inbox")

        if module == "inbox":
            dest_dir = PROJECT_ROOT / "inbox"
        else:
            module_path = None
            for rule in self.ROUTING_RULES:
                if rule["name"] == module:
                    module_path = rule["module"]
                    break
            if module_path:
                dest_dir = PROJECT_ROOT / module_path
            else:
                dest_dir = PROJECT_ROOT / "inbox"

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / filename

        if dest_file.exists():
            backup = dest_dir / f"{dest_file.stem}.bak{dest_file.suffix}"
            shutil.copy2(dest_file, backup)

        dest_file.write_text(content)

        self._log_save(filename, str(dest_file), tags)
        return str(dest_file)

    def get_routing_history(self, limit: int = 50) -> list[dict]:
        """Get recent routing history."""
        return self._state.get("routing_history", [])[-limit:]

    def get_stats(self) -> dict:
        """Get routing statistics."""
        history = self._state.get("routing_history", [])
        module_counts = {}
        for entry in history:
            mod = entry.get("module", "unknown")
            module_counts[mod] = module_counts.get(mod, 0) + 1

        return {
            "total_routes": len(history),
            "module_counts": module_counts,
            "files_saved": len(self._state.get("saved_files", [])),
        }

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return {"routing_history": [], "saved_files": []}

    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self._state, indent=2, default=str))

    def _log_route(self, result: dict):
        self._state.setdefault("routing_history", []).append(result)
        self._state["routing_history"] = self._state["routing_history"][-200:]
        self._save_state()

    def _log_save(self, filename: str, path: str, tags: list[str] | None):
        self._state.setdefault("saved_files", []).append(
            {
                "filename": filename,
                "path": path,
                "tags": tags or [],
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._state["saved_files"] = self._state["saved_files"][-500:]
        self._save_state()


# Singleton
router = HealthcareRouter()
