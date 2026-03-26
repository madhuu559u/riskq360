# HEDIS Measure Catalog

> **35 measures implemented** across 8 clinical domains.
> All measure definitions are data-driven YAML files in `catalog/`.
> Value sets are placeholders — replace with official NCQA-licensed sets for production.
>
> Public descriptions are based on CMS quality measure summaries and publicly available
> HEDIS measure descriptions. No NCQA-licensed specification text is reproduced.

## Measures by Domain

### Diabetes Care (6 measures)

| ID | Name | Age | Gender | Denominator | Numerator | Key Value Sets |
|----|------|-----|--------|-------------|-----------|----------------|
| CDC-A1C-TEST | HbA1c Testing | 18-75 | All | Diabetes Dx | A1C lab exists (12 mo) | VS_DIABETES_ICD10 |
| CDC-A1C-CONTROL-8 | HbA1c Control (<8%) | 18-75 | All | Diabetes Dx | A1C < 8.0 (12 mo) | VS_DIABETES_ICD10 |
| CDC-A1C-POOR-9 | HbA1c Poor Control (>9%) | 18-75 | All | Diabetes Dx | A1C > 9.0 (inverse) | VS_DIABETES_ICD10 |
| CDC-EYE | Eye Exam | 18-75 | All | Diabetes Dx | Eye exam procedure (24 mo) | VS_EYE_EXAM_CPT |
| CDC-NEPHROPATHY | Nephropathy Screening | 18-75 | All | Diabetes Dx | Nephropathy screen OR ACE/ARB | VS_NEPHROPATHY_SCREENING |
| CDC-STATIN | Statin Therapy | 40-75 | All | Diabetes Dx | Statin medication present | VS_STATIN_MEDICATIONS |

### Cardiovascular / Blood Pressure (1 measure)

| ID | Name | Age | Gender | Denominator | Numerator | Key Value Sets |
|----|------|-----|--------|-------------|-----------|----------------|
| CBP | Controlling High Blood Pressure | 18-85 | All | Hypertension Dx | BP < 140/90 (latest) | VS_HYPERTENSION_ICD10 |

### Preventive Screening (5 measures)

| ID | Name | Age | Gender | Denominator | Numerator | Key Value Sets |
|----|------|-----|--------|-------------|-----------|----------------|
| COL | Colorectal Cancer Screening | 45-75 | All | Population | Colonoscopy (10yr) OR FIT (1yr) OR Sig (5yr) | VS_COLONOSCOPY_CPT, VS_FIT_TEST_CPT |
| BCS | Breast Cancer Screening | 50-74 | Female | Population | Mammogram (27 mo) | VS_MAMMOGRAPHY_CPT |
| CCS | Cervical Cancer Screening | 21-64 | Female | Population | Cervical screen (36 mo) | VS_CERVICAL_SCREENING_CPT |
| CHL | Chlamydia Screening | 16-24 | Female | Population | Chlamydia test (12 mo) | VS_CHLAMYDIA_SCREENING_CPT |
| BMI | Adult BMI Assessment | 18-74 | All | Outpatient encounter | BMI documented (12 mo) | — |

### Immunization — Adult (2 measures)

| ID | Name | Age | Gender | Denominator | Numerator | Key Value Sets |
|----|------|-----|--------|-------------|-----------|----------------|
| FLU | Influenza Immunization | All | All | Population | Flu vaccine (12 mo) | VS_FLU_VACCINE_CVX |
| PNU | Pneumococcal Immunization | 65+ | All | Population | Pneumo vaccine (any time) | VS_PNEUMOCOCCAL_VACCINE_CVX |

### Immunization — Childhood (9 measures)

