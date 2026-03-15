"""
Service Registry - Discovery and health monitoring for all platform services.
"""

import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional

from healthcare.core.config.settings import config


class ServiceRegistry:
    """
    Central service registry with:
    - Service discovery by name
    - Health checking
    - Service metadata
    - Inter-service communication
    """

    def __init__(self):
        self._services = {}
        self._health_cache = {}
        self._cache_ttl = 30  # seconds
        self._last_check = 0

    def register(self, name: str, url: str, metadata: dict | None = None):
        """Register a service."""
        self._services[name] = {
            "name": name,
            "url": url,
            "metadata": metadata or {},
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "unknown",
        }

    def discover(self, name: str) -> dict | None:
        """Get service info by name."""
        return self._services.get(name)

    def discover_all(self) -> dict[str, dict]:
        """Get all registered services."""
        return self._services

    async def check_health(self, name: str) -> dict:
        """Check health of a specific service."""
        service = self._services.get(name)
        if not service:
            return {"name": name, "status": "not_registered"}

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{service['url']}/health")
                service["status"] = "healthy" if resp.status_code == 200 else "degraded"
                service["last_check"] = datetime.now(timezone.utc).isoformat()
                return {
                    "name": name,
                    "status": service["status"],
                    "url": service["url"],
                    "status_code": resp.status_code,
                }
        except Exception as e:
            service["status"] = "unhealthy"
            service["last_check"] = datetime.now(timezone.utc).isoformat()
            return {
                "name": name,
                "status": "unhealthy",
                "url": service["url"],
                "error": str(e),
            }

    async def check_all_health(self) -> dict[str, dict]:
        """Check health of all services in parallel."""
        tasks = [self.check_health(name) for name in self._services]
        results = await asyncio.gather(*tasks)
        return {r["name"]: r for r in results}

    def get_healthy_services(self) -> list[str]:
        """Get list of healthy service names."""
        return [
            name
            for name, svc in self._services.items()
            if svc.get("status") == "healthy"
        ]

    def auto_register_all(self):
        """Auto-register all services from config."""
        for name, svc_config in config.SERVICES.items():
            url = f"http://{svc_config['host']}:{svc_config['port']}"
            self.register(name, url, {"port": svc_config["port"]})


# Singleton with auto-registration
registry = ServiceRegistry()
registry.auto_register_all()
