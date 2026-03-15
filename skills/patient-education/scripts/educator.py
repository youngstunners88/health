"""
Patient education material generation.
Creates condition-specific and medication-specific educational content.
"""

from datetime import datetime, timezone


CONDITION_MATERIALS = {
    "chf": {
        "title": "Understanding Heart Failure",
        "what_is": "Heart failure means your heart is not pumping blood as well as it should. It does not mean your heart has stopped. With proper treatment, most people with heart failure can live active lives.",
        "causes": "Common causes include high blood pressure, coronary artery disease, heart valve problems, and previous heart attacks.",
        "symptoms": "Shortness of breath, fatigue, swelling in legs and ankles, rapid weight gain, persistent cough.",
        "self_care": [
            "Weigh yourself every morning before eating",
            "Take your medications exactly as prescribed",
            "Limit salt to less than 2,000 mg per day",
            "Limit fluids to 2 liters (about 8 cups) per day",
            "Stay as active as your doctor allows",
            "Quit smoking if you smoke",
            "Limit or avoid alcohol",
        ],
        "when_to_call": "Call your doctor if you gain more than 2-3 pounds in a day or 5 pounds in a week, have increased shortness of breath, or notice more swelling.",
    },
    "diabetes": {
        "title": "Managing Your Diabetes",
        "what_is": "Diabetes means your blood sugar (glucose) is too high. Your body either does not make enough insulin or cannot use insulin properly. Insulin helps sugar enter your cells for energy.",
        "causes": "Type 2 diabetes is caused by a combination of genetics and lifestyle factors including weight, diet, and physical activity.",
        "symptoms": "Increased thirst, frequent urination, hunger, fatigue, blurred vision, slow-healing cuts.",
        "self_care": [
            "Check your blood sugar as directed by your doctor",
            "Take your medications as prescribed",
            "Follow a balanced meal plan with controlled carbohydrates",
            "Exercise regularly (aim for 30 minutes most days)",
            "Check your feet daily for cuts, blisters, or sores",
            "Keep all medical appointments",
        ],
        "when_to_call": "Call your doctor if your blood sugar is consistently above 250 or below 70, or if you have signs of infection.",
    },
    "copd": {
        "title": "Living with COPD",
        "what_is": "COPD (Chronic Obstructive Pulmonary Disease) is a lung disease that makes it hard to breathe. It includes emphysema and chronic bronchitis.",
        "causes": "The most common cause is smoking. Long-term exposure to air pollution, chemical fumes, or dust can also contribute.",
        "symptoms": "Shortness of breath, chronic cough with mucus, wheezing, chest tightness, frequent respiratory infections.",
        "self_care": [
            "Take your medications as prescribed, including inhalers",
            "Quit smoking and avoid secondhand smoke",
            "Practice breathing exercises daily",
            "Stay active with gentle exercise as tolerated",
            "Get flu and pneumonia vaccines",
            "Avoid cold air and respiratory irritants",
        ],
        "when_to_call": "Call your doctor if you have increased difficulty breathing, a change in mucus color, fever, or chest pain.",
    },
}

