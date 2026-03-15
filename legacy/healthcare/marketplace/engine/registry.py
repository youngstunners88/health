"""Skill Registry for the Healthcare Marketplace Plugin System."""

import json
import logging
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {
    "clinical",
    "administrative",
    "patient-facing",
    "analytics",
    "integration",
    "monitoring",
}

REQUIRED_FIELDS = {
    "name",
    "description",
    "version",
    "author",
    "category",
    "tags",
    "install_command",
}

VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class SkillValidationError(Exception):
    pass


class DependencyResolutionError(Exception):
    pass


class SkillNotFoundError(Exception):
    pass


class SkillAlreadyInstalledError(Exception):
    pass


def _default_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": "skill-ehr-fhir-sync",
            "name": "EHR FHIR Sync",
            "description": "Synchronize patient records between EHR systems using HL7 FHIR R4 resources with conflict resolution and delta sync.",
            "version": "2.1.0",
            "author": "HealthPlatform Team",
            "category": "integration",
            "tags": ["fhir", "ehr", "hl7", "sync", "interoperability"],
            "install_command": "pip install healthcare-fhir-sync==2.1.0",
            "dependencies": ["requests>=2.28.0", "pydantic>=1.10.0"],
            "rating": 4.8,
            "downloads": 15420,
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-03-01T14:30:00Z",
        },
        {
            "id": "skill-icd10-coder",
            "name": "ICD-10 Auto Coder",
            "description": "AI-powered ICD-10 code suggestion from clinical notes with 95% accuracy. Supports ICD-10-CM and ICD-10-PCS.",
            "version": "3.0.2",
            "author": "MedCode Labs",
            "category": "clinical",
            "tags": ["icd-10", "coding", "nlp", "clinical-notes", "billing"],
            "install_command": "pip install icd10-autocoder==3.0.2",
            "dependencies": ["transformers>=4.30.0", "scikit-learn>=1.2.0"],
            "rating": 4.9,
            "downloads": 28350,
            "created_at": "2024-06-20T08:00:00Z",
            "updated_at": "2025-02-15T11:00:00Z",
        },
        {
            "id": "skill-prior-auth",
            "name": "Prior Authorization Engine",
            "description": "Automate prior authorization submissions and tracking across major payers with real-time status updates.",
            "version": "1.5.0",
            "author": "AuthFlow Inc",
            "category": "administrative",
            "tags": ["prior-auth", "insurance", "payer", "automation", "workflow"],
            "install_command": "pip install prior-auth-engine==1.5.0",
            "dependencies": ["celery>=5.3.0", "redis>=4.5.0"],
            "rating": 4.6,
            "downloads": 9870,
            "created_at": "2024-09-10T12:00:00Z",
            "updated_at": "2025-01-20T09:00:00Z",
        },
        {
            "id": "skill-patient-portal",
            "name": "Patient Portal Widget",
            "description": "Embeddable patient portal with appointment scheduling, bill pay, messaging, and lab result viewing.",
            "version": "4.2.1",
            "author": "PatientFirst Solutions",
            "category": "patient-facing",
            "tags": ["portal", "scheduling", "billing", "messaging", "lab-results"],
            "install_command": "pip install patient-portal-widget==4.2.1",
            "dependencies": ["django>=4.2.0", "stripe>=5.0.0"],
            "rating": 4.7,
            "downloads": 21500,
            "created_at": "2024-03-05T10:00:00Z",
            "updated_at": "2025-03-10T16:00:00Z",
        },
        {
            "id": "skill-population-health",
            "name": "Population Health Analytics",
            "description": "Comprehensive population health dashboards with risk stratification, care gap analysis, and HEDIS measure tracking.",
            "version": "2.8.0",
            "author": "PopHealth Analytics",
            "category": "analytics",
            "tags": [
                "population-health",
                "risk-stratification",
                "hedis",
                "dashboards",
                "quality",
            ],
            "install_command": "pip install population-health-analytics==2.8.0",
            "dependencies": ["pandas>=2.0.0", "plotly>=5.15.0", "numpy>=1.24.0"],
            "rating": 4.5,
            "downloads": 12300,
            "created_at": "2024-07-22T14:00:00Z",
            "updated_at": "2025-02-28T10:00:00Z",
        },
        {
            "id": "skill-hipaa-monitor",
            "name": "HIPAA Compliance Monitor",
            "description": "Real-time HIPAA compliance monitoring with automated alerts for PHI access anomalies and policy violations.",
            "version": "1.9.3",
            "author": "SecureHealth Systems",
            "category": "monitoring",
            "tags": ["hipaa", "compliance", "phi", "alerts", "audit"],
            "install_command": "pip install hipaa-compliance-monitor==1.9.3",
            "dependencies": ["elasticsearch>=8.0.0", "prometheus-client>=0.17.0"],
            "rating": 4.9,
            "downloads": 18900,
            "created_at": "2024-04-18T09:00:00Z",
            "updated_at": "2025-03-05T13:00:00Z",
        },
        {
            "id": "skill-claims-scrubber",
            "name": "Claims Scrubber Pro",
            "description": "Pre-submission claims scrubbing with 200+ edit checks, reducing denial rates by up to 40%. Supports CMS-1500 and UB-04.",
            "version": "5.1.0",
            "author": "CleanClaim Corp",
            "category": "administrative",
            "tags": ["claims", "scrubbing", "denial-prevention", "cms-1500", "ub-04"],
            "install_command": "pip install claims-scrubber-pro==5.1.0",
            "dependencies": ["x12-parser>=2.0.0", "jsonschema>=4.17.0"],
            "rating": 4.8,
            "downloads": 32100,
            "created_at": "2024-01-10T08:00:00Z",
            "updated_at": "2025-03-12T11:00:00Z",
        },
        {
            "id": "skill-telehealth-sdk",
            "name": "Telehealth SDK",
            "description": "HIPAA-compliant video conferencing SDK with waiting room, screen sharing, recording, and EHR integration.",
            "version": "3.3.0",
            "author": "TeleMed Technologies",
            "category": "patient-facing",
            "tags": ["telehealth", "video", "hipaa", "webrtc", "virtual-care"],
            "install_command": "pip install telehealth-sdk==3.3.0",
            "dependencies": ["aiortc>=1.5.0", "cryptography>=41.0.0"],
            "rating": 4.6,
            "downloads": 14200,
            "created_at": "2024-08-30T10:00:00Z",
            "updated_at": "2025-02-10T15:00:00Z",
        },
        {
            "id": "skill-drug-interaction",
            "name": "Drug Interaction Checker",
            "description": "Real-time drug-drug, drug-allergy, and drug-food interaction checking with severity ratings and clinical recommendations.",
            "version": "2.4.1",
            "author": "PharmaSafe Labs",
            "category": "clinical",
            "tags": ["drug-interaction", "pharmacy", "safety", "prescribing", "alerts"],
            "install_command": "pip install drug-interaction-checker==2.4.1",
            "dependencies": ["rxnorm-client>=1.2.0", "fastapi>=0.100.0"],
            "rating": 4.7,
            "downloads": 19800,
            "created_at": "2024-05-12T11:00:00Z",
            "updated_at": "2025-01-30T09:00:00Z",
        },
        {
            "id": "skill-epic-bridge",
            "name": "Epic EHR Bridge",
            "description": "Connector for Epic EHR systems using SMART on FHIR and Epic REST APIs for patient demographics, orders, and results.",
            "version": "1.7.2",
            "author": "InteropWorks",
            "category": "integration",
            "tags": ["epic", "ehr", "smart-on-fhir", "api", "connector"],
            "install_command": "pip install epic-ehr-bridge==1.7.2",
            "dependencies": ["oauthlib>=3.2.0", "fhir.resources>=7.0.0"],
            "rating": 4.4,
            "downloads": 8750,
            "created_at": "2024-10-05T13:00:00Z",
            "updated_at": "2025-02-20T10:00:00Z",
        },
        {
            "id": "skill-ml-readmission",
            "name": "ML Readmission Predictor",
            "description": "Machine learning model for 30-day readmission risk prediction using gradient boosting with SHAP explainability.",
            "version": "2.0.0",
            "author": "PredictiveCare AI",
            "category": "analytics",
            "tags": ["ml", "readmission", "prediction", "shap", "risk-score"],
            "install_command": "pip install ml-readmission-predictor==2.0.0",
            "dependencies": ["xgboost>=2.0.0", "shap>=0.43.0", "joblib>=1.3.0"],
            "rating": 4.8,
            "downloads": 11400,
            "created_at": "2024-11-15T09:00:00Z",
            "updated_at": "2025-03-08T14:00:00Z",
        },
        {
            "id": "skill-uptime-monitor",
            "name": "Healthcare Uptime Monitor",
            "description": "Infrastructure monitoring tailored for healthcare systems with HL7 interface monitoring, message queue health, and SLA tracking.",
            "version": "1.3.0",
            "author": "OpsHealth Inc",
            "category": "monitoring",
            "tags": ["uptime", "hl7", "sla", "infrastructure", "alerting"],
            "install_command": "pip install healthcare-uptime-monitor==1.3.0",
            "dependencies": ["prometheus-client>=0.17.0", "grafana-api>=1.0.0"],
            "rating": 4.5,
            "downloads": 7600,
            "created_at": "2025-01-02T08:00:00Z",
            "updated_at": "2025-03-01T12:00:00Z",
        },
    ]


