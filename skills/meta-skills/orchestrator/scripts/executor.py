"""
Autonomous execution engine for meta-skills.
Executes routed tasks without requiring explicit permission.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("meta_executor")


class MetaExecutor:
    """Executes meta-skill tasks autonomously."""

    def __init__(self):
        from skills.meta_skills.orchestrator.scripts.router import TaskRouter
        from skills.meta_skills.orchestrator.scripts.state_manager import StateManager

        self.router = TaskRouter()
        self.state = StateManager()

    def execute(self, task_description: str, context: dict | None = None) -> dict:
        """
        Route and execute a task autonomously.

        Args:
            task_description: Natural language task description
            context: Optional execution context

        Returns:
            Execution result dict
        """
        healthcare_route = self.router.route_healthcare_task(task_description)
        if healthcare_route:
            return {
                **healthcare_route,
                "execution": "routed_to_healthcare",
                "message": "Task routed to healthcare workspace",
            }

        route = self.router.route(task_description, context)
        skill = route["skill"]

        if skill == "general":
            return {
                **route,
                "execution": "handled_directly",
                "message": "Task handled with general approach",
            }

        executor_method = getattr(self, f"_execute_{skill.replace('-', '_')}", None)
        if executor_method:
            try:
                result = executor_method(task_description, context)
                self.state.record_task_execution(
                    skill=skill,
                    task=task_description,
                    status="completed",
                    result=result,
                )
                return {
                    **route,
                    "execution": "completed",
                    "result": result,
                }
            except Exception as e:
                logger.exception(f"Execution failed for skill={skill}")
                self.state.record_task_execution(
                    skill=skill,
                    task=task_description,
                    status="failed",
                    error=str(e),
                )
                return {
                    **route,
                    "execution": "failed",
                    "error": str(e),
                }

        return {
            **route,
            "execution": "no_executor",
            "message": f"No executor found for skill: {skill}",
        }

    def _execute_design_md(self, task: str, context: dict | None = None) -> dict:
        """Execute design-md skill task."""
        from skills.meta_skills.design_md.scripts.designer import DesignSystem

        designer = DesignSystem()
        return designer.process_task(task, context)

    def _execute_browser_use(self, task: str, context: dict | None = None) -> dict:
        """Execute browser-use skill task."""
        from skills.meta_skills.browser_use.scripts.browser_agent import BrowserAgent

        agent = BrowserAgent()
        return agent.execute_task(task, context)

    def _execute_autoagent(self, task: str, context: dict | None = None) -> dict:
        """Execute autoagent skill task."""
        from skills.meta_skills.autoagent.scripts.harness import AgentHarness

        harness = AgentHarness()
        return harness.process_task(task, context)

    def _execute_superpowers(self, task: str, context: dict | None = None) -> dict:
        """Execute superpowers skill task."""
        from skills.meta_skills.superpowers.scripts.workflow import DevWorkflow

        workflow = DevWorkflow()
        return workflow.process_task(task, context)
