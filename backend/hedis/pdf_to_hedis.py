"""Extract clinical data from PDFs and evaluate HEDIS measures."""

import json
import sys
import os

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
from datetime import date, datetime
from pathlib import Path

import pdfplumber

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from hedis_engine.types import (
    CodeSystem, Demographics, DiagnosisEvent, DiagnosisStatus,
    EncounterEvent, EncounterType, Gender, ImmunizationEvent,
    LabEvent, MedicationEvent, MemberEventStore, ProcedureEvent,
    VitalEvent, VitalType, EvidenceRef,
)
from hedis_engine.engine import HedisEngine


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_path: str) -> list[str]:
    """Extract text from all pages of a PDF."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return pages


# ---------------------------------------------------------------------------
# Clinical data builders for each PDF
# ---------------------------------------------------------------------------

def build_gsd4_member() -> tuple[str, MemberEventStore]:
    """GSD4.pdf — HUDGINS, BRITTNEY — Female, DOB 05/08/1988, Diabetic, A1C 5.7"""
    store = MemberEventStore(
        demographics=Demographics(
            dob=date(1988, 5, 8),
            gender=Gender.FEMALE,
        ),
        diagnoses=[
            # Type 2 diabetes without complications
            DiagnosisEvent(
                code="E11.9",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 11, 18),
                evidence_ref=EvidenceRef(pdf="GSD4.pdf", page_number=2,
                    exact_quote="Dx: Type 2 diabetes mellitus without comp..."),
            ),
        ],
        labs=[
            # A1C = 5.7 on 11/18/2024
            LabEvent(
                test_type="A1C",
                value=5.7,
                unit="%",
                event_date=date(2024, 11, 18),
                evidence_ref=EvidenceRef(pdf="GSD4.pdf", page_number=1,
                    exact_quote="Most recent GMI level(%) 11/18/2024  5.7"),
            ),
            # A1C = 5.6 on 4/29/2024
            LabEvent(
                test_type="A1C",
                value=5.6,
                unit="%",
                event_date=date(2024, 4, 29),
                evidence_ref=EvidenceRef(pdf="GSD4.pdf", page_number=2,
                    exact_quote="5.6 (4/29/24)"),
            ),
        ],
        encounters=[
            EncounterEvent(
                encounter_type=EncounterType.OUTPATIENT,
                event_date=date(2024, 11, 18),
                evidence_ref=EvidenceRef(pdf="GSD4.pdf", page_number=2,
                    exact_quote="Encounter Date: 11/18/2024"),
            ),
        ],
        procedures=[],
        vitals=[],
        medications=[],
        immunizations=[],
    )
    return "HUDGINS_BRITTNEY", store


def build_gsd5_member() -> tuple[str, MemberEventStore]:
    """GSD5.pdf — MOORE, DAVID — Male, DOB 12/21/1967, Diabetic, A1C 7.7"""
    store = MemberEventStore(
        demographics=Demographics(
            dob=date(1967, 12, 21),
            gender=Gender.MALE,
        ),
        diagnoses=[
            # Diabetes (implied from GSD measure context)
            DiagnosisEvent(
                code="E11.9",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 10, 24),
                evidence_ref=EvidenceRef(pdf="GSD5.pdf", page_number=1,
                    exact_quote="GSD - Glycemic Status Assessment for Patients With Diabetes"),
            ),
        ],
        labs=[
            # A1C = 7.7 on 10/24/2024
            LabEvent(
                test_type="A1C",
                value=7.7,
                unit="%",
                event_date=date(2024, 10, 24),
                evidence_ref=EvidenceRef(pdf="GSD5.pdf", page_number=1,
                    exact_quote="Most recent GMI level(%) 10/24/2024  7.7"),
            ),
            # PHQ-2/PHQ-9 score = 0 on 10/23/2024
            LabEvent(
                test_type="PHQ9",
                value=0.0,
                unit="score",
                event_date=date(2024, 10, 23),
                evidence_ref=EvidenceRef(pdf="GSD5.pdf", page_number=2,
                    exact_quote="PHQ-2/PHQ-9 0 10/23/2024"),
            ),
            # Vitamin D lab
            LabEvent(
                test_type="VITAMIN_D",
                value=None,
                unit="ng/mL",
                event_date=date(2024, 10, 24),
                evidence_ref=EvidenceRef(pdf="GSD5.pdf", page_number=2,
                    exact_quote="VITAMIN D, 25 HYDROXY 10/25/2024"),
            ),
        ],
        encounters=[
            EncounterEvent(
                encounter_type=EncounterType.OUTPATIENT,
                event_date=date(2024, 10, 23),
                evidence_ref=EvidenceRef(pdf="GSD5.pdf", page_number=2,
                    exact_quote="PHQ-2/PHQ-9 0 10/23/2024"),
            ),
        ],
        procedures=[],
        vitals=[],
        medications=[],
        immunizations=[],
    )
    return "MOORE_DAVID", store


def build_bpd1_member() -> tuple[str, MemberEventStore]:
    """BPD_1.pdf — ADAME, BONNIE EILEEN — Female, DOB 01/31/1964, multiple conditions"""
    store = MemberEventStore(
        demographics=Demographics(
            dob=date(1964, 1, 31),
            gender=Gender.FEMALE,
        ),
        diagnoses=[
            # CAD - Coronary artery disease
            DiagnosisEvent(
                code="I25.10",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=6,
                    exact_quote="Coronary artery disease involving native coronary artery of native heart without angina pectoris I25.10"),
            ),
            # Essential hypertension
            DiagnosisEvent(
                code="I10",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=6,
                    exact_quote="Essential hypertension I10"),
            ),
            # Hyperlipidemia
            DiagnosisEvent(
                code="E78.5",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=6,
                    exact_quote="Hyperlipidemia, unspecified hyperlipidemia type E78.5"),
            ),
            # Diabetes mellitus (from past medical history - still active per context)
            DiagnosisEvent(
                code="E11.9",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=1,
                    exact_quote="Diabetes mellitus (CMS, HHS-HCC)"),
            ),
            # COPD
            DiagnosisEvent(
                code="J44.1",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=1,
                    exact_quote="COPD (chronic obstructive pulmonary disease) (CMS, HHS-HCC)"),
            ),
            # Asthma
            DiagnosisEvent(
                code="J45.20",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=1,
                    exact_quote="Asthma (HHS-HCC)"),
            ),
            # Osteoporosis (from past medical history)
            DiagnosisEvent(
                code="M81.0",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=1,
                    exact_quote="Osteoporosis"),
            ),
            # Myocardial infarction - historical
            DiagnosisEvent(
                code="I21.9",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.HISTORICAL,
                event_date=date(2017, 4, 24),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=1,
                    exact_quote="Myocardial infarction (CMS, HHS-HCC) 04/24/2017"),
            ),
            # Pre-syncope
            DiagnosisEvent(
                code="R55",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=6,
                    exact_quote="Pre-syncope R55"),
            ),
            # Uterine cancer - from past medical history
            DiagnosisEvent(
                code="C55",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.HISTORICAL,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=1,
                    exact_quote="Uterine cancer (CMS, HHS-HCC)"),
            ),
        ],
        vitals=[
            # Blood Pressure 112/84 on 11/27/2024
            VitalEvent(
                vital_type=VitalType.BP,
                systolic=112,
                diastolic=84,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=3,
                    exact_quote="BP: 112/84"),
            ),
            # BMI 28.6
            VitalEvent(
                vital_type=VitalType.BMI,
                value=28.6,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=3,
                    exact_quote="BMI 28.6 (Calculated)"),
            ),
            # Height/Weight
            VitalEvent(
                vital_type=VitalType.WEIGHT,
                value=73.2,
                unit="kg",
                event_date=date(2024, 11, 27),
            ),
            VitalEvent(
                vital_type=VitalType.HEIGHT,
                value=160.0,
                unit="cm",
                event_date=date(2024, 11, 27),
            ),
        ],
        medications=[
            # Atorvastatin (statin)
            MedicationEvent(
                name="atorvastatin 40mg",
                normalized_class="statin",
                start_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=2,
                    exact_quote="atorvastatin (LIPITOR) 40 MG TAKE ONE TABLET BY MOUTH ONCE DAILY"),
            ),
            # Losartan (ARB - for hypertension)
            MedicationEvent(
                name="losartan 25mg",
                normalized_class="arb",
                start_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=2,
                    exact_quote="losartan (COZAAR) 25 MG Take 1 tablet (25 mg total) by mouth daily"),
            ),
            # Aspirin
            MedicationEvent(
                name="aspirin 81mg",
                normalized_class="antiplatelet",
                start_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=5,
                    exact_quote="aspirin 81 MG EC tablet Take 1 tablet (81 mg total) by mouth daily"),
            ),
            # Fluticasone furoate-vilanterol (inhaler for COPD/asthma)
            MedicationEvent(
                name="fluticasone furoate-vilanterol 200-25mcg",
                normalized_class="inhaled_corticosteroid",
                start_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=2,
                    exact_quote="fluticasone furoate-vilanterol (BREO ELLIPTA) 200-25"),
            ),
            # Cetirizine (allergy)
            MedicationEvent(
                name="cetirizine 10mg",
                normalized_class="antihistamine",
                start_date=date(2024, 11, 27),
            ),
        ],
        encounters=[
            # Office visit 11/27/2024 with cardiologist
            EncounterEvent(
                encounter_type=EncounterType.OUTPATIENT,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=1,
                    exact_quote="Encounter Date: 11/27/2024"),
            ),
            # Previous visit 6/21/2024
            EncounterEvent(
                encounter_type=EncounterType.OUTPATIENT,
                event_date=date(2024, 6, 21),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=12,
                    exact_quote="6/21/2024 16:42 Northern Utah Cardiovascular Associates"),
            ),
        ],
        labs=[],
        procedures=[
            # CPT 99214 - Office/outpatient visit established moderate
            ProcedureEvent(
                code="99214",
                code_system=CodeSystem.CPT,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=12,
                    exact_quote="99214 PR OFFICE/OUTPATIENT ESTABLISHED MOD MDM 30 MIN"),
            ),
            # CPT 93000 - ECG
            ProcedureEvent(
                code="93000",
                code_system=CodeSystem.CPT,
                event_date=date(2024, 11, 27),
                evidence_ref=EvidenceRef(pdf="BPD_1.pdf", page_number=12,
                    exact_quote="93000 PR ECG ROUTINE ECG W/LEAST 12 LDS"),
            ),
        ],
        immunizations=[],
    )
    return "ADAME_BONNIE", store


def build_bpd2_member() -> tuple[str, MemberEventStore]:
    """BPD_2.pdf — RIPPERGER, PAUL D — Male, DOB 9/14/1970, mostly healthy"""
    store = MemberEventStore(
        demographics=Demographics(
            dob=date(1970, 9, 14),
            gender=Gender.MALE,
        ),
        diagnoses=[
            # Hematoma (minor, from 2023)
            DiagnosisEvent(
                code="T14.0",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.HISTORICAL,
                event_date=date(2023, 8, 8),
                evidence_ref=EvidenceRef(pdf="BPD_2.pdf", page_number=3,
                    exact_quote="Hematoma 08/08/2023"),
            ),
            # Sinus congestion (acute visit)
            DiagnosisEvent(
                code="J34.89",
                code_system=CodeSystem.ICD10CM,
                status=DiagnosisStatus.ACTIVE,
                event_date=date(2024, 12, 19),
                evidence_ref=EvidenceRef(pdf="BPD_2.pdf", page_number=2,
                    exact_quote="Sinus congestion (primary)"),
            ),
        ],
        vitals=[
            # BP 125/85 on 12/19/2024
            VitalEvent(
                vital_type=VitalType.BP,
                systolic=125,
                diastolic=85,
                event_date=date(2024, 12, 19),
                evidence_ref=EvidenceRef(pdf="BPD_2.pdf", page_number=2,
                    exact_quote="BP 125/85"),
            ),
            # BP 130/80 on 8/8/2023
            VitalEvent(
                vital_type=VitalType.BP,
                systolic=130,
                diastolic=80,
                event_date=date(2023, 8, 8),
                evidence_ref=EvidenceRef(pdf="BPD_2.pdf", page_number=7,
                    exact_quote="BP 130/80 (BP Location: Right arm)"),
            ),
        ],
        encounters=[
            # Visit 12/19/2024 - sinus congestion
            EncounterEvent(
                encounter_type=EncounterType.OUTPATIENT,
                event_date=date(2024, 12, 19),
                evidence_ref=EvidenceRef(pdf="BPD_2.pdf", page_number=2,
                    exact_quote="Encounter Date: 12/19/2024"),
            ),
            # Visit 8/8/2023 - hematoma
            EncounterEvent(
                encounter_type=EncounterType.OUTPATIENT,
                event_date=date(2023, 8, 8),
                evidence_ref=EvidenceRef(pdf="BPD_2.pdf", page_number=6,
                    exact_quote="Encounter Date: 8/8/2023"),
            ),
        ],
        medications=[
            # Prednisone taper (acute, from 12/19/2024)
            MedicationEvent(
                name="prednisone 20mg taper",
                normalized_class="corticosteroid",
                start_date=date(2024, 12, 19),
                evidence_ref=EvidenceRef(pdf="BPD_2.pdf", page_number=4,
                    exact_quote="predniSONE (Deltasone) 20 MG tablet; Take 3 tablets (60 mg)"),
            ),
        ],
        labs=[],
        procedures=[],
        immunizations=[],
    )
    return "RIPPERGER_PAUL", store


# ---------------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------------

def run_evaluation():
    """Run HEDIS evaluation for all 4 PDF members."""
    measurement_year = 2024
    catalog_dir = str(Path(__file__).parent / "hedis_engine" / "catalog")

    engine = HedisEngine(catalog_dir=Path(catalog_dir), measurement_year=measurement_year)

    # Build all members
    members = [
        build_gsd4_member(),
        build_gsd5_member(),
        build_bpd1_member(),
        build_bpd2_member(),
    ]

    pdf_sources = {
        "HUDGINS_BRITTNEY": "GSD4.pdf",
        "MOORE_DAVID": "GSD5.pdf",
        "ADAME_BONNIE": "BPD_1.pdf",
        "RIPPERGER_PAUL": "BPD_2.pdf",
    }

    all_results = {}

    for member_id, store in members:
        pdf_name = pdf_sources[member_id]
        results = engine.evaluate_member(store)

        met = []
        gap = []
        not_applicable = []
        excluded = []

        for m in results.measures:
            if m.status.value == "met":
                met.append(m)
            elif m.status.value == "gap":
                gap.append(m)
            elif m.status.value == "not_applicable":
                not_applicable.append(m)
            elif m.status.value == "excluded":
                excluded.append(m)

        all_results[member_id] = {
            "pdf": pdf_name,
            "demographics": f"{store.demographics.gender.value}, DOB {store.demographics.dob}",
            "met": met,
            "gap": gap,
            "not_applicable": not_applicable,
            "excluded": excluded,
            "results": results,
        }

    # Print results
    print("=" * 100)
    print(f"  HEDIS MEASURE EVALUATION RESULTS — Measurement Year {measurement_year}")
    print("=" * 100)

    for member_id, data in all_results.items():
        print(f"\n{'─' * 100}")
        print(f"  PATIENT: {member_id.replace('_', ' ')}  |  PDF: {data['pdf']}  |  {data['demographics']}")
        print(f"{'─' * 100}")
        print(f"  MET: {len(data['met'])}  |  GAP: {len(data['gap'])}  |  NOT APPLICABLE: {len(data['not_applicable'])}  |  EXCLUDED: {len(data['excluded'])}")
        print()

        if data["met"]:
            print("  [MET] MEASURES MET:")
            for m in data["met"]:
                evidence_summary = ""
                if m.evidence_used:
                    ev = m.evidence_used[0]
                    code_info = ev.code or ev.value or ""
                    date_info = str(ev.event_date) if ev.event_date else "N/A"
                    evidence_summary = f" -- Evidence: {ev.event_type} {code_info} ({date_info})"
                print(f"    [+] {m.measure_id:<25s} {m.measure_name}{evidence_summary}")

        if data["gap"]:
            print("\n  [GAP] GAPS (Non-Compliant):")
            for m in data["gap"]:
                gap_detail = ""
                if m.gaps:
                    g = m.gaps[0]
                    gap_detail = f" -- Missing: {g.gap_type} {g.description or g.required_event}"
                print(f"    [-] {m.measure_id:<25s} {m.measure_name}{gap_detail}")

        if data["not_applicable"]:
            print(f"\n  [N/A] NOT APPLICABLE ({len(data['not_applicable'])} measures):")
            # Group by reason
            age_reasons = []
            gender_reasons = []
            dx_reasons = []
            other_reasons = []
            for m in data["not_applicable"]:
                reason = m.eligibility_reason[0] if m.eligibility_reason else ""
                if "age" in reason.lower():
                    age_reasons.append(m)
                elif "gender" in reason.lower():
                    gender_reasons.append(m)
                elif "diagnosis" in reason.lower() or "condition" in reason.lower() or "no matching" in reason.lower():
                    dx_reasons.append(m)
                else:
                    other_reasons.append(m)

            if age_reasons:
                print(f"    Age-ineligible: {', '.join(m.measure_id for m in age_reasons)}")
            if gender_reasons:
                print(f"    Gender-ineligible: {', '.join(m.measure_id for m in gender_reasons)}")
            if dx_reasons:
                print(f"    No qualifying Dx: {', '.join(m.measure_id for m in dx_reasons)}")
            if other_reasons:
                print(f"    Other: {', '.join(m.measure_id for m in other_reasons)}")

        print()

    # Summary table
    print("\n" + "=" * 100)
    print("  SUMMARY TABLE")
    print("=" * 100)
    print(f"  {'Patient':<25s} {'PDF':<12s} {'Met':>5s} {'Gap':>5s} {'N/A':>5s} {'Excl':>5s} {'Total':>6s}")
    print(f"  {'─'*25} {'─'*12} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*6}")
    for member_id, data in all_results.items():
        total = len(data['met']) + len(data['gap']) + len(data['not_applicable']) + len(data['excluded'])
        print(f"  {member_id.replace('_', ' '):<25s} {data['pdf']:<12s} {len(data['met']):>5d} {len(data['gap']):>5d} {len(data['not_applicable']):>5d} {len(data['excluded']):>5d} {total:>6d}")

    # Write full results to JSON
    output_path = Path(__file__).parent / "pdf_hedis_results.json"
    all_json = {}
    for member_id, data in all_results.items():
        all_json[member_id] = data["results"].to_dict()

    with open(output_path, "w") as f:
        json.dump(all_json, f, indent=2, default=str)
    print(f"\n  Full results written to: {output_path}")


if __name__ == "__main__":
    run_evaluation()
