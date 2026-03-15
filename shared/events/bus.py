"""
Event Bus - Pub/Sub for cross-service communication.
Decouples services: emit events, subscribers react independently.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Callable, Any
from collections import defaultdict


logger = logging.getLogger("healthcare.events")

EVENT_LOG_DIR = Path(__file__).parent.parent.parent / "data" / "events"
EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)


class EventBus:
    """
    Async event bus with:
    - Type-safe event handlers
    - Event persistence for audit trail
    - Retry on handler failure
    - Wildcard subscriptions (*.patient.*)
    """

    def __init__(self, max_retries: int = 3, persist: bool = True):
        self._handlers = defaultdict(list)
        self._max_retries = max_retries
        self._persist = persist
        self._event_log = EVENT_LOG_DIR / "events.jsonl"

    def on(self, event_type: str, handler: Callable):
        """Subscribe to an event type."""
        self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def emit(self, event_type: str, payload: dict):
        """Emit an event to all matching handlers."""
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "id": f"evt-{__import__('uuid').uuid4().hex[:8]}",
        }

        if self._persist:
            self._log_event(event)

        handlers = self._match_handlers(event_type)
        for handler in handlers:
            await self._execute_handler(handler, event)

    def emit_sync(self, event_type: str, payload: dict):
        """Synchronous emit for non-async contexts."""
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "id": f"evt-{__import__('uuid').uuid4().hex[:8]}",
        }

        if self._persist:
            self._log_event(event)

        handlers = self._match_handlers(event_type)
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.get_event_loop().run_until_complete(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event_type}: {e}")

    def _match_handlers(self, event_type: str) -> list[Callable]:
        """Find all handlers matching the event type, including wildcards."""
        handlers = list(self._handlers.get(event_type, []))

        for pattern, pattern_handlers in self._handlers.items():
            if "*" in pattern:
                parts = pattern.split(".")
                event_parts = event_type.split(".")
                if len(parts) == len(event_parts):
                    match = all(p == e or p == "*" for p, e in zip(parts, event_parts))
                    if match:
                        handlers.extend(pattern_handlers)

        return handlers

    async def _execute_handler(self, handler: Callable, event: dict):
        """Execute a handler with retry logic."""
        for attempt in range(self._max_retries):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                return
            except Exception as e:
                logger.error(
                    f"Handler attempt {attempt + 1} failed for {event['type']}: {e}"
                )
                if attempt == self._max_retries - 1:
                    logger.error(f"All retries exhausted for {event['type']}")

    def _log_event(self, event: dict):
        """Append event to JSONL log file."""
        try:
            with open(self._event_log, "a") as f:
                f.write(json.dumps(event, default=str) + "\n")
        except IOError:
            pass

    def get_event_history(
        self, event_type: str | None = None, limit: int = 100
    ) -> list[dict]:
        """Read recent events from the log."""
        if not self._event_log.exists():
            return []

        events = []
        try:
            with open(self._event_log, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if event_type is None or event.get("type") == event_type:
                            events.append(event)
                    except json.JSONDecodeError:
                        continue
        except IOError:
            pass

        return events[-limit:]


# Singleton
event_bus = EventBus()

# ─── Standard Event Types ────────────────────────────────────────────────


class Events:
    PATIENT_CREATED = "patient.created"
    PATIENT_UPDATED = "patient.updated"
    PATIENT_DISCHARGED = "patient.discharged"
    VITALS_RECORDED = "vitals.recorded"
    VITALS_ALERT = "vitals.alert"
    RISK_ASSESSED = "risk.assessed"
    PRIOR_AUTH_SUBMITTED = "prior_auth.submitted"
    PRIOR_AUTH_DECIDED = "prior_auth.decided"
    CLAIM_SUBMITTED = "claim.submitted"
    CLAIM_ADJUDICATED = "claim.adjudicated"
    SDOH_SCREENED = "sdoh.screened"
    SDOH_REFERRAL_CREATED = "sdoh.referral_created"
    DEVICE_REGISTERED = "device.registered"
    DEVICE_READING = "device.reading"
    NOTIFICATION_SENT = "notification.sent"
    ALERT_CREATED = "alert.created"
    ALERT_RESOLVED = "alert.resolved"
    CARE_TEAM_UPDATED = "care_team.updated"
    TRIAL_MATCHED = "trial.matched"
