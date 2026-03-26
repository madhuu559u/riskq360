"""Shared test fixtures for MedInsight 360."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set test environment variables before importing settings
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "medinsight360_test")
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ.setdefault("ACTIVE_LLM_PROVIDER", "openai")
os.environ.setdefault("ENABLE_ML_PREDICTIONS", "false")
os.environ.setdefault("ENABLE_LLM_VERIFICATION", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture
def reference_dir() -> Path:
    return PROJECT_ROOT / "decisioning" / "reference"


@pytest.fixture
def models_dir() -> Path:
    return PROJECT_ROOT / "ml_engine" / "models"


@pytest.fixture
def uploads_dir() -> Path:
    return PROJECT_ROOT / "uploads"


@pytest.fixture
def sample_clinical_text() -> str:
    return """
PATIENT: John Smith  DOB: 03/15/1955  MBI: 1EG4-TE5-MK72
DATE OF SERVICE: 08/15/2025
PROVIDER: Dr. Sarah Johnson, MD

CHIEF COMPLAINT: Follow-up for diabetes management and hypertension.

HISTORY OF PRESENT ILLNESS:
Mr. Smith is a 70-year-old male with a history of type 2 diabetes mellitus
with chronic complications including diabetic retinopathy and hyperglycemia.
He reports his blood sugars have been running between 150-200 mg/dL fasting.
He denies any chest pain or shortness of breath.
No evidence of peripheral neuropathy at this time.
Mother had breast cancer at age 62.

REVIEW OF SYSTEMS:
Constitutional: No fever, no weight loss.
Cardiovascular: No chest pain, no palpitations.
Respiratory: No shortness of breath.
Endocrine: Polyuria, polydipsia noted.

PHYSICAL EXAMINATION:
Vitals: BP 142/88 mmHg, HR 76, Temp 98.6F, Weight 210 lbs, BMI 31.2
General: Alert, oriented, no acute distress.
Heart: RRR, no murmurs.
Lungs: Clear to auscultation bilaterally.
Extremities: No edema, pulses intact.

LABORATORY RESULTS:
HbA1c: 8.2% (drawn 08/01/2025)
LDL: 128 mg/dL
Creatinine: 1.1 mg/dL
eGFR: 72 mL/min

ASSESSMENT AND PLAN:
1. Type 2 diabetes mellitus with hyperglycemia (E11.65) - uncontrolled.
   Continue metformin 1000mg BID. Add glipizide 5mg daily.
   Recheck A1C in 3 months. Diabetic eye exam ordered.
2. Essential hypertension (I10) - not at goal.
   Increase lisinopril to 20mg daily. Recheck BP in 2 weeks.
3. Obesity (E66.01) - BMI 31.2. Counseled on diet and exercise.
4. History of stroke in 2018 - stable, continue aspirin 81mg daily.

Follow-up in 3 months.
"""


@pytest.fixture
def sample_demographics() -> Dict[str, Any]:
    return {
        "patient_name": "John Smith",
        "date_of_birth": "1955-03-15",
        "gender": "M",
        "mbi": "1EG4-TE5-MK72",
        "age": 70,
    }


@pytest.fixture
def sample_verified_codes() -> List[Dict[str, Any]]:
    return [
        {
            "icd10_code": "E11.65",
            "icd10_description": "Type 2 diabetes mellitus with hyperglycemia",
            "confidence": 0.92,
            "ml_confidence": 0.87,
            "polarity": "active",
            "meat_evidence": {
                "monitored": True,
                "evaluated": True,
                "assessed": True,
                "treated": True,
            },
            "evidence_spans": [{"text": "Type 2 diabetes with hyperglycemia", "page": 1}],
            "date_of_service": "2025-08-15",
            "provider": "Dr. Sarah Johnson",
        },
        {
            "icd10_code": "I10",
            "icd10_description": "Essential (primary) hypertension",
            "confidence": 0.88,
            "ml_confidence": 0.82,
            "polarity": "active",
            "meat_evidence": {
                "monitored": True,
                "evaluated": True,
                "assessed": True,
                "treated": True,
            },
            "evidence_spans": [{"text": "Essential hypertension - not at goal", "page": 1}],
            "date_of_service": "2025-08-15",
            "provider": "Dr. Sarah Johnson",
        },
        {
            "icd10_code": "E66.01",
            "icd10_description": "Morbid (severe) obesity due to excess calories",
            "confidence": 0.85,
            "ml_confidence": 0.78,
            "polarity": "active",
            "meat_evidence": {
                "monitored": True,
                "evaluated": True,
                "assessed": True,
                "treated": False,
            },
            "evidence_spans": [{"text": "Obesity - BMI 31.2", "page": 1}],
            "date_of_service": "2025-08-15",
            "provider": "Dr. Sarah Johnson",
        },
    ]


@pytest.fixture
def sample_hcc_mappings() -> List[Dict[str, Any]]:
    """Pre-mapped HCC results for hierarchy testing."""
    return [
        {
            "icd10_code": "E11.65",
            "icd10_description": "Type 2 diabetes mellitus with hyperglycemia",
            "hcc_code": "HCC37",
            "hcc_description": "Diabetes with Chronic Complications",
            "raf_weight": 0.302,
            "confidence": 0.92,
            "ml_confidence": 0.87,
            "llm_confidence": 0.92,
            "polarity": "active",
            "meat_evidence": {},
            "evidence_spans": [],
            "date_of_service": "2025-08-15",
            "provider": "Dr. Smith",
            "is_suppressed": False,
            "suppressed_by": None,
        },
        {
            "icd10_code": "E11.9",
            "icd10_description": "Type 2 diabetes mellitus without complications",
            "hcc_code": "HCC38",
            "hcc_description": "Diabetes without Complications",
            "raf_weight": 0.118,
            "confidence": 0.80,
            "ml_confidence": 0.75,
            "llm_confidence": 0.80,
            "polarity": "active",
            "meat_evidence": {},
            "evidence_spans": [],
            "date_of_service": "2025-08-15",
            "provider": "Dr. Smith",
            "is_suppressed": False,
            "suppressed_by": None,
        },
    ]
