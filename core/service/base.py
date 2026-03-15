"""
Base Service - Abstract base for all platform services.
Provides: state management, event emission, logging, error handling.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from healthcare.core.state.store import state_store
from healthcare.shared.events.bus import event_bus, Events
from healthcare.core.config.settings import config


class BaseService(ABC):
    """
    Abstract base for all services.
    Every service gets:
    - Namespaced state store access
    - Event bus integration
    - Structured logging
    - Consistent error handling
    """

    SERVICE_NAME = "base"
    NAMESPACE = "base"

    def __init__(self):
        self.logger = logging.getLogger(f"healthcare.{self.SERVICE_NAME}")
        self.state = state_store
        self.events = event_bus

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get namespaced state."""
        return self.state.get(key, namespace=self.NAMESPACE, default=default)

    def set_state(self, key: str, value: Any, ttl: int | None = None) -> str:
        """Set namespaced state."""
        return self.state.set(key, value, namespace=self.NAMESPACE, ttl=ttl)

    def delete_state(self, key: str) -> bool:
        """Delete namespaced state."""
        return self.state.delete(key, namespace=self.NAMESPACE)

    def emit_event(self, event_type: str, payload: dict):
        """Emit a service-prefixed event."""
        full_type = f"{self.SERVICE_NAME}.{event_type}"
        self.events.emit_sync(full_type, payload)
        self.logger.info(f"Event emitted: {full_type}")

    async def emit_event_async(self, event_type: str, payload: dict):
        """Emit a service-prefixed event asynchronously."""
        full_type = f"{self.SERVICE_NAME}.{event_type}"
        await self.events.emit(full_type, payload)
        self.logger.info(f"Event emitted (async): {full_type}")

    def handle_error(self, operation: str, error: Exception) -> dict:
        """Standardized error handling."""
        self.logger.error(
            f"{self.SERVICE_NAME}.{operation} failed: {error}", exc_info=True
        )
        return {
            "status": "error",
            "operation": f"{self.SERVICE_NAME}.{operation}",
            "error": str(error),
        }

    def get_service_info(self) -> dict:
        """Get service metadata."""
        return {
            "name": self.SERVICE_NAME,
            "namespace": self.NAMESPACE,
            "version": config.VERSION,
            "state_stats": self.state.get_stats(),
        }
