"""
FHIR client for EHR integration.
Supports FHIR R4 resources with OAuth2 authentication.
"""

import os
import requests
from datetime import datetime, timezone


class FHIRClient:
    """Client for interacting with FHIR R4 compliant EHR servers."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.environ.get(
            "FHIR_SERVER_URL", "https://hapi.fhir.org/baseR4"
        )
        self.client_id = os.environ.get("FHIR_CLIENT_ID")
        self.client_secret = os.environ.get("FHIR_CLIENT_SECRET")
        self._token = None
        self._session = requests.Session()

    def _auth_headers(self) -> dict:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        if self.client_id and self.client_secret:
            self._request_token()
            if self._token:
                return {"Authorization": f"Bearer {self._token}"}
        return {}

    def _request_token(self):
        """Request OAuth2 bearer token from the FHIR server."""
        token_url = f"{self.base_url}/token"
        try:
            resp = self._session.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
            resp.raise_for_status()
            self._token = resp.json().get("access_token")
        except requests.RequestException:
            self._token = None

    def _search(self, resource_type: str, params: dict | None = None) -> list[dict]:
        url = f"{self.base_url}/{resource_type}"
        headers = self._auth_headers()
        search_params = params or {}
        try:
            resp = self._session.get(
                url, headers=headers, params=search_params, timeout=30
            )
            resp.raise_for_status()
            bundle = resp.json()
            return [entry["resource"] for entry in bundle.get("entry", [])]
        except requests.RequestException as e:
            return [{"error": str(e), "resource_type": resource_type}]

    def get_patient_record(self, patient_id: str) -> dict:
        """Retrieve a comprehensive patient record."""
        return {
            "patient": self._get_resource("Patient", patient_id),
            "conditions": self.get_conditions(patient_id),
            "medications": self.get_medications(patient_id),
            "allergies": self.get_allergies(patient_id),
            "observations": self.get_observations(patient_id),
            "encounters": self.get_encounters(patient_id),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_resource(self, resource_type: str, resource_id: str) -> dict:
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        headers = self._auth_headers()
        try:
            resp = self._session.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e), "id": resource_id}

    def get_conditions(self, patient_id: str) -> list[dict]:
        return self._search("Condition", {"patient": patient_id, "_sort": "-date"})

    def get_medications(self, patient_id: str) -> list[dict]:
        return self._search(
            "MedicationRequest", {"patient": patient_id, "status": "active"}
        )

    def get_allergies(self, patient_id: str) -> list[dict]:
        return self._search("AllergyIntolerance", {"patient": patient_id})

    def get_observations(self, patient_id: str, code: str | None = None) -> list[dict]:
        params = {"patient": patient_id, "_sort": "-date"}
        if code:
            params["code"] = code
        return self._search("Observation", params)

    def get_encounters(self, patient_id: str) -> list[dict]:
        return self._search("Encounter", {"patient": patient_id, "_sort": "-date"})