def _validate_skill(skill: dict[str, Any]) -> None:
    missing = REQUIRED_FIELDS - set(skill.keys())
    if missing:
        raise SkillValidationError(f"Missing required fields: {missing}")
    if skill["category"] not in VALID_CATEGORIES:
        raise SkillValidationError(
            f"Invalid category '{skill['category']}'. Must be one of: {VALID_CATEGORIES}"
        )
    if not VERSION_PATTERN.match(skill["version"]):
        raise SkillValidationError(
            f"Invalid version '{skill['version']}'. Must follow semver (e.g., 1.0.0)"
        )
    if not isinstance(skill["tags"], list) or len(skill["tags"]) == 0:
        raise SkillValidationError("Tags must be a non-empty list")
    if "dependencies" in skill and not isinstance(skill["dependencies"], list):
        raise SkillValidationError("Dependencies must be a list")


def _resolve_dependencies(
    skill: dict[str, Any],
    installed: dict[str, dict[str, Any]],
    catalog: dict[str, dict[str, Any]],
) -> list[str]:
    resolved = []
    visited = set()

    def _resolve(skill_id: str) -> None:
        if skill_id in visited:
            return
        visited.add(skill_id)
        dep_list = []
        if skill_id == skill.get("id"):
            dep_list = skill.get("dependencies", [])
        elif skill_id in installed:
            dep_list = installed[skill_id].get("dependencies", [])
        elif skill_id in catalog:
            dep_list = catalog[skill_id].get("dependencies", [])
        for dep in dep_list:
            dep_id = dep.split(">=")[0].split("==")[0].split("<")[0].strip()
            if dep_id not in visited:
                _resolve(dep_id)
        resolved.append(skill_id)

    _resolve(skill["id"])
    return resolved


