"""
Intelligent task router for meta-skills.
Routes tasks to the appropriate skill based on context analysis.
"""

import re
from pathlib import Path
from datetime import datetime, timezone


ROUTING_RULES = {
    "design-md": {
        "keywords": [
            "design",
            "ui",
            "frontend",
            "landing page",
            "css",
            "styling",
            "theme",
            "color palette",
            "typography",
            "component",
            "responsive",
            "dark mode",
            "light mode",
            "design system",
            "tailwind",
            "build a page",
            "build a dashboard",
            "build a form",
            "make it look like",
            "clone the design",
            "replicate the ui",
        ],
        "patterns": [
            r"build\s+(a|an|the)\s+(page|dashboard|form|ui|interface|component)",
            r"design\s+(a|an|the)\s+(page|dashboard|form|ui|interface)",
            r"(make|style|look)\s+like\s+\w+",
            r"apply\s+(design|theme|style)",
        ],
        "priority": 1,
    },
    "browser-use": {
        "keywords": [
            "browse",
            "scrape",
            "web",
            "url",
            "website",
            "http",
            "fill form",
            "login",
            "sign in",
            "navigate",
            "click",
            "screenshot",
            "extract from",
            "research online",
            "check website",
            "look up",
            "search for",
            "download",
            "automate browser",
            "web automation",
        ],
        "patterns": [
            r"go\s+to\s+(https?://|www\.)",
            r"(open|visit|navigate)\s+(to\s+)?(https?://|www\.|the\s+website)",
            r"(scrape|extract)\s+(data|info|content)\s+from",
            r"(fill|complete)\s+(the\s+)?form",
            r"research\s+(online|the\s+web|about)",
        ],
        "priority": 2,
    },
    "autoagent": {
        "keywords": [
            "agent",
            "harness",
            "benchmark",
            "optimize agent",
            "improve agent",
            "agent score",
            "agent performance",
            "iterate on agent",
            "agent engineering",
            "self-improving",
            "autoagent",
            "meta-agent",
        ],
        "patterns": [
            r"(optimize|improve|iterate)\s+(the\s+)?agent",
            r"run\s+(benchmark|evaluation|test)",
            r"agent\s+(score|performance|quality)",
        ],
        "priority": 3,
    },
    "superpowers": {
        "keywords": [
            "build",
            "code",
            "implement",
            "feature",
            "bug",
            "plan",
            "brainstorm",
            "design doc",
            "spec",
            "architecture",
            "refactor",
            "test",
            "debug",
            "fix",
            "create",
            "development",
            "engineering",
            "software",
        ],
        "patterns": [
            r"(build|create|implement)\s+(a|an|the)\s+(feature|system|service|api|endpoint)",
            r"(fix|debug|resolve)\s+(a|the\s+)?(bug|issue|error|problem)",
            r"(plan|design|architect)\s+(a|an|the)\s+(feature|system|service)",
            r"how\s+(should|do)\s+(we|i)\s+(build|implement|approach)",
        ],
        "priority": 4,
    },
}


class TaskRouter:
    """Routes tasks to the appropriate meta-skill based on context analysis."""

    def __init__(self):
        self._compiled_patterns = {}
        for skill, rules in ROUTING_RULES.items():
            self._compiled_patterns[skill] = [
                re.compile(p, re.IGNORECASE) for p in rules.get("patterns", [])
            ]

    def route(self, task_description: str, context: dict | None = None) -> dict:
        """
        Route a task description to the appropriate skill.

        Args:
            task_description: Natural language description of the task
            context: Optional context dict with current state, active skills, etc.

        Returns:
            Dict with 'skill', 'confidence', 'reasoning', and 'action'
        """
        task_lower = task_description.lower()
        scores = {}

        for skill, rules in ROUTING_RULES.items():
            score = 0
            matched_keywords = []
            matched_patterns = []

            for keyword in rules["keywords"]:
                if keyword.lower() in task_lower:
                    score += 1
                    matched_keywords.append(keyword)

            for pattern in self._compiled_patterns[skill]:
                if pattern.search(task_lower):
                    score += 3
                    matched_patterns.append(pattern.pattern)

            if score > 0:
                scores[skill] = {
                    "score": score,
                    "matched_keywords": matched_keywords,
                    "matched_patterns": matched_patterns,
                }

        if not scores:
            return {
                "skill": "general",
                "confidence": 0.0,
                "reasoning": "No meta-skill matched; using general approach",
                "action": "handle_directly",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        best_skill = max(scores, key=lambda s: scores[s]["score"])
        best_score = scores[best_skill]["score"]
        max_possible = (
            len(ROUTING_RULES[best_skill]["keywords"])
            + len(ROUTING_RULES[best_skill]["patterns"]) * 3
        )
        confidence = min(best_score / max_possible, 1.0)

        return {
            "skill": best_skill,
            "confidence": round(confidence, 2),
            "reasoning": f"Matched keywords: {scores[best_skill]['matched_keywords']}, patterns: {len(scores[best_skill]['matched_patterns'])}",
            "action": f"execute_{best_skill.replace('-', '_')}",
            "matched_keywords": scores[best_skill]["matched_keywords"],
            "matched_patterns": scores[best_skill]["matched_patterns"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def route_healthcare_task(self, task_description: str) -> dict:
        """Check if task should go to healthcare workspace first."""
        healthcare_keywords = [
            "healthcare",
            "patient",
            "discharge",
            "ehr",
            "medical",
            "clinical",
            "hospital",
            "readmission",
            "medication",
            "vitals",
            "diagnosis",
            "treatment",
            "care",
        ]
        task_lower = task_description.lower()
        if any(kw in task_lower for kw in healthcare_keywords):
            return {
                "skill": "healthcare",
                "confidence": 0.9,
                "reasoning": "Healthcare-related task detected",
                "action": "route_to_healthcare_workspace",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return None
