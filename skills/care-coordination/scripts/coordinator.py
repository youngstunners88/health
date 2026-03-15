"""
Care coordination between providers, specialists, and services.
Manages care teams and care transition notifications.
"""

from datetime import datetime, timezone


CARE_TEAM_ROLES = {
    "primary_care": {
        "title": "Primary Care Provider",
        "responsibilities": [
            "Overall care management",
            "Follow-up coordination",
            "Medication management",
        ],
    },
    "cardiology": {
        "title": "Cardiologist",
        "responsibilities": [
            "Heart failure management",
            "Echocardiogram scheduling",
            "Medication titration",
        ],
    },
    "endocrinology": {
        "title": "Endocrinologist",
        "responsibilities": [
            "Diabetes management",
            "Insulin adjustment",
            "Lab monitoring",
        ],
    },
    "pulmonology": {
        "title": "Pulmonologist",
        "responsibilities": [
            "COPD/asthma management",
            "Pulmonary function testing",
            "Oxygen therapy",
        ],
    },
    "home_health": {
        "title": "Home Health Nurse",
        "responsibilities": [
            "Vital sign monitoring",
            "Medication administration",
            "Wound care",
        ],
    },
    "social_work": {
        "title": "Social Worker",
        "responsibilities": [
            "Resource coordination",
            "Financial assistance",
            "Caregiver support",
        ],
    },
    "pharmacy": {
        "title": "Clinical Pharmacist",
        "responsibilities": [
            "Medication reconciliation",
            "Drug interaction review",
            "Patient education",
        ],
    },
    "physical_therapy": {
        "title": "Physical Therapist",
        "responsibilities": [
            "Mobility assessment",
            "Exercise program",
            "Fall prevention",
        ],
    },
}


class CareCoordinator:
    """Coordinates care between multiple providers and services."""

    def assemble_care_team(
        self,
        patient_id: str,
        primary_care_provider: str,
        specialists: list[str] | None = None,
        home_health: bool = False,
        social_work: bool = False,
        pharmacy: bool = False,
        physical_therapy: bool = False,
    ) -> dict:
        team = {
            "patient_id": patient_id,
            "members": [
                {
                    "role": "primary_care",
                    "title": CARE_TEAM_ROLES["primary_care"]["title"],
                    "name": primary_care_provider,
                    "responsibilities": CARE_TEAM_ROLES["primary_care"][
                        "responsibilities"
                    ],
                }
            ],
            "assembled_at": datetime.now(timezone.utc).isoformat(),
        }

        for spec in specialists or []:
            key = spec.lower().replace(" ", "_")
            if key in CARE_TEAM_ROLES:
                team["members"].append(
                    {
                        "role": key,
                        "title": CARE_TEAM_ROLES[key]["title"],
                        "name": f"{spec} Team",
                        "responsibilities": CARE_TEAM_ROLES[key]["responsibilities"],
                    }
                )

        if home_health:
            team["members"].append(
                {
                    "role": "home_health",
                    "title": CARE_TEAM_ROLES["home_health"]["title"],
                    "name": "Home Health Agency",
                    "responsibilities": CARE_TEAM_ROLES["home_health"][
                        "responsibilities"
                    ],
                }
            )
        if social_work:
            team["members"].append(
                {
                    "role": "social_work",
                    "title": CARE_TEAM_ROLES["social_work"]["title"],
                    "name": "Social Services",
                    "responsibilities": CARE_TEAM_ROLES["social_work"][
                        "responsibilities"
                    ],
                }
            )
        if pharmacy:
            team["members"].append(
                {
                    "role": "pharmacy",
                    "title": CARE_TEAM_ROLES["pharmacy"]["title"],
                    "name": "Clinical Pharmacy",
                    "responsibilities": CARE_TEAM_ROLES["pharmacy"]["responsibilities"],
                }
            )
        if physical_therapy:
            team["members"].append(
                {
                    "role": "physical_therapy",
                    "title": CARE_TEAM_ROLES["physical_therapy"]["title"],
                    "name": "Physical Therapy",
                    "responsibilities": CARE_TEAM_ROLES["physical_therapy"][
                        "responsibilities"
                    ],
                }
            )

        return team

    def notify_care_transition(
        self,
        patient_id: str,
        from_location: str,
        to_location: str,
        discharge_summary: str,
        care_team: dict,
    ) -> dict:
        notifications = []
        for member in care_team.get("members", []):
            notifications.append(
                {
                    "recipient": member["name"],
                    "role": member["title"],
                    "type": "care_transition",
                    "from": from_location,
                    "to": to_location,
                    "patient_id": patient_id,
                    "summary": discharge_summary[:200],
                    "action_required": member["responsibilities"][0],
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        return {
            "patient_id": patient_id,
            "transition": f"{from_location} -> {to_location}",
            "notifications_sent": len(notifications),
            "notifications": notifications,
            "discharge_summary": discharge_summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_care_team_for_condition(self, condition: str) -> list[str]:
        """Return recommended care team roles for a given condition."""
        condition_roles = {
            "chf": ["primary_care", "cardiology", "pharmacy", "home_health"],
            "copd": ["primary_care", "pulmonology", "pharmacy", "home_health"],
            "diabetes": ["primary_care", "endocrinology", "pharmacy"],
            "hip replacement": ["primary_care", "physical_therapy", "home_health"],
            "pneumonia": ["primary_care", "pulmonology"],
        }
        return condition_roles.get(condition.lower(), ["primary_care"])