class SkillRegistry:
    """Manages healthcare skill lifecycle: publish, install, uninstall, search."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        skills_dir: Optional[str] = None,
    ) -> None:
        self.data_dir = Path(
            data_dir or os.path.join(os.path.dirname(__file__), "..", "data")
        )
        self.skills_dir = Path(
            skills_dir or os.path.join(os.path.dirname(__file__), "..", "skills")
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        self.catalog_path = self.data_dir / "catalog.json"
        self.installed_path = self.data_dir / "installed.json"
        self.stats_path = self.data_dir / "stats.json"

        self._catalog: dict[str, dict[str, Any]] = {}
        self._installed: dict[str, dict[str, Any]] = {}
        self._stats: dict[str, Any] = {}

        self._load()

    def _load(self) -> None:
        if self.catalog_path.exists():
            try:
                with open(self.catalog_path, "r") as f:
                    raw = json.load(f)
                self._catalog = {s["id"]: s for s in raw}
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Failed to load catalog, using defaults: %s", exc)
                self._catalog = {s["id"]: s for s in _default_catalog()}
        else:
            self._catalog = {s["id"]: s for s in _default_catalog()}
            self._save_catalog()

        if self.installed_path.exists():
            try:
                with open(self.installed_path, "r") as f:
                    raw = json.load(f)
                self._installed = {s["id"]: s for s in raw}
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Failed to load installed skills: %s", exc)
                self._installed = {}
        else:
            self._installed = {}

        if self.stats_path.exists():
            try:
                with open(self.stats_path, "r") as f:
                    self._stats = json.load(f)
            except (json.JSONDecodeError, KeyError):
                self._stats = {}
        else:
            self._stats = {
                "total_publishes": len(self._catalog),
                "total_installs": len(self._installed),
                "total_uninstalls": 0,
                "created_at": datetime.utcnow().isoformat() + "Z",
            }

    def _save_catalog(self) -> None:
        with open(self.catalog_path, "w") as f:
            json.dump(list(self._catalog.values()), f, indent=2)

    def _save_installed(self) -> None:
        with open(self.installed_path, "w") as f:
            json.dump(list(self._installed.values()), f, indent=2)

    def _save_stats(self) -> None:
        with open(self.stats_path, "w") as f:
            json.dump(self._stats, f, indent=2)

    def publish_skill(self, skill_metadata: dict[str, Any]) -> dict[str, Any]:
        _validate_skill(skill_metadata)
        skill_id = skill_metadata.get("id")
        if not skill_id:
            skill_id = f"skill-{skill_metadata['name'].lower().replace(' ', '-')}"
            skill_metadata["id"] = skill_id

        if skill_id in self._catalog:
            existing = self._catalog[skill_id]
            existing.update(skill_metadata)
            existing["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self._catalog[skill_id] = existing
            logger.info("Updated skill %s in catalog", skill_id)
        else:
            skill_metadata["created_at"] = datetime.utcnow().isoformat() + "Z"
            skill_metadata["updated_at"] = skill_metadata["created_at"]
            skill_metadata.setdefault("rating", 0.0)
            skill_metadata.setdefault("downloads", 0)
            self._catalog[skill_id] = skill_metadata
            self._stats["total_publishes"] = self._stats.get("total_publishes", 0) + 1
            logger.info("Published new skill %s", skill_id)

        self._save_catalog()
        self._save_stats()
        return self._catalog[skill_id]

    def install_skill(self, skill_id: str) -> dict[str, Any]:
        if skill_id not in self._catalog:
            raise SkillNotFoundError(f"Skill '{skill_id}' not found in catalog")
        if skill_id in self._installed:
            raise SkillAlreadyInstalledError(f"Skill '{skill_id}' is already installed")

        skill = self._catalog[skill_id]
        resolved = _resolve_dependencies(skill, self._installed, self._catalog)

        for dep_id in resolved:
            if dep_id == skill_id:
                continue
            if dep_id not in self._installed and dep_id in self._catalog:
                dep_skill = self._catalog[dep_id]
                dep_dir = self.skills_dir / dep_id
                dep_dir.mkdir(parents=True, exist_ok=True)
                self._installed[dep_id] = {
                    **dep_skill,
                    "installed_at": datetime.utcnow().isoformat() + "Z",
                    "status": "installed",
                }

        skill_dir = self.skills_dir / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            **skill,
            "installed_at": datetime.utcnow().isoformat() + "Z",
            "status": "installed",
        }
        with open(skill_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        self._installed[skill_id] = manifest

        install_cmd = skill.get("install_command", "")
        if install_cmd:
            try:
                result = subprocess.run(
                    install_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    logger.warning(
                        "Install command for %s returned non-zero: %s",
                        skill_id,
                        result.stderr,
                    )
            except (subprocess.TimeoutExpired, OSError) as exc:
                logger.warning(
                    "Failed to run install command for %s: %s", skill_id, exc
                )

        self._catalog[skill_id]["downloads"] = (
            self._catalog[skill_id].get("downloads", 0) + 1
        )
        self._stats["total_installs"] = self._stats.get("total_installs", 0) + 1

        self._save_catalog()
        self._save_installed()
        self._save_stats()
        logger.info("Installed skill %s", skill_id)
        return manifest

    def uninstall_skill(self, skill_id: str) -> dict[str, Any]:
        if skill_id not in self._installed:
            raise SkillNotFoundError(f"Skill '{skill_id}' is not installed")

        skill_dir = self.skills_dir / skill_id
        if skill_dir.exists():
            shutil.rmtree(skill_dir)

        removed = self._installed.pop(skill_id)
        self._stats["total_uninstalls"] = self._stats.get("total_uninstalls", 0) + 1

        self._save_installed()
        self._save_stats()
        logger.info("Uninstalled skill %s", skill_id)
        return removed

    def search_skills(
        self, query: str = "", category: str = ""
    ) -> list[dict[str, Any]]:
        results = list(self._catalog.values())
        if category:
            results = [
                s for s in results if s.get("category", "").lower() == category.lower()
            ]
        if query:
            query_lower = query.lower()
            filtered = []
            for skill in results:
                searchable = " ".join(
                    [
                        skill.get("name", ""),
                        skill.get("description", ""),
                        " ".join(skill.get("tags", [])),
                        skill.get("author", ""),
                    ]
                ).lower()
                if query_lower in searchable:
                    filtered.append(skill)
            results = filtered
        return sorted(results, key=lambda s: s.get("downloads", 0), reverse=True)

    def get_skill_details(self, skill_id: str) -> dict[str, Any]:
        if skill_id not in self._catalog:
            raise SkillNotFoundError(f"Skill '{skill_id}' not found")
        skill = dict(self._catalog[skill_id])
        skill["is_installed"] = skill_id in self._installed
        if skill_id in self._installed:
            skill["installed_at"] = self._installed[skill_id].get("installed_at")
        return skill

    def get_installed_skills(self) -> list[dict[str, Any]]:
        return list(self._installed.values())

    def get_statistics(self) -> dict[str, Any]:
        category_counts: dict[str, int] = {}
        for skill in self._catalog.values():
            cat = skill.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        total_downloads = sum(s.get("downloads", 0) for s in self._catalog.values())
        avg_rating = (
            sum(s.get("rating", 0) for s in self._catalog.values()) / len(self._catalog)
            if self._catalog
            else 0
        )

        return {
            **self._stats,
            "total_skills": len(self._catalog),
            "installed_skills": len(self._installed),
            "category_counts": category_counts,
            "total_downloads": total_downloads,
            "average_rating": round(avg_rating, 2),
        }
