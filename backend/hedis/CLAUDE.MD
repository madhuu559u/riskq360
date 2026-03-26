ROLE
You are Claude Code acting as a principal engineer building a production-grade HEDIS measure engine (rule-based) that evaluates member eligibility + compliance + gaps from extracted clinical evidence. You must research, implement, test, and document a system that supports ~50 HEDIS-like measures (focus on top 30 first, but architecture must handle 50). The system must be extensible, structured, testable, and audit-friendly.

CRITICAL REALITY CHECK (DO NOT IGNORE)
Official HEDIS specifications and value set files are NCQA-licensed. If you cannot legally access full specs, you must:
- implement the engine architecture + rule DSL + measure catalog scaffolding
- populate measures using publicly available descriptions (not the licensed spec text)
- design the code so official value sets/specs can be dropped in later without refactor
Do not copy licensed spec text verbatim. Cite sources for any public references used.

INPUT DATA CONTEXT (WHAT THE UPSTREAM EXTRACTOR PROVIDES)
Assume we already have per-member evidence extracted from PDFs into JSON “assertions” with fields like:
- member demographics: DOB, gender (may be extracted or provided from enrollment)
- encounter/service dates and inferred dates
- diagnosis/assertion concepts (canonical_concept)
- codes: ICD-10-CM, ICD-9-CM (separate), CPT/HCPCS (sometimes), and free-text meds/vitals/labs if present
- vitals (BP systolic/diastolic, BMI, etc.) when present
- labs (A1c value/date) when present
- medications (name string; may later map to RxNorm/NDC)
- evidence anchors: pdf, page_number, exact_quote, offsets
You must not require perfect data; engine should work with partial evidence and return “unknown/missing” cleanly.

GOAL
Create a HEDIS measure evaluation system that can answer for each member:
1) Is this measure applicable (eligible) for the member in the measurement year?
2) If applicable, is the member compliant? If not, what gap remains?
3) What evidence supports compliance (include dates + references)?
4) What evidence supports denominator inclusion/exclusion?
5) What data is missing that prevents determination?

MEASURES SCOPE
Implement a catalog with at least 30 high-impact measures, and design to scale to 50+.
Prioritize domains:
- Diabetes care (A1c test/control, eye exam, nephropathy, statin use)
- Hypertension/BP control
- Preventive screenings (colorectal, breast, cervical)
- Immunizations (childhood, adolescent, flu, pneumococcal)
- Well-child/adolescent visits
- Depression screening/follow-up
- Medication adherence proxies (if feasible from data)
- Tobacco screening/cessation counseling
- BMI/obesity-related counseling
- Care transitions / follow-up after hospitalization (only if you have admission/discharge evidence)

ARCHITECTURE REQUIREMENTS (NON-NEGOTIABLE)
1) Separate measure logic from code sets:
   - Measure definitions reference abstract “ValueSet” IDs (e.g., VS_COLONOSCOPY_CPT)
   - Value sets loaded from external JSON/CSV (placeholder now; official later)
2) Deterministic rule engine:
   - No ML for eligibility/compliance decisions
   - Use explicit rule evaluation with trace output
3) Audit trail:
   - Every decision must return a structured trace describing which rule fired, which evidence was used, and which dates were applied
4) Extensible DSL:
   - A measure definition format (YAML/JSON) describing:
     - name, id, version, measurement_year
     - population criteria: age, gender, continuous enrollment flags (optional)
     - denominator: required conditions/events
     - exclusions: conditions/events/time windows
     - numerator: required events/values in time window
     - stratifications (optional)
     - evidence requirements: what must be shown
5) Time windows:
   - Support measurement year, lookback windows (e.g., 12 months), rolling periods, age as of date
6) Multi-source evidence:
   - Accept claims-like codes (CPT/HCPCS/ICD) plus clinical text events (labs/vitals)
7) Output contract:
   - For each measure, return:
     - applicable: boolean
     - eligibility_reason: structured list
     - compliant: boolean/unknown
     - compliance_reason: structured list
     - gaps: structured list
     - evidence_used: list of {type, code, date, source_ref}
     - missing_data: list of needed events/codes
     - confidence: deterministic score (not ML), based on evidence strength and completeness

RESEARCH INSTRUCTIONS
You must research and compile a “measure catalog” using public descriptions (e.g., publicly described HEDIS measures, CMS quality measure descriptions, payer public docs). Do NOT paste licensed NCQA spec text. Summarize measure intent and implement the engine skeleton for each.
For each measure, identify:
- Age/sex eligibility
- Core numerator event(s)
- Major exclusions (if publicly known; otherwise placeholder)
- Evidence signals available from our extractor (codes, labs, vitals, meds)
- Value sets needed (as placeholders with descriptive names)
Cite sources in documentation files (not in code comments if that risks license text).

IMPLEMENTATION PLAN (DO THIS IN ORDER)
Step 1: Create project structure
- hedis_engine/
  - engine.py (rule evaluator)
  - types.py (dataclasses/pydantic models)
  - catalog/ (measure defs)
  - valuesets/ (placeholder valuesets)
  - adapters/ (convert upstream assertions JSON into normalized events)
  - tests/ (golden tests)
  - docs/ (catalog tables + sources)

