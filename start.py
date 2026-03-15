#!/usr/bin/env python3
"""
Healthcare Platform - Unified Startup
Starts all services with proper ordering, health checks, and graceful shutdown.
"""

import sys
import os
import signal
import time
import subprocess
import asyncio
import httpx
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from healthcare.core.config.settings import config
from healthcare.core.infrastructure.registry import registry


SERVICES = [
    {
        "name": "mcp_ehr",
        "module": "workspaces.healthcare.protocols.mcp_ehr_server",
        "args": [],
    },
    {
        "name": "patient_portal",
        "module": "workspaces.healthcare.patient-portal.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/patient-portal")],
        "uvicorn": True,
    },
    {
        "name": "care_dashboard",
        "module": "workspaces.healthcare.care-dashboard.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/care-dashboard")],
        "uvicorn": True,
    },
    {
        "name": "prior_auth",
        "module": "workspaces.healthcare.prior-auth.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/prior-auth")],
        "uvicorn": True,
    },
    {
        "name": "revenue_cycle",
        "module": "workspaces.healthcare.revenue-cycle.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/revenue-cycle")],
        "uvicorn": True,
    },
    {
        "name": "sdoh",
        "module": "workspaces.healthcare.sdoh.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/sdoh")],
        "uvicorn": True,
    },
    {
        "name": "wearables",
        "module": "workspaces.healthcare.wearables.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/wearables")],
        "uvicorn": True,
    },
    {
        "name": "notifications",
        "module": "workspaces.healthcare.notifications.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/notifications")],
        "uvicorn": True,
    },
    {
        "name": "clinical_trials",
        "module": "workspaces.healthcare.clinical-trials.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/clinical-trials")],
        "uvicorn": True,
    },
    {
        "name": "marketplace",
        "module": "workspaces.healthcare.marketplace.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/marketplace")],
        "uvicorn": True,
    },
    {
        "name": "compliance",
        "module": "workspaces.healthcare.compliance.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/compliance")],
        "uvicorn": True,
    },
    {
        "name": "gateway",
        "module": "workspaces.healthcare.gateway.api.app",
        "args": ["--app-dir", str(ROOT / "workspaces/healthcare/gateway")],
        "uvicorn": True,
    },
]


class PlatformLauncher:
    """Manages the lifecycle of all platform services."""

    def __init__(self, select: list[str] | None = None):
        self.select = select
        self.processes = {}
        self.running = True

    def start_all(self):
        """Start all services in order."""
        print("=" * 60)
        print("HEALTHCARE PLATFORM - STARTING")
        print("=" * 60)
        print(f"Time: {datetime.now(timezone.utc).isoformat()}")
        print(f"Python: {sys.version}")
        print(f"Root: {ROOT}")
        print()

        services_to_start = SERVICES
        if self.select:
            services_to_start = [s for s in SERVICES if s["name"] in self.select]

        for svc in services_to_start:
            self._start_service(svc)

        print()
        print("=" * 60)
        print("WAITING FOR SERVICES TO BECOME HEALTHY...")
        print("=" * 60)

        self._wait_for_health(services_to_start)

        print()
        print("=" * 60)
        print("ALL SERVICES RUNNING")
        print("=" * 60)
        self._print_service_table(services_to_start)

        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.stop_all()

    def _start_service(self, svc: dict):
        """Start a single service."""
        name = svc["name"]
        port = config.SERVICES[name]["port"]

        if svc.get("uvicorn"):
            cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                svc["module"] + ":app",
                "--host",
                "0.0.0.0",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ]
        else:
            cmd = [sys.executable, "-m", svc["module"]]

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + ":" + env.get("PYTHONPATH", "")

        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.processes[name] = proc
        print(f"  [{name:20s}] PID {proc.pid:6d} → :{port}")

    def _wait_for_health(self, services: list[dict], timeout: int = 30):
        """Wait for all services to become healthy."""
        start = time.time()
        healthy = set()

        while time.time() - start < timeout:
            for svc in services:
                name = svc["name"]
                if name in healthy:
                    continue
                port = config.SERVICES[name]["port"]
                try:
                    import urllib.request

                    resp = urllib.request.urlopen(
                        f"http://localhost:{port}/", timeout=2
                    )
                    if resp.status < 500:
                        healthy.add(name)
                        print(f"  ✓ {name:20s} healthy")
                except Exception:
                    pass

            if len(healthy) == len(services):
                return

            time.sleep(1)

        unhealty = [s["name"] for s in services if s["name"] not in healthy]
        if unhealty:
            print(f"  ⚠ Services not healthy after {timeout}s: {', '.join(unhealty)}")

    def _print_service_table(self, services: list[dict]):
        """Print a table of running services."""
        print(f"{'Service':<20} {'Port':<8} {'PID':<8} {'URL'}")
        print("-" * 60)
        for svc in services:
            name = svc["name"]
            port = config.SERVICES[name]["port"]
            proc = self.processes.get(name)
            pid = proc.pid if proc else "N/A"
            url = f"http://localhost:{port}"
            print(f"{name:<20} {port:<8} {pid:<8} {url}")

    def stop_all(self):
        """Stop all services gracefully."""
        for name, proc in self.processes.items():
            print(f"  Stopping {name} (PID {proc.pid})...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("All services stopped.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Start the healthcare platform")
    parser.add_argument("--services", nargs="*", help="Specific services to start")
    parser.add_argument("--list", action="store_true", help="List available services")
    args = parser.parse_args()

    if args.list:
        print("Available services:")
        for svc in SERVICES:
            port = config.SERVICES[svc["name"]]["port"]
            print(f"  {svc['name']:20s} :{port}")
        return

    launcher = PlatformLauncher(select=args.services)

    def signal_handler(sig, frame):
        launcher.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    launcher.start_all()


if __name__ == "__main__":
    main()
