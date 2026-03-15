"""
Clinical risk scoring for readmission prediction.
Supports LACE index, HOSPITAL score, and heuristic ML-based assessment.
"""

from datetime import datetime, timezone


# LACE Index scoring tables
LACE_LENGTH_OF_STAY = lambda days: min(days, 5)

LACE_ACUITY = {
    "elective": 0,
    "urgent": 1,
    "emergency": 3,
}

LACE_COMORBIDITY_WEIGHTS = {
    "CHF": 1,
    "MI": 1,
    "PVD": 1,
    "CVD": 1,
    "dementia": 1,
    "COPD": 1,
    "rheumatic": 1,
    "ulcer": 1,
    "mild_liver": 1,
    "diabetes": 1,
    "hemiplegia": 2,
    "moderate_severe_renal": 2,
    "diabetes_end_organ": 2,
    "tumor": 2,
    "leukemia": 2,
    "lymphoma": 2,
    "moderate_severe_liver": 3,
    "metastatic": 6,
    "AIDS": 6,
}

LACE_ED_VISITS = lambda visits: min(visits, 4)


def _lace_score(params: dict) -> tuple[int, float, str, list[str]]:
    los = LACE_LENGTH_OF_STAY(params.get("length_of_stay_days", 0))
    acuity = LACE_ACUITY.get(params.get("admission_acuity", "elective"), 0)
    comorbidities = params.get("comorbidities", [])
    comorbidity_score = sum(
        LACE_COMORBIDITY_WEIGHTS.get(c.lower().replace(" ", "_"), 1)
        for c in comorbidities
    )
    ed = LACE_ED_VISITS(params.get("ed_visits_last_6mo", 0))

    total = los + acuity + comorbidity_score + ed

    if total <= 4:
        risk, level = 0.05, "low"
    elif total <= 9:
        risk, level = 0.15, "moderate"
    elif total <= 14:
        risk, level = 0.25, "high"
    else:
        risk, level = 0.40, "very_high"

    factors = []
    if los >= 4:
        factors.append(
            f"Extended hospital stay ({params.get('length_of_stay_days')} days)"
        )
    if acuity >= 3:
        factors.append("Emergency admission increases readmission risk")
    if comorbidity_score >= 3:
        factors.append(f"Significant comorbidity burden ({comorbidity_score} points)")
    if ed >= 2:
        factors.append(
            f"Frequent ED use ({params.get('ed_visits_last_6mo')} visits in 6 months)"
        )
    if any(c.upper() in ["CHF", "COPD", "DIABETES"] for c in comorbidities):
        factors.append("High-risk chronic condition present")

    recommendations = []
    if level in ("high", "very_high"):
        recommendations.extend(
            [
                "Schedule follow-up within 48-72 hours",
                "Assign care coordinator for transition management",
                "Conduct medication reconciliation before discharge",
                "Arrange home health services if applicable",
            ]
        )
    if level == "moderate":
        recommendations.extend(
            [
                "Schedule follow-up within 7 days",
                "Provide detailed discharge instructions",
            ]
        )

    return total, risk, level, factors, recommendations


def _hospital_score(params: dict) -> tuple[int, float, str, list[str]]:
    h_map = {"low": 3, "high": 0}
    h = h_map.get(params.get("h", "high"), 0)
    o = 3 if params.get("o", False) else 0
    s = min(params.get("s", 0), 75) // 25
    p = min(params.get("p", 0), 2)
    i_map = {"none": 0, "medical": 1, "emergency": 2}
    i = i_map.get(params.get("i", "none"), 0)
    t = 5 if params.get("t", 0) == 5 else 0
    a = min(params.get("a", 0), 3)
    l = min(params.get("l", 0), 5)

    total = h + o + s + p + i + t + a + l

    if total <= 4:
        risk, level = 0.05, "low"
    elif total <= 8:
        risk, level = 0.12, "moderate"
    else:
        risk, level = 0.25, "high"

    factors = []
    if o:
        factors.append("Active oncology treatment increases readmission risk")
    if a >= 2:
        factors.append(f"Multiple recent admissions ({params.get('a')})")
    if t == 5:
        factors.append("Emergency admission")

    recommendations = []
    if level == "high":
        recommendations.extend(
            [
                "Intensive discharge planning required",
                "Oncology/social work consult if applicable",
                "Early follow-up appointment scheduling",
            ]
        )

    return total, risk, level, factors, recommendations


def calculate_risk(
    patient_id: str,
    method: str = "lace",
    params: dict | None = None,
) -> dict:
    """
    Calculate readmission risk using the specified method.

    Args:
        patient_id: Unique patient identifier
        method: Scoring method - 'lace', 'hospital', or 'ml'
        params: Method-specific parameters

    Returns:
        Dict with score, risk level, contributing factors, and recommendations
    """
    params = params or {}

    if method == "lace":
        score, risk, level, factors, recs = _lace_score(params)
    elif method == "hospital":
        score, risk, level, factors, recs = _hospital_score(params)
    elif method == "ml":
        # Heuristic fallback when no trained model is available
        # In production, replace with actual ML model inference
        comorbidities = params.get("comorbidities", [])
        age = params.get("age", 50)
        prior_admissions = params.get("prior_admissions_12mo", 0)

        base_risk = 0.1
        if "chf" in [c.lower() for c in comorbidities]:
            base_risk += 0.2
        if "copd" in [c.lower() for c in comorbidities]:
            base_risk += 0.15
        if age > 65:
            base_risk += 0.1
        if age > 80:
            base_risk += 0.1
        base_risk += prior_admissions * 0.05
        risk = min(base_risk, 0.85)

        if risk < 0.15:
            level = "low"
        elif risk < 0.25:
            level = "moderate"
        elif risk < 0.4:
            level = "high"
        else:
            level = "very_high"

        score = int(risk * 20)
        factors = [
            f"Age {age}",
            f"{len(comorbidities)} comorbidities",
            f"{prior_admissions} prior admissions",
        ]
        recs = (
            ["Consider enhanced discharge protocol"]
            if level in ("high", "very_high")
            else []
        )
    else:
        raise ValueError(f"Unknown risk scoring method: {method}")

    return {
        "patient_id": patient_id,
        "method": method,
        "score": score,
        "risk": round(risk, 2),
        "level": level,
        "factors": factors,
        "recommendations": recs,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
