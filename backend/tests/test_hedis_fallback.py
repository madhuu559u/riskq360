from __future__ import annotations

from extraction.hedis_fallback import extract_hedis_fallback_artifacts, parse_pages_from_full_text


def test_parse_pages_from_full_text() -> None:
    text = """
--- PAGE 1 [TEXT] ---
DOB: 01/02/1970
BP 132/84
--- PAGE 2 [TEXT] ---
HbA1c 7.4%
"""
    pages = parse_pages_from_full_text(text)
    assert sorted(pages.keys()) == [1, 2]
    assert "DOB" in pages[1]
    assert "HbA1c" in pages[2]


def test_extract_hedis_fallback_artifacts_evidence() -> None:
    text = """
--- PAGE 1 [TEXT] ---
DOB: 01/02/1970
Sex: Female
Encounter - Office Visit Date of service: 01/10/2025
SEEN BY Dr. Avery Chen
FACILITY: Harbor Primary Care
Type 2 diabetes mellitus
BP 138/82
--- PAGE 2 [TEXT] ---
A1c 7.1%
Mammogram completed 11/03/2025
Atorvastatin 20 mg daily
Influenza vaccine given 10/01/2025
"""
    out = extract_hedis_fallback_artifacts(full_text=text, pdf_name="demo.pdf")
    assertions = out["assertions"]
    assert assertions, "Expected deterministic assertions"
    assert all(a.get("page_number") is not None for a in assertions)
    assert all(a.get("exact_quote") for a in assertions)

    demo = out["demographics"]
    assert demo.get("dob") == "01/02/1970"
    assert demo.get("gender") == "female"

    hedis_patch = out["hedis_patch"]
    assert hedis_patch["blood_pressure_readings"]
    assert hedis_patch["lab_results"]
    assert hedis_patch["screenings"]
    assert hedis_patch["medications_for_measures"]
    assert hedis_patch["immunizations"]

    encounters_patch = out.get("encounters_patch", {})
    encounters = encounters_patch.get("encounters", [])
    assert encounters
    first = encounters[0]
    assert first.get("date") == "2025-01-10"
    assert first.get("provider")
    assert first.get("facility")
    assert first.get("page_number") == 1
    assert first.get("evidence")