| ID | Name | Age | Doses Required |
|----|------|-----|---------------|
| CIS-DTAP | DTaP | 2 | 4 |
| CIS-POLIO | Polio (IPV) | 2 | 3 |
| CIS-MMR | MMR | 2 | 1 |
| CIS-HIB | Hib | 2 | 3 |
| CIS-HEPB | Hepatitis B | 2 | 3 |
| CIS-VZV | Varicella | 2 | 1 |
| CIS-PCV | PCV13 | 2 | 4 |
| CIS-HEPA | Hepatitis A | 2 | 1 |
| CIS-RV | Rotavirus | 2 | 2 |

### Immunization — Adolescent (3 measures)

| ID | Name | Age | Doses Required |
|----|------|-----|---------------|
| IMA-HPV | HPV | 13 | 2 |
| IMA-MENING | Meningococcal | 13 | 1 |
| IMA-TDAP | Tdap | 13 | 1 |

### Behavioral Health (5 measures)

| ID | Name | Age | Gender | Denominator | Numerator |
|----|------|-----|--------|-------------|-----------|
| DSF | Depression Screening & Follow-Up | 12+ | All | Outpatient encounter | Depression screening (12 mo) |
| AMM-ACUTE | Antidepressant Mgmt — Acute | 18+ | All | Depression Dx | Antidepressant (3 mo) |
| AMM-CONTINUATION | Antidepressant Mgmt — Continuation | 18+ | All | Depression Dx | Antidepressant (6 mo) |
| FUH-7 | Follow-Up After MH Hospitalization (7d) | 6+ | All | MH Dx | Outpatient visit (1 mo approx) |
| FUH-30 | Follow-Up After MH Hospitalization (30d) | 6+ | All | MH Dx | Outpatient visit (1 mo approx) |

### Tobacco & Lifestyle (1 measure)

| ID | Name | Age | Gender | Numerator |
|----|------|-----|--------|-----------|
| TSC | Tobacco Screening & Cessation | 18+ | All | Tobacco screen OR cessation (24 mo) |

### Pediatric / Well Visits (2 measures)

| ID | Name | Age | Gender | Numerator |
|----|------|-----|--------|-----------|
| WCV | Well-Child Visits | 3-11 | All | Well-child visit procedure (12 mo) |
| AWC | Adolescent Well-Care | 12-21 | All | Adolescent visit procedure (12 mo) |

### Musculoskeletal (1 measure)

| ID | Name | Age | Gender | Numerator |
|----|------|-----|--------|-----------|
| OMW | Osteoporosis Mgmt in Women | 67-85 | Female | DEXA scan (24 mo) OR osteoporosis med |

## Common Exclusions

Most measures include:
- **Hospice care** (VS_HOSPICE) — standard HEDIS exclusion
- **Pregnancy** (VS_PREGNANCY_ICD10) — for diabetes and hypertension measures

## Value Sets Summary

50 placeholder value set files are provided in `valuesets/`. Each contains representative codes marked as `placeholder: true`. Replace with official NCQA-licensed value sets for production use.

### Value Set Categories
- **Diagnosis codes** (ICD-10-CM): 12 value sets
- **Procedure codes** (CPT/HCPCS): 16 value sets
- **Vaccine codes** (CVX): 14 value sets
- **Medication codes** (RxNorm/NDC): 6 value sets
- **Exclusion codes**: 2 value sets

## Data Sources

The engine accepts clinical evidence from:
1. **Claims data** — diagnosis codes, procedure codes, service dates
2. **Lab results** — test type, value, unit, date
3. **Vitals** — blood pressure, BMI, weight, height
4. **Medications** — drug name, class, start/end dates
5. **Immunization registries** — vaccine type, CVX code, date, dose number
6. **Encounter records** — visit type, date, provider

## Public References

Measure descriptions are based on publicly available information from:
- CMS Quality Payment Program measure specifications (qpp.cms.gov)
- CDC Advisory Committee on Immunization Practices (ACIP) schedules
- USPSTF screening recommendations
- ADA Standards of Medical Care in Diabetes
- ACC/AHA Hypertension Guidelines

No NCQA-licensed specification text has been reproduced.
