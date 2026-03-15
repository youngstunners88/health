"""
AutoAgent harness for self-improving agent engineering.
Iterates on agent configurations, benchmarks performance, and hill-climbs on score.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
import logging

logger = logging.getLogger("autoagent_harness")


HARNESS_DIR = Path(__file__).parent.parent / "config"
HARNESS_DIR.mkdir(exist_ok=True)


class AgentHarness:
    """Self-improving agent harness engineering."""

    def __init__(self, harness_dir: Path | None = None):
        self.harness_dir = harness_dir or HARNESS_DIR
        self._program = self._load_program()
        self._results = self._load_results()

    def _load_program(self) -> dict:
        program_file = self.harness_dir / "program.json"
        if program_file.exists():
            try:
                return json.loads(program_file.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "directive": "Build and optimize agent configurations",
            "target_score": 0.9,
            "max_iterations": 50,
            "current_iteration": 0,
            "best_score": 0.0,
            "best_config": None,
        }

    def _save_program(self):
        program_file = self.harness_dir / "program.json"
        program_file.write_text(json.dumps(self._program, indent=2, default=str))

    def _load_results(self) -> list[dict]:
        results_file = self.harness_dir / "results.json"
        if results_file.exists():
            try:
                return json.loads(results_file.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_results(self):
        results_file = self.harness_dir / "results.json"
        results_file.write_text(json.dumps(self._results[-100:], indent=2, default=str))

    def process_task(self, task: str, context: dict | None = None) -> dict:
        """
        Process an agent engineering task.

        Args:
            task: Natural language description
            context: Optional context with agent config, benchmark info

        Returns:
            Result dict with iteration outcome
        """
        context = context or {}
        task_lower = task.lower()

        if "benchmark" in task_lower or "run" in task_lower:
            return self._run_benchmark(context)
        elif "optimize" in task_lower or "improve" in task_lower:
            return self._optimize_agent(context)
        elif "configure" in task_lower or "setup" in task_lower:
            return self._configure_harness(context)
        elif "status" in task_lower or "report" in task_lower:
            return self._get_status()
        else:
            return self._process_generic(task, context)

    def _run_benchmark(self, context: dict) -> dict:
        """Run benchmark evaluation on current agent config."""
        iteration = self._program["current_iteration"] + 1
        self._program["current_iteration"] = iteration

        result = {
            "iteration": iteration,
            "status": "benchmark_ready",
            "message": f"Benchmark iteration {iteration} queued",
            "current_config": self._program.get("best_config"),
            "best_score_so_far": self._program["best_score"],
            "strategy": "Run benchmark → Score → Compare → Keep if better",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._results.append(result)
        self._save_results()
        self._save_program()

        return result

    def _optimize_agent(self, context: dict) -> dict:
        """Optimize agent configuration through hill-climbing."""
        iteration = self._program["current_iteration"] + 1
        self._program["current_iteration"] = iteration

        modifications = context.get("modifications", [])

        result = {
            "iteration": iteration,
            "status": "optimization_started",
            "message": f"Optimization iteration {iteration} started",
            "modifications_to_try": modifications,
            "current_best_score": self._program["best_score"],
            "strategy": "Modify config → Benchmark → Compare → Keep if improvement",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._results.append(result)
        self._save_results()
        self._save_program()

        return result

    def _configure_harness(self, context: dict) -> dict:
        """Configure the agent harness."""
        if "directive" in context:
            self._program["directive"] = context["directive"]
        if "target_score" in context:
            self._program["target_score"] = context["target_score"]
        if "max_iterations" in context:
            self._program["max_iterations"] = context["max_iterations"]

        self._save_program()

        return {
            "status": "configured",
            "program": self._program,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _get_status(self) -> dict:
        """Get current harness status."""
        return {
            "program": self._program,
            "total_iterations": len(self._results),
            "recent_results": self._results[-5:],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _process_generic(self, task: str, context: dict) -> dict:
        """Process a generic agent engineering task."""
        return {
            "task": task,
            "status": "queued",
            "message": f"Agent engineering task queued: {task}",
            "current_iteration": self._program["current_iteration"],
            "best_score": self._program["best_score"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def record_benchmark_result(self, score: float, config: dict | None = None):
        """Record a benchmark result and update best if improved."""
        self._program["current_iteration"] += 1

        if score > self._program["best_score"]:
            self._program["best_score"] = score
            if config:
                self._program["best_config"] = config
            improved = True
        else:
            improved = False

        result = {
            "iteration": self._program["current_iteration"],
            "score": score,
            "improved": improved,
            "best_score": self._program["best_score"],
            "config": config,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._results.append(result)
        self._save_results()
        self._save_program()

        return result
