"""Clinical Trials Matching Engine.

Matches patients to clinical trials based on EHR data including diagnoses,
age, medications, comorbidities, and prior treatments.
"""

import logging
import json
import os
from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# ICD-10 code mappings for conditions
ICD10_CONDITION_MAP = {
    "I50": "CHF",
    "I50.0": "CHF",
    "I50.1": "CHF",
    "I50.9": "CHF",
    "E11": "diabetes",
    "E11.9": "diabetes",
    "E11.65": "diabetes",
    "E10": "diabetes",
    "E10.9": "diabetes",
    "J44": "COPD",
    "J44.0": "COPD",
    "J44.1": "COPD",
    "J44.9": "COPD",
    "C34": "lung cancer",
    "C50": "breast cancer",
    "C61": "prostate cancer",
    "C18": "colorectal cancer",
    "C18.9": "colorectal cancer",
    "G30": "Alzheimer's",
    "G30.0": "Alzheimer's",
    "G30.1": "Alzheimer's",
    "G30.9": "Alzheimer's",
    "I10": "hypertension",
    "I11": "hypertension",
    "I11.0": "hypertension",
    "I11.9": "hypertension",
    "E66": "obesity",
    "E66.0": "obesity",
    "E66.01": "obesity",
    "E66.9": "obesity",
    "F32": "depression",
    "F32.0": "depression",
    "F32.1": "depression",
    "F32.9": "depression",
    "F33": "depression",
    "F33.0": "depression",
    "F33.1": "depression",
    "F33.9": "depression",
}

MEDICATION_TO_CONDITION = {
    "metformin": "diabetes",
    "insulin": "diabetes",
    "glipizide": "diabetes",
    "sitagliptin": "diabetes",
    "lisinopril": "hypertension",
    "amlodipine": "hypertension",
    "losartan": "hypertension",
    "hydrochlorothiazide": "hypertension",
    "furosemide": "CHF",
    "carvedilol": "CHF",
    "enalapril": "CHF",
    "spironolactone": "CHF",
    "albuterol": "COPD",
    "tiotropium": "COPD",
    "budesonide": "COPD",
    "ipratropium": "COPD",
    "donepezil": "Alzheimer's",
    "memantine": "Alzheimer's",
    "rivastigmine": "Alzheimer's",
    "sertraline": "depression",
    "fluoxetine": "depression",
    "escitalopram": "depression",
    "venlafaxine": "depression",
    "duloxetine": "depression",
    "semaglutide": "obesity",
    "liraglutide": "obesity",
    "orlistat": "obesity",
    "tamoxifen": "breast cancer",
    "paclitaxel": "breast cancer",
    "cisplatin": "lung cancer",
    "pembrolizumab": "lung cancer",
}


@dataclass
class ClinicalTrial:
    """Represents a clinical trial."""

    trial_id: str
    title: str
    condition: str
    icd10_codes: list
    phase: str
    sponsor: str
    status: str
    locations: list
    min_age: int
    max_age: int
    gender: str
    inclusion_criteria: list
    exclusion_criteria: list
    required_medications: list = field(default_factory=list)
    excluded_medications: list = field(default_factory=list)
    required_prior_treatments: list = field(default_factory=list)
    excluded_comorbidities: list = field(default_factory=list)
    required_comorbidities: list = field(default_factory=list)
    bmi_min: Optional[float] = None
    bmi_max: Optional[float] = None
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    enrollment_target: int = 0
    enrollment_current: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MatchResult:
    """Result of matching a patient to a trial."""

    trial_id: str
    trial_title: str
    eligibility_score: float
    eligible: bool
    reasons_matched: list
    reasons_excluded: list
    missing_criteria: list

    def to_dict(self) -> dict:
        return asdict(self)