MEDICATION_GUIDES = {
    "lisinopril": {
        "generic": "Lisinopril",
        "class": "ACE Inhibitor",
        "what_it_does": "Lowers blood pressure and reduces strain on the heart by relaxing blood vessels.",
        "how_to_take": "Take once daily at the same time each day. Can be taken with or without food.",
        "side_effects": "Dizziness, dry cough, headache, tiredness. Call your doctor if you have swelling of face/lips, difficulty breathing, or severe dizziness.",
        "warnings": "Do not use if pregnant. Tell your doctor about all other medications, especially potassium supplements or diuretics.",
    },
    "metformin": {
        "generic": "Metformin",
        "class": "Biguanide",
        "what_it_does": "Lowers blood sugar by decreasing glucose production in the liver and improving insulin sensitivity.",
        "how_to_take": "Take with meals to reduce stomach upset. Usually taken twice daily.",
        "side_effects": "Nausea, diarrhea, stomach upset (usually improves over time). Call your doctor if you have unusual muscle pain, trouble breathing, or feeling very weak.",
        "warnings": "Tell your doctor before any imaging tests with contrast dye. Limit alcohol intake.",
    },
    "furosemide": {
        "generic": "Furosemide (Lasix)",
        "class": "Loop Diuretic (Water Pill)",
        "what_it_does": "Helps your body remove excess fluid by increasing urination. Reduces swelling and lowers blood pressure.",
        "how_to_take": "Take in the morning to avoid nighttime urination. Take with food if it upsets your stomach.",
        "side_effects": "Frequent urination, dizziness, dehydration, low potassium. Call your doctor if you have severe dizziness, muscle cramps, or irregular heartbeat.",
        "warnings": "Drink fluids as directed by your doctor. You may need potassium supplements. Avoid excessive sun exposure.",
    },
    "atorvastatin": {
        "generic": "Atorvastatin (Lipitor)",
        "class": "Statin",
        "what_it_does": "Lowers cholesterol and reduces the risk of heart attack and stroke.",
        "how_to_take": "Take once daily, with or without food. Can be taken at any time of day but be consistent.",
        "side_effects": "Muscle pain, diarrhea, nausea. Call your doctor immediately if you have unexplained muscle pain, tenderness, or weakness.",
        "warnings": "Avoid grapefruit juice. Tell your doctor about all medications. Do not use if pregnant.",
    },
}


class PatientEducator:
    """Generates patient-friendly educational materials."""

    def generate_condition_material(
        self,
        condition: str,
        reading_level: str = "8th_grade",
        language: str = "en",
    ) -> dict:
        key = condition.lower().replace(" ", "_")
        material = CONDITION_MATERIALS.get(key)
        if not material:
            return {
                "condition": condition,
                "title": f"Understanding {condition}",
                "message": "Educational material not available in library. Please consult your care team.",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        return {
            **material,
            "condition": condition,
            "reading_level": reading_level,
            "language": language,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_medication_guide(
        self,
        medication: str,
        dose: str = "",
        frequency: str = "",
        reading_level: str = "8th_grade",
    ) -> dict:
        key = medication.lower()
        guide = MEDICATION_GUIDES.get(key)
        if not guide:
            return {
                "medication": medication,
                "message": "Medication guide not available in library. Please consult your pharmacist.",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        return {
            **guide,
            "prescribed_dose": dose,
            "prescribed_frequency": frequency,
            "reading_level": reading_level,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_discharge_instructions(
        self,
        patient_name: str,
        conditions: list[str],
        medications: list[dict],
        followups: list[dict],
        warning_signs: list[str],
        reading_level: str = "8th_grade",
    ) -> dict:
        instructions = {
            "patient_name": patient_name,
            "reading_level": reading_level,
            "sections": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        for condition in conditions:
            material = self.generate_condition_material(condition, reading_level)
            if "what_is" in material:
                instructions["sections"].append(
                    {
                        "type": "condition",
                        "title": material["title"],
                        "content": material,
                    }
                )

        for med in medications:
            guide = self.generate_medication_guide(
                med["name"], med.get("dose", ""), med.get("frequency", "")
            )
            if "what_it_does" in guide:
                instructions["sections"].append(
                    {
                        "type": "medication",
                        "title": f"Your Medication: {med['name']}",
                        "content": guide,
                    }
                )

        if followups:
            instructions["sections"].append(
                {
                    "type": "followups",
                    "title": "Your Upcoming Appointments",
                    "appointments": followups,
                }
            )

        if warning_signs:
            instructions["sections"].append(
                {
                    "type": "warnings",
                    "title": "Warning Signs - When to Call Your Doctor",
                    "signs": warning_signs,
                }
            )

        return instructions
