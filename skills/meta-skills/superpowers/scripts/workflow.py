"""
Software development workflow orchestration.
Implements brainstorming → planning → execution → review cycle.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
import logging

logger = logging.getLogger("dev_workflow")


WORKFLOW_DIR = Path(__file__).parent.parent / "workflows"
WORKFLOW_DIR.mkdir(exist_ok=True)


WORKFLOW_STAGES = {
    "brainstorming": {
        "description": "Refine idea through questions, explore alternatives",
        "outputs": ["design_document.md"],
        "triggers": ["build", "create", "implement", "new feature", "how should i"],
    },
    "planning": {
        "description": "Break work into bite-sized tasks with exact steps",
        "outputs": ["implementation_plan.md"],
        "triggers": ["plan", "break down", "steps", "approach"],
    },
    "execution": {
        "description": "Execute plan with TDD and code quality checks",
        "outputs": ["code_changes", "test_results"],
        "triggers": ["execute", "implement", "code", "write"],
    },
    "review": {
        "description": "Review against plan, report issues by severity",
        "outputs": ["review_report.md"],
        "triggers": ["review", "check", "verify", "inspect"],
    },
    "finish": {
        "description": "Verify tests, present merge options, cleanup",
        "outputs": ["completion_report.md"],
        "triggers": ["finish", "complete", "done", "merge"],
    },
}


class DevWorkflow:
    """Orchestrates software development workflows."""

    def __init__(self):
        self._state = self._load_state()

    def _load_state(self) -> dict:
        state_file = WORKFLOW_DIR / "workflow_state.json"
        if state_file.exists():
            try:
                return json.loads(state_file.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "active_workflow": None,
            "current_stage": None,
            "design_document": None,
            "implementation_plan": None,
            "completed_tasks": [],
            "total_tasks": 0,
        }

    def _save_state(self):
        state_file = WORKFLOW_DIR / "workflow_state.json"
        state_file.write_text(json.dumps(self._state, indent=2, default=str))

    def process_task(self, task: str, context: dict | None = None) -> dict:
        """
        Process a development task through the workflow.

        Args:
            task: Natural language description
            context: Optional context with stage, design, etc.

        Returns:
            Result dict with workflow state and next actions
        """
        context = context or {}
        stage = context.get("stage") or self._detect_stage(task)

        if stage == "brainstorming":
            return self._brainstorm(task, context)
        elif stage == "planning":
            return self._plan(task, context)
        elif stage == "execution":
            return self._execute(task, context)
        elif stage == "review":
            return self._review(task, context)
        elif stage == "finish":
            return self._finish(task, context)
        else:
            return self._handle_unknown(task, context)

    def _detect_stage(self, task: str) -> str:
        """Detect workflow stage from task description."""
        task_lower = task.lower()

        if self._state["active_workflow"]:
            return self._state.get("current_stage", "planning")

        for stage, info in WORKFLOW_STAGES.items():
            if any(trigger in task_lower for trigger in info["triggers"]):
                return stage

        if self._state["implementation_plan"]:
            return "execution"
        return "brainstorming"

    def _brainstorm(self, task: str, context: dict) -> dict:
        """Brainstorming stage: refine idea, explore alternatives."""
        questions = self._generate_design_questions(task)

        design_doc = {
            "title": task,
            "problem_statement": "",
            "proposed_solution": "",
            "alternatives_considered": [],
            "technical_decisions": [],
            "risks": [],
            "status": "draft",
        }

        self._state["active_workflow"] = task
        self._state["current_stage"] = "brainstorming"
        self._state["design_document"] = design_doc
        self._save_state()

        return {
            "stage": "brainstorming",
            "status": "started",
            "questions": questions,
            "design_document": design_doc,
            "next_stage": "planning",
            "message": "Answer these questions to refine the design",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _plan(self, task: str, context: dict) -> dict:
        """Planning stage: break work into bite-sized tasks."""
        design = context.get("design_document") or self._state.get(
            "design_document", {}
        )

        tasks = self._break_into_tasks(task, design)

        plan = {
            "title": task,
            "tasks": tasks,
            "total_tasks": len(tasks),
            "completed_tasks": 0,
            "status": "ready",
        }

        self._state["implementation_plan"] = plan
        self._state["current_stage"] = "planning"
        self._state["total_tasks"] = len(tasks)
        self._state["completed_tasks"] = []
        self._save_state()

        return {
            "stage": "planning",
            "status": "complete",
            "plan": plan,
            "next_stage": "execution",
            "message": f"Plan created with {len(tasks)} tasks. Ready to execute.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _execute(self, task: str, context: dict) -> dict:
        """Execution stage: implement with TDD."""
        plan = self._state.get("implementation_plan", {})
        tasks = plan.get("tasks", [])
        completed = self._state.get("completed_tasks", [])

        next_task = None
        for t in tasks:
            if t.get("id") not in completed:
                next_task = t
                break

        if not next_task:
            return {
                "stage": "execution",
                "status": "all_complete",
                "message": "All tasks completed! Ready for review.",
                "next_stage": "review",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "stage": "execution",
            "status": "in_progress",
            "current_task": next_task,
            "progress": f"{len(completed)}/{len(tasks)} tasks complete",
            "tdd_reminder": "Write failing test first, then minimal code to pass",
            "next_stage": "review",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _review(self, task: str, context: dict) -> dict:
        """Review stage: check against plan."""
        plan = self._state.get("implementation_plan", {})

        review = {
            "plan_followed": True,
            "issues": [],
            "critical_issues": [],
            "warnings": [],
            "suggestions": [],
            "status": "pending",
        }

        self._state["current_stage"] = "review"
        self._save_state()

        return {
            "stage": "review",
            "status": "started",
            "review": review,
            "next_stage": "finish",
            "message": "Review code against plan. Critical issues block progress.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _finish(self, task: str, context: dict) -> dict:
        """Finish stage: verify, present options, cleanup."""
        completion = {
            "workflow": self._state.get("active_workflow"),
            "tasks_completed": len(self._state.get("completed_tasks", [])),
            "total_tasks": self._state.get("total_tasks", 0),
            "options": ["merge", "create_pr", "keep_branch", "discard"],
            "status": "ready_for_decision",
        }

        self._state["active_workflow"] = None
        self._state["current_stage"] = None
        self._save_state()

        return {
            "stage": "finish",
            "status": "complete",
            "completion": completion,
            "message": "All tasks done. Choose: merge, PR, keep, or discard.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _handle_unknown(self, task: str, context: dict) -> dict:
        """Handle tasks that don't match a clear stage."""
        return {
            "stage": "auto_detected",
            "detected_stage": self._detect_stage(task),
            "message": f"Detected stage: {self._detect_stage(task)}. Proceeding.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_design_questions(self, task: str) -> list[str]:
        """Generate Socratic questions to refine the design."""
        return [
            "What problem are we solving? Who is the user?",
            "What are the core requirements? What's out of scope?",
            "What are 2-3 alternative approaches? Pros/cons of each?",
            "What existing code/components will this interact with?",
            "What are the key technical decisions? Why those choices?",
            "What could go wrong? What are the risks?",
            "How will we test this? What are the edge cases?",
            "What does success look like? How do we measure it?",
        ]

    def _break_into_tasks(self, task: str, design: dict) -> list[dict]:
        """Break work into bite-sized tasks (2-5 min each)."""
        return [
            {
                "id": "task_1",
                "title": "Setup and scaffolding",
                "description": "Create file structure, imports, basic types/interfaces",
                "verification": "Files exist, imports resolve, types compile",
                "estimated_minutes": 3,
            },
            {
                "id": "task_2",
                "title": "Core logic implementation",
                "description": "Implement the main functionality with tests",
                "verification": "Tests pass, core functionality works",
                "estimated_minutes": 5,
            },
            {
                "id": "task_3",
                "title": "Integration and edge cases",
                "description": "Connect components, handle edge cases, error handling",
                "verification": "Integration tests pass, edge cases covered",
                "estimated_minutes": 5,
            },
            {
                "id": "task_4",
                "title": "Cleanup and documentation",
                "description": "Refactor, add docstrings, update docs",
                "verification": "Code is clean, docs updated, lint passes",
                "estimated_minutes": 3,
            },
        ]

    def get_status(self) -> dict:
        """Get current workflow status."""
        return {
            "active_workflow": self._state.get("active_workflow"),
            "current_stage": self._state.get("current_stage"),
            "progress": f"{len(self._state.get('completed_tasks', []))}/{self._state.get('total_tasks', 0)} tasks",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def complete_task(self, task_id: str) -> dict:
        """Mark a task as completed."""
        completed = self._state.get("completed_tasks", [])
        if task_id not in completed:
            completed.append(task_id)
            self._state["completed_tasks"] = completed
            self._save_state()

        return {
            "task_id": task_id,
            "status": "completed",
            "progress": f"{len(completed)}/{self._state.get('total_tasks', 0)} tasks",
            "all_complete": len(completed) >= self._state.get("total_tasks", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