class ClinicalTrialsEngine:
    """Engine for matching patients to clinical trials."""

    DATA_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "trials.json"
    )

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or self.DATA_FILE
        self.trials: dict[str, ClinicalTrial] = {}
        self._match_history: list[dict] = []
        self._load_or_initialize_trials()
        logger.info("ClinicalTrialsEngine initialized with %d trials", len(self.trials))

    def _load_or_initialize_trials(self):
        """Load trials from persistent storage or initialize with sample data."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                for t in data:
                    trial = ClinicalTrial(**t)
                    self.trials[trial.trial_id] = trial
                logger.info(
                    "Loaded %d trials from %s", len(self.trials), self.data_file
                )
                return
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Failed to load trials from %s: %s", self.data_file, e)

        self._initialize_sample_trials()
        self._persist_trials()

    def _persist_trials(self):
        """Persist trials to disk."""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        data = [t.to_dict() for t in self.trials.values()]
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Persisted %d trials to %s", len(self.trials), self.data_file)

    def _initialize_sample_trials(self):
        """Initialize 24 sample clinical trials across 8 conditions."""
        sample_trials = [
            # CHF Trials (3)
            ClinicalTrial(
                trial_id="CHF-001",
                title="Novel SGLT2 Inhibitor for Chronic Heart Failure",
                condition="CHF",
                icd10_codes=["I50", "I50.0", "I50.1", "I50.9"],
                phase="Phase 3",
                sponsor="CardioVax Therapeutics",
                status="Recruiting",
                locations=["New York, NY", "Boston, MA", "Chicago, IL"],
                min_age=40,
                max_age=85,
                gender="All",
                inclusion_criteria=[
                    "Diagnosis of chronic heart failure (NYHA Class II-IV)",
                    "LVEF <= 40%",
                    "On stable guideline-directed medical therapy for >= 4 weeks",
                    "NT-proBNP >= 600 pg/mL",
                ],
                exclusion_criteria=[
                    "Acute decompensated heart failure requiring hospitalization within 30 days",
                    "Type 1 diabetes",
                    "eGFR < 25 mL/min/1.73m2",
                    "History of diabetic ketoacidosis",
                ],
                required_prior_treatments=["ACE inhibitor", "beta-blocker"],
                excluded_comorbidities=["type 1 diabetes"],
                description="Evaluating efficacy and safety of a novel SGLT2 inhibitor in reducing cardiovascular death and heart failure hospitalization.",
                start_date="2025-01-15",
                end_date="2027-06-30",
                enrollment_target=3500,
                enrollment_current=2100,
            ),
            ClinicalTrial(
                trial_id="CHF-002",
                title="Gene Therapy for Advanced Heart Failure",
                condition="CHF",
                icd10_codes=["I50", "I50.9"],
                phase="Phase 2",
                sponsor="HeartGene Bio",
                status="Recruiting",
                locations=["San Francisco, CA", "Houston, TX"],
                min_age=30,
                max_age=75,
                gender="All",
                inclusion_criteria=[
                    "Ischemic or non-ischemic cardiomyopathy",
                    "LVEF <= 35%",
                    "6-minute walk distance 150-450 meters",
                ],
                exclusion_criteria=[
                    "Prior cardiac transplant",
                    "LVAD in place",
                    "Active myocarditis",
                    "BMI > 40",
                ],
                bmi_max=40.0,
                description="Single-dose gene therapy targeting SERCA2a to improve cardiac function in advanced heart failure.",
                start_date="2025-03-01",
                end_date="2027-12-31",
                enrollment_target=200,
                enrollment_current=85,
            ),
            ClinicalTrial(
                trial_id="CHF-003",
                title="Remote Monitoring Device for CHF Management",
                condition="CHF",
                icd10_codes=["I50", "I50.1"],
                phase="Phase 4",
                sponsor="MedTech Innovations",
                status="Recruiting",
                locations=["Seattle, WA", "Denver, CO", "Atlanta, GA", "Miami, FL"],
                min_age=50,
                max_age=90,
                gender="All",
                inclusion_criteria=[
                    "CHF diagnosis within past 2 years",
                    "At least 1 HF hospitalization in past 12 months",
                    "Ability to use smartphone application",
                ],
                exclusion_criteria=[
                    "End-stage renal disease on dialysis",
                    "Life expectancy < 1 year",
                    "Cognitive impairment preventing device use",
                ],
                excluded_comorbidities=["end-stage renal disease"],
                description="Real-world evaluation of implantable hemodynamic monitor for reducing HF readmissions.",
                start_date="2024-09-01",
                end_date="2026-08-31",
                enrollment_target=1200,
                enrollment_current=890,
            ),
            # Diabetes Trials (3)
            ClinicalTrial(
                trial_id="DM-001",
                title="Dual GIP/GLP-1 Receptor Agonist for Type 2 Diabetes",
                condition="diabetes",
                icd10_codes=["E11", "E11.9", "E11.65"],
                phase="Phase 3",
                sponsor="EliVance Pharmaceuticals",
                status="Recruiting",
                locations=["Nashville, TN", "Dallas, TX", "Phoenix, AZ"],
                min_age=18,
                max_age=75,
                gender="All",
                inclusion_criteria=[
                    "Type 2 diabetes diagnosis >= 6 months",
                    "HbA1c 7.0-10.5% on stable metformin monotherapy",
                    "BMI >= 25 kg/m2",
                ],
                exclusion_criteria=[
                    "Type 1 diabetes",
                    "History of pancreatitis",
                    "Personal/family history of medullary thyroid carcinoma",
                    "eGFR < 30 mL/min/1.73m2",
                ],
                required_medications=["metformin"],
                required_comorbidities=["obesity"],
                bmi_min=25.0,
                description="Assessing glycemic control and weight loss with dual incretin receptor agonist vs placebo.",
                start_date="2025-02-01",
                end_date="2027-09-30",
                enrollment_target=2800,
                enrollment_current=1650,
            ),
            ClinicalTrial(
                trial_id="DM-002",
                title="Closed-Loop Insulin Delivery System",
                condition="diabetes",
                icd10_codes=["E10", "E10.9", "E11", "E11.9"],
                phase="Phase 4",
                sponsor="AutoDiabetes Systems",
                status="Recruiting",
                locations=["Portland, OR", "Minneapolis, MN"],
                min_age=14,
                max_age=70,
                gender="All",
                inclusion_criteria=[
                    "Type 1 or Type 2 diabetes on insulin therapy",
                    "HbA1c >= 7.5%",
                    "Using insulin pump or multiple daily injections",
                ],
                exclusion_criteria=[
                    "Hypoglycemia unawareness",
                    "Pregnancy or planning pregnancy",
                    "Untreated thyroid disorder",
                ],
                required_medications=["insulin"],
                description="Fully automated closed-loop insulin delivery system for improved glycemic control.",
                start_date="2024-11-01",
                end_date="2026-12-31",
                enrollment_target=500,
                enrollment_current=340,
            ),
            ClinicalTrial(
                trial_id="DM-003",
                title="Stem Cell-Derived Beta Cell Replacement Therapy",
                condition="diabetes",
                icd10_codes=["E10", "E10.9"],
                phase="Phase 1/2",
                sponsor="RegenBeta Therapeutics",
                status="Recruiting",
                locations=["San Diego, CA"],
                min_age=18,
                max_age=55,
                gender="All",
                inclusion_criteria=[
                    "Type 1 diabetes diagnosis >= 5 years",
                    "History of severe hypoglycemia (>= 2 episodes in past year)",
                    "HbA1c >= 7.0%",
                    "C-peptide < 0.4 ng/mL",
                ],
                exclusion_criteria=[
                    "Prior islet or pancreas transplant",
                    "Active autoimmune disease other than T1D",
                    "Immunosuppression contraindication",
                ],
                required_prior_treatments=["insulin"],
                description="Transplantation of stem cell-derived pancreatic beta cells for Type 1 diabetes.",
                start_date="2025-06-01",
                end_date="2029-12-31",
                enrollment_target=40,
                enrollment_current=12,
            ),
            # COPD Trials (3)
            ClinicalTrial(
                trial_id="COPD-001",
                title="Triple Inhaled Therapy for Severe COPD",
                condition="COPD",
                icd10_codes=["J44", "J44.0", "J44.1", "J44.9"],
                phase="Phase 3",
                sponsor="RespiraPharm",
                status="Recruiting",
                locations=["Baltimore, MD", "Cleveland, OH", "Detroit, MI"],
                min_age=40,
                max_age=80,
                gender="All",
                inclusion_criteria=[
                    "COPD diagnosis (GOLD Stage 2-4)",
                    "FEV1 < 60% predicted",
                    "History of >= 1 exacerbation in past year",
                    "Current or former smoker (>= 10 pack-years)",
                ],
                exclusion_criteria=[
                    "Asthma diagnosis",
                    "Pneumonia within past 3 months",
                    "Lung cancer or other malignancy",
                    "Alpha-1 antitrypsin deficiency",
                ],
                excluded_comorbidities=["asthma", "lung cancer"],
                required_prior_treatments=["bronchodilator"],
                description="Comparing triple ICS/LABA/LAMA therapy vs dual therapy in reducing COPD exacerbations.",
                start_date="2025-01-01",
                end_date="2027-03-31",
                enrollment_target=4200,
                enrollment_current=2800,
            ),
            ClinicalTrial(
                trial_id="COPD-002",
                title="Bronchoscopic Lung Volume Reduction for Emphysema",
                condition="COPD",
                icd10_codes=["J44", "J44.1"],
                phase="Phase 4",
                sponsor="PulmoTech Medical",
                status="Recruiting",
                locations=["Los Angeles, CA", "Philadelphia, PA"],
                min_age=45,
                max_age=75,
                gender="All",
                inclusion_criteria=[
                    "Severe emphysema with hyperinflation",
                    "FEV1 15-45% predicted",
                    "RV >= 175% predicted",
                    "6-minute walk distance >= 150 meters",
                ],
                exclusion_criteria=[
                    "FEV1 < 15% predicted",
                    "PaCO2 > 50 mmHg",
                    "Active smoking",
                    "Pulmonary hypertension",
                ],
                description="Endobronchial valve placement for lung volume reduction in severe emphysema.",
                start_date="2024-06-01",
                end_date="2026-12-31",
                enrollment_target=300,
                enrollment_current=210,
            ),
            ClinicalTrial(
                trial_id="COPD-003",
                title="Anti-IL-5 Biologic for Eosinophilic COPD",
                condition="COPD",
                icd10_codes=["J44", "J44.0"],
                phase="Phase 2",
                sponsor="BioAir Therapeutics",
                status="Recruiting",
                locations=["Rochester, MN", "Ann Arbor, MI"],
                min_age=40,
                max_age=75,
                gender="All",
                inclusion_criteria=[
                    "Moderate to severe COPD",
                    "Blood eosinophil count >= 300 cells/mcL",
                    "History of >= 2 exacerbations in past year",
                ],
                exclusion_criteria=[
                    "Current asthma diagnosis",
                    "Parasitic infection",
                    "Immunodeficiency",
                    "Systemic corticosteroid use > 10mg/day prednisone equivalent",
                ],
                excluded_comorbidities=["asthma"],
                description="Targeting eosinophilic inflammation in COPD with anti-IL-5 monoclonal antibody.",
                start_date="2025-04-01",
                end_date="2027-12-31",
                enrollment_target=600,
                enrollment_current=180,
            ),
            # Cancer Trials (4)
            ClinicalTrial(
                trial_id="CAN-001",
                title="CAR-T Cell Therapy for Refractory Lung Cancer",
                condition="lung cancer",
                icd10_codes=["C34"],
                phase="Phase 1/2",
                sponsor="OncoCell Therapeutics",
                status="Recruiting",
                locations=["Houston, TX", "New York, NY", "Los Angeles, CA"],
                min_age=18,
                max_age=75,
                gender="All",
                inclusion_criteria=[
                    "Stage IIIB/IV non-small cell lung cancer",
                    "Progressed on >= 2 prior lines of therapy",
                    "Measurable disease per RECIST 1.1",
                    "ECOG performance status 0-1",
                ],
                exclusion_criteria=[
                    "Active brain metastases",
                    "Autoimmune disease requiring systemic treatment",
                    "Uncontrolled intercurrent illness",
                    "Prior CAR-T therapy",
                ],
                required_prior_treatments=["chemotherapy", "immunotherapy"],
                excluded_comorbidities=["autoimmune disease"],
                description="Autologous CAR-T cells targeting mesothelin in advanced NSCLC.",
                start_date="2025-03-15",
                end_date="2028-12-31",
                enrollment_target=80,
                enrollment_current=25,
            ),
            ClinicalTrial(
                trial_id="CAN-002",
                title="Antibody-Drug Conjugate for HER2-Low Breast Cancer",
                condition="breast cancer",
                icd10_codes=["C50"],
                phase="Phase 3",
                sponsor="OncoTarget Pharma",
                status="Recruiting",
                locations=["Boston, MA", "Seattle, WA", "Atlanta, GA"],
                min_age=18,
                max_age=80,
                gender="Female",
                inclusion_criteria=[
                    "Unresectable or metastatic breast cancer",
                    "HER2-low expression (IHC 1+ or 2+/ISH-)",
                    "Progressed on >= 1 prior chemotherapy in metastatic setting",
                    "ECOG 0-2",
                ],
                exclusion_criteria=[
                    "HER2-positive disease",
                    "Triple-negative breast cancer",
                    "Active brain metastases requiring treatment",
                    "LVEF < 50%",
                    "Interstitial lung disease",
                ],
                required_prior_treatments=["chemotherapy"],
                description="Novel ADC targeting HER2-low expressing metastatic breast cancer.",
                start_date="2024-08-01",
                end_date="2027-06-30",
                enrollment_target=1500,
                enrollment_current=980,
            ),
            ClinicalTrial(
                trial_id="CAN-003",
                title="PARP Inhibitor Combination for Prostate Cancer",
                condition="prostate cancer",
                icd10_codes=["C61"],
                phase="Phase 3",
                sponsor="ProstaGene Sciences",
                status="Recruiting",
                locations=["Durham, NC", "Chicago, IL"],
                min_age=18,
                max_age=85,
                gender="Male",
                inclusion_criteria=[
                    "Metastatic castration-resistant prostate cancer",
                    "HRR gene mutation (BRCA1/2, ATM, etc.)",
                    "Progressed on abiraterone or enzalutamide",
                ],
                exclusion_criteria=[
                    "Prior PARP inhibitor therapy",
                    "Myelodysplastic syndrome or AML",
                    "Major surgery within 28 days",
                ],
                required_prior_treatments=["abiraterone", "enzalutamide"],
                description="Combining PARP inhibitor with androgen receptor pathway inhibitor in mCRPC.",
                start_date="2025-01-01",
                end_date="2028-03-31",
                enrollment_target=800,
                enrollment_current=420,
            ),
            ClinicalTrial(
                trial_id="CAN-004",
                title="Immunotherapy-Chemotherapy Combo for Colorectal Cancer",
                condition="colorectal cancer",
                icd10_codes=["C18", "C18.9"],
                phase="Phase 2",
                sponsor="GastroOnc Therapeutics",
                status="Recruiting",
                locations=["San Francisco, CA", "Nashville, TN"],
                min_age=18,
                max_age=75,
                gender="All",
                inclusion_criteria=[
                    "Stage IV colorectal cancer",
                    "MSS/pMMR tumor status",
                    "No prior systemic therapy for metastatic disease",
                    "ECOG 0-1",
                ],
                exclusion_criteria=[
                    "MSI-H or dMMR tumor",
                    "BRAF V600E mutation",
                    "Active autoimmune disease",
                    "Untreated brain metastases",
                ],
                description="First-line combination of checkpoint inhibitor with standard chemotherapy in MSS colorectal cancer.",
                start_date="2025-05-01",
                end_date="2028-12-31",
                enrollment_target=400,
                enrollment_current=95,
            ),
            # Alzheimer's Trials (3)
            ClinicalTrial(
                trial_id="AD-001",
                title="Anti-Amyloid Monoclonal Antibody for Early Alzheimer's",
                condition="Alzheimer's",
                icd10_codes=["G30", "G30.0", "G30.1", "G30.9"],
                phase="Phase 3",
                sponsor="NeuroCure Biologics",
                status="Recruiting",
                locations=["Boston, MA", "Rochester, MN", "San Francisco, CA"],
                min_age=50,
                max_age=85,
                gender="All",
                inclusion_criteria=[
                    "Mild cognitive impairment or mild dementia due to AD",
                    "Positive amyloid PET scan",
                    "MMSE score 22-30",
                    "CDR-GS 0.5-1.0",
                ],
                exclusion_criteria=[
                    "Moderate to severe Alzheimer's disease",
                    "Evidence of microhemorrhages > 4 on MRI",
                    "APOE e4/e4 homozygous with prior ARIA",
                    "Other significant neurological disease",
                ],
                excluded_comorbidities=["Parkinson's", "stroke"],
                description="Subcutaneous anti-amyloid antibody for slowing cognitive decline in early AD.",
                start_date="2024-10-01",
                end_date="2027-09-30",
                enrollment_target=1800,
                enrollment_current=1200,
            ),
            ClinicalTrial(
                trial_id="AD-002",
                title="Tau-Targeting Antisense Oligonucleotide",
                condition="Alzheimer's",
                icd10_codes=["G30", "G30.9"],
                phase="Phase 1/2",
                sponsor="TauSilence Therapeutics",
                status="Recruiting",
                locations=["San Diego, CA"],
                min_age=55,
                max_age=80,
                gender="All",
                inclusion_criteria=[
                    "Mild to moderate Alzheimer's disease",
                    "MMSE 16-26",
                    "Positive tau PET scan",
                    "Stable on cholinesterase inhibitor for >= 3 months",
                ],
                exclusion_criteria=[
                    "Significant vascular lesions on MRI",
                    "Platelet count < 100,000",
                    "Severe hepatic impairment",
                ],
                required_medications=["donepezil", "memantine", "rivastigmine"],
                description="Intrathecal antisense oligonucleotide targeting tau protein production.",
                start_date="2025-07-01",
                end_date="2029-06-30",
                enrollment_target=60,
                enrollment_current=18,
            ),
            ClinicalTrial(
                trial_id="AD-003",
                title="Digital Cognitive Training for MCI/Early AD",
                condition="Alzheimer's",
                icd10_codes=["G30", "G30.0", "G30.1"],
                phase="Phase 4",
                sponsor="BrainFit Digital Health",
                status="Recruiting",
                locations=["Remote (US-wide)"],
                min_age=55,
                max_age=90,
                gender="All",
                inclusion_criteria=[
                    "Diagnosis of MCI or mild AD",
                    "MMSE >= 20",
                    "Access to tablet computer",
                    "Caregiver available for support",
                ],
                exclusion_criteria=[
                    "Moderate to severe AD",
                    "Vision or hearing impairment preventing device use",
                    "Other neurological conditions affecting cognition",
                ],
                description="Prescription digital therapeutic for cognitive training in early Alzheimer's.",
                start_date="2024-06-01",
                end_date="2026-06-30",
                enrollment_target=2000,
                enrollment_current=1450,
            ),
            # Hypertension Trials (3)
            ClinicalTrial(
                trial_id="HTN-001",
                title="Renal Denervation for Resistant Hypertension",
                condition="hypertension",
                icd10_codes=["I10", "I11", "I11.0", "I11.9"],
                phase="Phase 4",
                sponsor="RenalTech Medical",
                status="Recruiting",
                locations=["Cleveland, OH", "Minneapolis, MN", "Dallas, TX"],
                min_age=18,
                max_age=80,
                gender="All",
                inclusion_criteria=[
                    "Resistant hypertension (uncontrolled on >= 3 medications)",
                    "Office SBP >= 150 mmHg",
                    "Ambulatory SBP >= 140 mmHg",
                    "On stable antihypertensive regimen for >= 4 weeks",
                ],
                exclusion_criteria=[
                    "Secondary hypertension",
                    "eGFR < 45 mL/min/1.73m2",
                    "Renal artery stenosis",
                    "Prior renal denervation",
                ],
                required_medications=[
                    "lisinopril",
                    "amlodipine",
                    "losartan",
                    "hydrochlorothiazide",
                ],
                description="Catheter-based renal denervation for blood pressure reduction in resistant hypertension.",
                start_date="2024-09-01",
                end_date="2027-08-31",
                enrollment_target=600,
                enrollment_current=380,
            ),
            ClinicalTrial(
                trial_id="HTN-002",
                title="siRNA Therapy for Hypertension (Zilebesiran-like)",
                condition="hypertension",
                icd10_codes=["I10"],
                phase="Phase 2",
                sponsor="SilenceCardio",
                status="Recruiting",
                locations=["New York, NY", "Los Angeles, CA"],
                min_age=18,
                max_age=75,
                gender="All",
                inclusion_criteria=[
                    "Mild to moderate essential hypertension",
                    "Untreated or on 1-2 antihypertensives",
                    "Office SBP 140-175 mmHg",
                ],
                exclusion_criteria=[
                    "Severe hypertension (SBP > 180)",
                    "Secondary hypertension",
                    "Pregnancy or breastfeeding",
                    "Severe hepatic impairment",
                ],
                description="Subcutaneous siRNA targeting angiotensinogen for sustained BP reduction (6-month dosing).",
                start_date="2025-02-15",
                end_date="2027-12-31",
                enrollment_target=1000,
                enrollment_current=520,
            ),
            ClinicalTrial(
                trial_id="HTN-003",
                title="AI-Guided Hypertension Management Platform",
                condition="hypertension",
                icd10_codes=["I10", "I11"],
                phase="Phase 4",
                sponsor="SmartBP Digital",
                status="Recruiting",
                locations=["Remote (US-wide)"],
                min_age=21,
                max_age=85,
                gender="All",
                inclusion_criteria=[
                    "Diagnosed hypertension",
                    "On at least 1 antihypertensive medication",
                    "Access to smartphone",
                    "Home BP monitor available",
                ],
                exclusion_criteria=[
                    "Pregnancy",
                    "End-stage renal disease",
                    "Life expectancy < 1 year",
                ],
                description="AI-driven medication titration and lifestyle recommendations for hypertension control.",
                start_date="2025-01-01",
                end_date="2026-12-31",
                enrollment_target=5000,
                enrollment_current=3200,
            ),
            # Obesity Trials (3)
            ClinicalTrial(
                trial_id="OB-001",
                title="Oral GLP-1 Receptor Agonist for Obesity",
                condition="obesity",
                icd10_codes=["E66", "E66.0", "E66.01", "E66.9"],
                phase="Phase 3",
                sponsor="MetaWeight Pharma",
                status="Recruiting",
                locations=["Chicago, IL", "Houston, TX", "Phoenix, AZ"],
                min_age=18,
                max_age=70,
                gender="All",
                inclusion_criteria=[
                    "BMI >= 30 kg/m2, or BMI >= 27 with weight-related comorbidity",
                    "Weight stable (± 5%) for 3 months prior",
                    "Willing to follow diet and exercise program",
                ],
                exclusion_criteria=[
                    "Type 1 diabetes",
                    "History of pancreatitis",
                    "Personal/family history of MEN2 or MTC",
                    "Gallbladder disease",
                    "Pregnancy or planning pregnancy",
                ],
                bmi_min=27.0,
                description="Once-daily oral GLP-1 RA for weight management in adults with obesity.",
                start_date="2025-03-01",
                end_date="2027-12-31",
                enrollment_target=3000,
                enrollment_current=1800,
            ),
            ClinicalTrial(
                trial_id="OB-002",
                title="Combination Amylin + GLP-1 Therapy for Obesity",
                condition="obesity",
                icd10_codes=["E66", "E66.0"],
                phase="Phase 2",
                sponsor="DualPath Therapeutics",
                status="Recruiting",
                locations=["San Diego, CA", "Boston, MA"],
                min_age=18,
                max_age=65,
                gender="All",
                inclusion_criteria=[
                    "BMI 30-45 kg/m2",
                    "Failed prior weight loss attempts",
                    "No diabetes or well-controlled T2DM on metformin only",
                ],
                exclusion_criteria=[
                    "HbA1c > 8.5%",
                    "History of eating disorder",
                    "Untreated thyroid disorder",
                    "Prior bariatric surgery",
                ],
                bmi_min=30.0,
                bmi_max=45.0,
                description="Co-formulated amylin analogue + GLP-1 RA for enhanced weight loss.",
                start_date="2025-06-01",
                end_date="2028-03-31",
                enrollment_target=800,
                enrollment_current=290,
            ),
            ClinicalTrial(
                trial_id="OB-003",
                title="Endoscopic Sleeve Gastroplasty vs Medical Therapy",
                condition="obesity",
                icd10_codes=["E66", "E66.01"],
                phase="Phase 4",
                sponsor="GastroSleeve Medical",
                status="Recruiting",
                locations=["Miami, FL", "New York, NY", "Los Angeles, CA"],
                min_age=21,
                max_age=65,
                gender="All",
                inclusion_criteria=[
                    "BMI 30-40 kg/m2",
                    "Failed supervised weight management program",
                    "Willing to be randomized",
                ],
                exclusion_criteria=[
                    "Prior gastric surgery",
                    "Large hiatal hernia (> 5 cm)",
                    "Untreated H. pylori",
                    "Coagulopathy",
                ],
                bmi_min=30.0,
                bmi_max=40.0,
                description="Comparing endoscopic sleeve gastroplasty to intensive medical therapy for obesity.",
                start_date="2024-11-01",
                end_date="2027-10-31",
                enrollment_target=400,
                enrollment_current=260,
            ),
            # Depression Trials (3)
            ClinicalTrial(
                trial_id="DEP-001",
                title="Rapid-Acting Nasal Spray for Treatment-Resistant Depression",
                condition="depression",
                icd10_codes=[
                    "F32",
                    "F32.0",
                    "F32.1",
                    "F32.9",
                    "F33",
                    "F33.0",
                    "F33.1",
                    "F33.9",
                ],
                phase="Phase 3",
                sponsor="NeuroRapid Therapeutics",
                status="Recruiting",
                locations=["New York, NY", "Chicago, IL", "Seattle, WA"],
                min_age=18,
                max_age=65,
                gender="All",
                inclusion_criteria=[
                    "Major depressive disorder (DSM-5 criteria)",
                    "Treatment-resistant (failed >= 2 antidepressants)",
                    "MADRS score >= 28",
                    "Current episode duration >= 4 weeks",
                ],
                exclusion_criteria=[
                    "Bipolar disorder",
                    "Schizophrenia or schizoaffective disorder",
                    "Active suicidal intent",
                    "Substance use disorder within 6 months",
                    "Uncontrolled hypertension",
                ],
                excluded_comorbidities=["bipolar disorder", "schizophrenia"],
                required_prior_treatments=["antidepressant"],
                description="Novel NMDA modulator nasal spray for rapid antidepressant effect in TRD.",
                start_date="2025-04-01",
                end_date="2027-12-31",
                enrollment_target=600,
                enrollment_current=310,
            ),
            ClinicalTrial(
                trial_id="DEP-002",
                title="Transcranial Magnetic Stimulation Protocol Optimization",
                condition="depression",
                icd10_codes=["F32", "F32.9", "F33", "F33.9"],
                phase="Phase 4",
                sponsor="NeuroStim Devices",
                status="Recruiting",
                locations=["San Francisco, CA", "Austin, TX", "Denver, CO"],
                min_age=21,
                max_age=70,
                gender="All",
                inclusion_criteria=[
                    "Major depressive disorder, current episode",
                    "Failed 1-4 antidepressant trials",
                    "MADRS score >= 20",
                    "Willing to attend daily treatment sessions",
                ],
                exclusion_criteria=[
                    "Metallic implants in head",
                    "History of seizures",
                    "Pregnancy",
                    "Concurrent ECT",
                ],
                excluded_comorbidities=["epilepsy"],
                description="Comparing accelerated iTBS vs standard rTMS protocols for MDD.",
                start_date="2024-08-01",
                end_date="2026-07-31",
                enrollment_target=900,
                enrollment_current=620,
            ),
            ClinicalTrial(
                trial_id="DEP-003",
                title="Psilocybin-Assisted Therapy for Treatment-Resistant Depression",
                condition="depression",
                icd10_codes=["F33", "F33.1", "F33.9"],
                phase="Phase 2",
                sponsor="MindMed Research",
                status="Recruiting",
                locations=["Baltimore, MD", "Los Angeles, CA"],
                min_age=21,
                max_age=65,
                gender="All",
                inclusion_criteria=[
                    "Treatment-resistant major depressive disorder",
                    "Failed >= 2 adequate antidepressant trials",
                    "MADRS score >= 24",
                    "Stable on current medication for >= 6 weeks",
                ],
                exclusion_criteria=[
                    "Personal/family history of psychotic disorder",
                    "Bipolar I disorder",
                    "Uncontrolled cardiovascular disease",
                    "History of substance use disorder within 1 year",
                ],
                excluded_comorbidities=["psychotic disorder", "bipolar disorder"],
                required_prior_treatments=["antidepressant"],
                description="Psilocybin with psychological support for TRD in controlled clinical setting.",
                start_date="2025-09-01",
                end_date="2028-06-30",
                enrollment_target=200,
                enrollment_current=45,
            ),
        ]

        for trial in sample_trials:
            self.trials[trial.trial_id] = trial

        logger.info("Initialized %d sample clinical trials", len(sample_trials))

    def match_patient_to_trials(self, patient_ehr: dict) -> list[dict]:
        """Match a patient to eligible clinical trials.

        Args:
            patient_ehr: Dictionary containing patient EHR data with keys:
                - patient_id: str
                - age: int
                - gender: str
                - diagnoses: list of ICD-10 codes
                - medications: list of medication names
                - comorbidities: list of condition names
                - prior_treatments: list of treatment names
                - bmi: float (optional)

        Returns:
            List of MatchResult dicts sorted by eligibility_score descending.
        """
        if not patient_ehr:
            logger.warning("Empty patient EHR provided")
            return []

        required_fields = ["patient_id", "age", "gender", "diagnoses"]
        missing = [f for f in required_fields if f not in patient_ehr]
        if missing:
            raise ValueError(f"Patient EHR missing required fields: {missing}")

        results = []
        patient_conditions = self._extract_conditions(patient_ehr.get("diagnoses", []))
        patient_medications = [m.lower() for m in patient_ehr.get("medications", [])]
        patient_comorbidities = [
            c.lower() for c in patient_ehr.get("comorbidities", [])
        ]
        patient_prior_treatments = [
            t.lower() for t in patient_ehr.get("prior_treatments", [])
        ]
        patient_bmi = patient_ehr.get("bmi")

        for trial in self.trials.values():
            match_result = self._evaluate_trial(
                trial,
                patient_ehr,
                patient_conditions,
                patient_medications,
                patient_comorbidities,
                patient_prior_treatments,
                patient_bmi,
            )
            results.append(match_result.to_dict())

        results.sort(key=lambda x: x["eligibility_score"], reverse=True)

        self._match_history.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "patient_id": patient_ehr["patient_id"],
                "trials_evaluated": len(results),
                "eligible_count": sum(1 for r in results if r["eligible"]),
            }
        )

        logger.info(
            "Matched patient %s: %d trials evaluated, %d eligible",
            patient_ehr["patient_id"],
            len(results),
            sum(1 for r in results if r["eligible"]),
        )
        return results

    def _extract_conditions(self, icd10_codes: list) -> set:
        """Extract condition names from ICD-10 codes."""
        conditions = set()
        for code in icd10_codes:
            code_upper = str(code).upper()
            if code_upper in ICD10_CONDITION_MAP:
                conditions.add(ICD10_CONDITION_MAP[code_upper].lower())
            else:
                prefix = code_upper.split(".")[0]
                if prefix in ICD10_CONDITION_MAP:
                    conditions.add(ICD10_CONDITION_MAP[prefix].lower())
        return conditions

    def _evaluate_trial(
        self,
        trial: ClinicalTrial,
        patient: dict,
        patient_conditions: set,
        patient_medications: list,
        patient_comorbidities: list,
        patient_prior_treatments: list,
        patient_bmi: Optional[float],
    ) -> MatchResult:
        """Evaluate a single trial for patient eligibility."""
        reasons_matched = []
        reasons_excluded = []
        missing_criteria = []
        total_criteria = 0
        met_criteria = 0

        # Check condition match
        total_criteria += 1
        condition_match = trial.condition.lower() in patient_conditions
        if condition_match:
            met_criteria += 1
            reasons_matched.append(f"Patient has matching condition: {trial.condition}")
        else:
            reasons_excluded.append(
                f"Patient does not have condition: {trial.condition}"
            )

        # Check age
        total_criteria += 1
        age = patient.get("age", 0)
        if trial.min_age <= age <= trial.max_age:
            met_criteria += 1
            reasons_matched.append(
                f"Age {age} within range [{trial.min_age}-{trial.max_age}]"
            )
        else:
            reasons_excluded.append(
                f"Age {age} outside range [{trial.min_age}-{trial.max_age}]"
            )

        # Check gender
        total_criteria += 1
        gender = patient.get("gender", "").strip()
        if trial.gender == "All" or gender.lower() == trial.gender.lower():
            met_criteria += 1
            reasons_matched.append(f"Gender {gender} matches trial requirement")
        else:
            reasons_excluded.append(
                f"Gender {gender} does not match trial requirement ({trial.gender})"
            )

        # Check required medications
        if trial.required_medications:
            total_criteria += 1
            med_match = any(
                req_med in patient_medications
                for req_med in [m.lower() for m in trial.required_medications]
            )
            if med_match:
                met_criteria += 1
                reasons_matched.append("Patient takes required medication")
            else:
                reasons_excluded.append(
                    f"Patient not taking required medications: {trial.required_medications}"
                )

        # Check excluded medications
        if trial.excluded_medications:
            total_criteria += 1
            excluded_med_found = [
                med
                for med in trial.excluded_medications
                if med.lower() in patient_medications
            ]
            if excluded_med_found:
                reasons_excluded.append(
                    f"Patient taking excluded medications: {excluded_med_found}"
                )
            else:
                met_criteria += 1
                reasons_matched.append("No excluded medications detected")

        # Check required prior treatments
        if trial.required_prior_treatments:
            total_criteria += 1
            treatment_match = any(
                req in patient_prior_treatments
                for req in [t.lower() for t in trial.required_prior_treatments]
            )
            if treatment_match:
                met_criteria += 1
                reasons_matched.append("Patient has required prior treatment history")
            else:
                reasons_excluded.append(
                    f"Patient lacks required prior treatments: {trial.required_prior_treatments}"
                )

        # Check excluded comorbidities
        if trial.excluded_comorbidities:
            total_criteria += 1
            excluded_comorbid_found = [
                com
                for com in trial.excluded_comorbidities
                if com.lower() in patient_comorbidities
            ]
            if excluded_comorbid_found:
                reasons_excluded.append(
                    f"Patient has excluded comorbidities: {excluded_comorbid_found}"
                )
            else:
                met_criteria += 1
                reasons_matched.append("No excluded comorbidities")

        # Check required comorbidities
        if trial.required_comorbidities:
            total_criteria += 1
            comorbid_match = any(
                req in patient_comorbidities
                for req in [c.lower() for c in trial.required_comorbidities]
            )
            if comorbid_match:
                met_criteria += 1
                reasons_matched.append("Patient has required comorbidity")
            else:
                reasons_excluded.append(
                    f"Patient lacks required comorbidities: {trial.required_comorbidities}"
                )

        # Check BMI
        if trial.bmi_min is not None or trial.bmi_max is not None:
            total_criteria += 1
            if patient_bmi is not None:
                bmi_ok = True
                if trial.bmi_min is not None and patient_bmi < trial.bmi_min:
                    bmi_ok = False
                    reasons_excluded.append(
                        f"BMI {patient_bmi} below minimum {trial.bmi_min}"
                    )
                if trial.bmi_max is not None and patient_bmi > trial.bmi_max:
                    bmi_ok = False
                    reasons_excluded.append(
                        f"BMI {patient_bmi} above maximum {trial.bmi_max}"
                    )
                if bmi_ok:
                    met_criteria += 1
                    reasons_matched.append(f"BMI {patient_bmi} within acceptable range")
            else:
                missing_criteria.append("BMI not provided in patient record")

        # Calculate score
        if total_criteria > 0:
            score = round((met_criteria / total_criteria) * 100, 1)
        else:
            score = 0.0

        eligible = len(reasons_excluded) == 0

        return MatchResult(
            trial_id=trial.trial_id,
            trial_title=trial.title,
            eligibility_score=score,
            eligible=eligible,
            reasons_matched=reasons_matched,
            reasons_excluded=reasons_excluded,
            missing_criteria=missing_criteria,
        )

    def get_trial_details(self, trial_id: str) -> Optional[dict]:
        """Get full details for a specific trial."""
        trial = self.trials.get(trial_id)
        if trial is None:
            logger.warning("Trial %s not found", trial_id)
            return None
        return trial.to_dict()

    def search_trials(
        self,
        condition: str = "",
        location: str = "",
        phase: str = "",
    ) -> list[dict]:
        """Search trials by condition, location, and/or phase."""
        results = []
        condition_lower = condition.lower().strip() if condition else ""
        location_lower = location.lower().strip() if location else ""
        phase_lower = phase.lower().strip() if phase else ""

        for trial in self.trials.values():
            match = True

            if condition_lower:
                cond_match = condition_lower in trial.condition.lower() or any(
                    condition_lower in icd.lower() for icd in trial.icd10_codes
                )
                if not cond_match:
                    match = False

            if location_lower and match:
                loc_match = any(
                    location_lower in loc.lower() for loc in trial.locations
                )
                if not loc_match:
                    match = False

            if phase_lower and match:
                if phase_lower not in trial.phase.lower():
                    match = False

            if match:
                results.append(trial.to_dict())

        logger.info(
            "Search: condition='%s', location='%s', phase='%s' -> %d results",
            condition,
            location,
            phase,
            len(results),
        )
        return results

    def get_eligibility_reasons(self, patient: dict, trial: dict) -> dict:
        """Get detailed eligibility explanation for a patient-trial pair."""
        patient_conditions = self._extract_conditions(patient.get("diagnoses", []))
        patient_medications = [m.lower() for m in patient.get("medications", [])]
        patient_comorbidities = [c.lower() for c in patient.get("comorbidities", [])]
        patient_prior_treatments = [
            t.lower() for t in patient.get("prior_treatments", [])
        ]
        patient_bmi = patient.get("bmi")

        trial_obj = ClinicalTrial(**trial) if isinstance(trial, dict) else trial

        result = self._evaluate_trial(
            trial_obj,
            patient,
            patient_conditions,
            patient_medications,
            patient_comorbidities,
            patient_prior_treatments,
            patient_bmi,
        )

        return {
            "trial_id": trial_obj.trial_id,
            "trial_title": trial_obj.title,
            "eligible": result.eligible,
            "eligibility_score": result.eligibility_score,
            "reasons_matched": result.reasons_matched,
            "reasons_excluded": result.reasons_excluded,
            "missing_criteria": result.missing_criteria,
        }

    def get_statistics(self) -> dict:
        """Get engine statistics."""
        by_condition = {}
        by_phase = {}
        by_status = {}
        total_enrollment = 0
        total_target = 0

        for trial in self.trials.values():
            by_condition[trial.condition] = by_condition.get(trial.condition, 0) + 1
            by_phase[trial.phase] = by_phase.get(trial.phase, 0) + 1
            by_status[trial.status] = by_status.get(trial.status, 0) + 1
            total_enrollment += trial.enrollment_current
            total_target += trial.enrollment_target

        return {
            "total_trials": len(self.trials),
            "by_condition": by_condition,
            "by_phase": by_phase,
            "by_status": by_status,
            "total_enrollment_current": total_enrollment,
            "total_enrollment_target": total_target,
            "enrollment_rate": round(total_enrollment / total_target * 100, 1)
            if total_target > 0
            else 0,
            "total_matches_performed": len(self._match_history),
            "trial_ids": list(self.trials.keys()),
        }