Step 2: Build normalized event model
Convert upstream assertions into normalized events:
- DiagnosisEvent: {code_system, code, date, status, evidence_ref}
- ProcedureEvent: {cpt/hcpcs, date, evidence_ref}
- LabEvent: {test_type, value, unit, date, evidence_ref}
- VitalEvent: {type (BP), systolic, diastolic, date, evidence_ref}
- MedicationEvent: {name, normalized_class(optional), start_date, end_date(optional), evidence_ref}
- EncounterEvent: {type, date}
- Demographics: {dob, gender}

Step 3: Implement rule primitives
Implement reusable primitives:
- age_between(as_of_date, min, max)
- gender_in(set)
- has_code(valueset_id, within_window)
- has_procedure(valueset_id, within_window)
- has_diagnosis(valueset_id, within_window, status=active)
- lab_exists(test_type, within_window)
- lab_value_in_range(test_type, comparator, threshold, within_window)
- bp_controlled(thresholds, within_window, rule=lowest/latest)
- medication_present(class_or_valueset, within_window)
- continuous_enrollment(check stub; allow external enrollment feed later)

Step 4: Implement measure evaluation
Given measurement_year, evaluate:
- applicability (eligibility rules)
- denominator inclusion
- exclusions
- numerator compliance
- produce trace + evidence used + gaps

Step 5: Create measure definition schema (YAML/JSON)
Example (conceptual):
- id: "CDC-A1C"
- name: "Diabetes Care - HbA1c Testing"
- eligibility:
  - age: {min: 18, max: 75, as_of: "12-31"}
  - requires_condition: "VS_DIABETES_ICD10"
- numerator:
  - requires_lab: {type: "A1C", within_months: 12}
- exclusions:
  - hospice: "VS_HOSPICE"
  - pregnancy: "VS_PREGNANCY"
- valuesets:
  - VS_DIABETES_ICD10
  - VS_A1C_TEST
  - VS_HOSPICE
Return trace: which events satisfied which clause.

Step 6: Populate top 30 measures (then extend to 50)
For each measure, create:
- catalog/<measure_id>.yaml
- define needed valuesets placeholders
Also generate a docs table listing all measures, eligibility, numerator event, exclusions, required data.

Step 7: Write tests
- Create synthetic member event sets that should pass/fail each measure.
- Add regression tests for:
  - DOB/gender eligibility edge cases
  - multiple encounters and multiple dates
  - missing lab values
  - conflicting evidence (negated diagnosis vs active)
- Add “golden output” snapshots for a few representative measures.

Step 8: Integrate with upstream extractor outputs
Write an adapter:
- input: upstream JSON file (assertions)
- output: normalized event store
Then run measures for a member and emit:
- hedis_results.json (per measure)
- hedis_results_summary.md (counts: applicable/compliant/gaps)

QUALITY TARGETS
- Engine must never crash on missing data.
- Must distinguish:
  - not applicable vs applicable-but-noncompliant vs indeterminate (missing data)
- Must show evidence citations:
  - include pdf/page/exact_quote refs in evidence_used.

IMPORTANT DOMAIN RULES TO IMPLEMENT
- Age and gender gating is mandatory.
- Time windows must be explicit and correct.
- Latest-vs-best BP logic must be deterministic (pick “latest BP in period” unless otherwise configured).
- A1c control measures must handle both “test exists” and “value threshold” variants.
- Screening measures must accept multiple procedure modalities (colonoscopy vs FIT vs sigmoidoscopy) using valuesets.
- Immunization measures must handle series counts; if series logic is too complex without immunization registries, implement as:
  - evidence of required vaccine codes present count >= N with date constraints, else “indeterminate”.

DELIVERABLES
1) A runnable package:
   python -m hedis_engine.run --input ./member_assertions.json --year 2025 --out ./hedis_results.json
2) A complete catalog table:
   docs/measure_catalog.md (30–50 measures, eligibility summary, numerator, exclusions, required data, valuesets placeholders)
3) Placeholder valuesets:
   valuesets/*.json with descriptive names and example codes (marked as placeholders)
4) Tests:
   pytest suite with coverage of at least 30 measures.

OUTPUT FORMATS
hedis_results.json example:
{
  "member_id": "...",
  "measurement_year": 2025,
  "measures": [
    {
      "id": "CDC-A1C-TEST",
      "applicable": true,
      "compliant": false,
      "status": "gap",
      "eligibility_reason": [...],
      "compliance_reason": [...],
      "gaps": [
        {"type":"missing_lab","lab":"A1C","window":"2024-01-01..2024-12-31"}
      ],
      "evidence_used": [
        {"type":"diagnosis","code":"E11.9","system":"icd10cm","date":"2024-07-23","source":{"pdf":"...","page":1}}
      ],
      "missing_data": [...],
      "trace": {...}
    }
  ]
}

HARD RULE: GENERIC, NOT HARD-CODED
Do not build “if measure == X do weird thing.” Build primitives + data-driven YAML definitions.

BEGIN
- Inspect repo, create hedis_engine module as above.
- Build evaluator and tests.
- Populate 30 measures with structured definitions + placeholders.
- Produce documentation + runnable CLI.
- Ensure deterministic, auditable outputs.