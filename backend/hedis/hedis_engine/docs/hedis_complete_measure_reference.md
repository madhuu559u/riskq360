# Complete NCQA HEDIS Measure Reference

> **Research compiled: March 2026**
> Covers HEDIS Measurement Years 2024, 2025, and 2026.
> Based on publicly available descriptions from NCQA, CMS, health plan provider guides,
> and public quality measure documentation. No NCQA-licensed specification text is
> reproduced verbatim. Placeholder notes indicate where official value sets are needed.

---

## Table of Contents

1. [Overview and Structure](#overview)
2. [Domain 1: Effectiveness of Care](#effectiveness-of-care)
3. [Domain 2: Access/Availability of Care](#access-availability)
4. [Domain 3: Experience of Care (CAHPS)](#experience-of-care)
5. [Domain 4: Utilization and Risk-Adjusted Utilization](#utilization)
6. [Domain 5: Health Plan Descriptive Information](#descriptive-info)
7. [Domain 6: Measures Reported Using ECDS](#ecds-measures)
8. [Retired Measures (2024-2026)](#retired-measures)
9. [Summary Count and Index](#summary)
10. [Sources](#sources)

---

## <a name="overview"></a>1. Overview and Structure

HEDIS (Healthcare Effectiveness Data and Information Set) is developed and maintained by
NCQA (National Committee for Quality Assurance). It is used by more than 90% of U.S. health
plans, covering approximately 235 million enrolled people. HEDIS contains **90+ measures**
across **6 domains** of care.

### Product Lines
- **C** = Commercial (HMO/POS, PPO)
- **MCD** = Medicaid
- **MCR** = Medicare
- **MP** = Medicare-Medicaid Plan (MMP)

### Reporting Methods
- **Administrative** (claims/encounter data only)
- **Hybrid** (claims + medical record review)
- **ECDS** (Electronic Clinical Data Systems -- structured clinical data)

### Key Terminology
- **Measurement Year (MY)**: The calendar year during which performance is assessed (e.g., MY 2025 = Jan 1 - Dec 31, 2025)
- **Denominator**: The eligible population for the measure
- **Numerator**: The subset of the denominator that met the measure criteria
- **Exclusions**: Conditions that remove a member from the denominator
- **Lookback Period**: Time window for evidence (varies by measure)

---

## <a name="effectiveness-of-care"></a>2. Domain 1: Effectiveness of Care

### 2.1 Prevention and Screening

#### BCS / BCS-E -- Breast Cancer Screening
| Field | Value |
|-------|-------|
| **Abbreviation** | BCS (Admin/Hybrid), BCS-E (ECDS) |
| **Full Name** | Breast Cancer Screening |
| **Domain** | Effectiveness of Care -- Prevention and Screening |
| **Age Range** | 50-74 years (as of December 31 of MY) |
| **Gender** | Female (updated for gender inclusivity in recent years) |
| **Denominator** | Women 50-74 enrolled during MY |
| **Numerator** | One or more mammograms during MY or the year prior (27-month lookback for ECDS) |
| **Key Exclusions** | Bilateral mastectomy; unilateral mastectomy with bilateral SNOMED qualifier (updated MY 2026); hospice; advanced illness |
| **Sub-measures** | None |
| **Data Sources** | Claims (CPT/HCPCS), medical records, ECDS |
| **Product Lines** | C, MCD, MCR |

#### CCS / CCS-E -- Cervical Cancer Screening
| Field | Value |
|-------|-------|
| **Abbreviation** | CCS-E (ECDS only as of MY 2025) |
| **Full Name** | Cervical Cancer Screening |
| **Age Range** | 21-64 years |
| **Gender** | Female |
| **Denominator** | Women 21-64 enrolled during MY |
| **Numerator** | Cervical cytology (Pap) within prior 3 years (ages 21-64) OR HPV test within prior 5 years (ages 30-64) OR HPV/cytology co-test within prior 5 years (ages 30-64) |
| **Key Exclusions** | Hysterectomy with no residual cervix; hospice; advanced illness |
| **Sub-measures** | None |
| **Data Sources** | ECDS (ECDS-only as of MY 2025) |
| **Product Lines** | C, MCD, MCR |

#### COL / COL-E -- Colorectal Cancer Screening
| Field | Value |
|-------|-------|
| **Abbreviation** | COL (Admin/Hybrid), COL-E (ECDS) |
| **Full Name** | Colorectal Cancer Screening |
| **Age Range** | 45-75 years |
| **Gender** | All |
| **Denominator** | Members 45-75 enrolled during MY |
| **Numerator** | Any of: Colonoscopy within prior 10 years; Flexible sigmoidoscopy within prior 5 years; FIT/FOBT within prior 1 year; FIT-DNA within prior 3 years; CT colonography within prior 5 years |
| **Key Exclusions** | Colorectal cancer; total colectomy; hospice; advanced illness |
| **Sub-measures** | None |
| **Data Sources** | Claims, medical records, ECDS |
| **Product Lines** | C, MCD, MCR |

#### CHL -- Chlamydia Screening
| Field | Value |
|-------|-------|
| **Abbreviation** | CHL |
| **Full Name** | Chlamydia Screening (formerly "Chlamydia Screening in Women") |
| **Age Range** | 16-24 years |
| **Gender** | Female (updated MY 2025 for gender inclusivity to include transgender members) |
| **Denominator** | Sexually active women/eligible members 16-24 |
| **Numerator** | At least one chlamydia test during MY |
| **Key Exclusions** | Hospice; pregnancy-related exclusions vary |
| **Sub-measures** | None |
| **Data Sources** | Claims (lab CPT codes) |
| **Product Lines** | C, MCD |

#### LSC / LSC-E -- Lead Screening in Children
| Field | Value |
|-------|-------|
| **Abbreviation** | LSC-E (ECDS-only as of MY 2026) |
| **Full Name** | Lead Screening in Children |
| **Age Range** | Children who turn 2 years old during MY |
| **Gender** | All |
| **Denominator** | Children turning age 2 during MY |
| **Numerator** | At least one capillary or venous blood lead test by age 2 |
| **Key Exclusions** | Hospice |
| **Sub-measures** | None |
| **Data Sources** | ECDS (previously admin/hybrid; transitioned MY 2026) |
| **Product Lines** | MCD |

#### DBM-E -- Documented BI-RADS Assessment After Mammogram
| Field | Value |
|-------|-------|
| **Abbreviation** | DBM-E |
| **Full Name** | Documented BI-RADS Assessment After Mammogram |
| **Age Range** | 40-74 years |
| **Gender** | Female |
| **Denominator** | Episodes of mammograms during MY for women 40-74 |
| **Numerator** | BI-RADS assessment documented within 14 days of mammogram |
| **Key Exclusions** | Hospice; bilateral mastectomy |
| **Sub-measures** | None |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |
| **Notes** | New measure added MY 2025 |

#### FMA-E / FAM-E -- Follow-Up After Abnormal Mammogram Assessment
| Field | Value |
|-------|-------|
| **Abbreviation** | FMA-E / FAM-E |
| **Full Name** | Follow-Up After Abnormal Mammogram Assessment |
| **Age Range** | 40-74 years |
| **Gender** | Female |
| **Denominator** | Episodes with inconclusive or high-risk BI-RADS assessments |
| **Numerator** | Appropriate follow-up within 90 days of assessment |
| **Key Exclusions** | Hospice; bilateral mastectomy |
| **Sub-measures** | None |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |
| **Notes** | New measure added MY 2025 |

#### PSA -- Non-Recommended PSA-Based Screening in Older Men
| Field | Value |
|-------|-------|
| **Abbreviation** | PSA |
| **Full Name** | Non-Recommended PSA-Based Screening in Older Men |
| **Age Range** | 70+ years |
| **Gender** | Male |
| **Denominator** | Men 70+ enrolled during MY |
| **Numerator** | PSA test during MY (lower rate = better performance -- inverse measure) |
| **Key Exclusions** | Prostate cancer diagnosis; hospice |
| **Sub-measures** | None |
| **Data Sources** | Claims |
| **Product Lines** | MCR |

### 2.2 Immunizations

#### CIS / CIS-E -- Childhood Immunization Status
| Field | Value |
|-------|-------|
| **Abbreviation** | CIS-E (ECDS-only as of MY 2025) |
| **Full Name** | Childhood Immunization Status |
| **Age Range** | Children who turn 2 years old during MY |
| **Gender** | All |
| **Denominator** | Children turning age 2 during MY |
| **Numerator** | Completion of required vaccines by age 2 |
| **Key Exclusions** | Hospice; contraindication to specific vaccines (anaphylaxis, encephalopathy) |
| **Sub-measures/Indicators** | Combo 3 (DTaP, IPV, MMR, HiB, HepB, VZV, PCV), Combo 10 (adds HepA, Rotavirus, Influenza) |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD |
| **Vaccine Components** | DTaP (4 doses), IPV (3 doses), MMR (1 dose), HiB (3 doses), HepB (3 doses), VZV (1 dose), PCV (4 doses), HepA (1 dose), Rotavirus (2-3 doses), Influenza (2 doses) |

#### IMA / IMA-E -- Immunizations for Adolescents
| Field | Value |
|-------|-------|
| **Abbreviation** | IMA-E (ECDS-only as of MY 2025) |
| **Full Name** | Immunizations for Adolescents |
| **Age Range** | 13 years old during MY |
| **Gender** | All |
| **Denominator** | Adolescents turning 13 during MY |
| **Numerator** | Completion of required adolescent vaccines |
| **Key Exclusions** | Hospice; anaphylaxis/contraindication |
| **Sub-measures/Indicators** | Combo 1 (Meningococcal + Tdap), Combo 2 (Combo 1 + HPV) |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD |
| **Vaccine Components** | Meningococcal (1 dose), Tdap (1 dose), HPV (2-3 doses) |

#### AIS-E -- Adult Immunization Status
| Field | Value |
|-------|-------|
| **Abbreviation** | AIS-E |
| **Full Name** | Adult Immunization Status |
| **Age Range** | 19+ years (updated age bands in MY 2025/2026) |
| **Gender** | All |
| **Denominator** | Adults 19+ enrolled during MY |
| **Numerator** | Completion of age-appropriate vaccines |
| **Key Exclusions** | Hospice; contraindications |
| **Sub-measures/Indicators** | Influenza, Td/Tdap, Herpes Zoster (50+), Pneumococcal (65+), Hepatitis B (19-59; added MY 2025), COVID-19 (65+; added MY 2026) |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |

#### PRS-E -- Prenatal Immunization Status
| Field | Value |
|-------|-------|
| **Abbreviation** | PRS-E |
| **Full Name** | Prenatal Immunization Status |
| **Age Range** | Pregnant women of any age |
| **Gender** | Female |
| **Denominator** | Live deliveries during MY |
| **Numerator** | Influenza and Tdap vaccination during pregnancy |
| **Key Exclusions** | Hospice; contraindications |
| **Sub-measures** | Influenza indicator, Tdap indicator, combined |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD |

### 2.3 Respiratory Conditions

#### AMR -- Asthma Medication Ratio (RETIRED MY 2026)
| Field | Value |
|-------|-------|
| **Abbreviation** | AMR |
| **Full Name** | Asthma Medication Ratio |
| **Age Range** | 5-64 years |
| **Gender** | All |
| **Denominator** | Persistent asthma members with asthma medication dispensing events |
| **Numerator** | Ratio of controller medications to total asthma medications >= 0.50 |
| **Key Exclusions** | COPD; emphysema; cystic fibrosis; acute respiratory failure; hospice |
| **Data Sources** | Claims (pharmacy) |
| **Product Lines** | C, MCD, MCR |
| **Status** | **RETIRED effective MY 2026** -- replaced by AAF-E |

#### AAF-E -- Follow-Up After Acute and Urgent Care Visits for Asthma
| Field | Value |
|-------|-------|
| **Abbreviation** | AAF-E |
| **Full Name** | Follow-Up After Acute and Urgent Care Visits for Asthma |
| **Age Range** | 5-64 years |
| **Gender** | All |
| **Denominator** | ED visits, urgent care visits, acute inpatient stays, or observation discharges for asthma |
| **Numerator** | Appropriate follow-up visit within specified timeframe after acute/urgent care |
| **Key Exclusions** | Hospice; COPD |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |
| **Notes** | New measure added MY 2026, replacing AMR |

#### CWP -- Appropriate Testing for Pharyngitis
| Field | Value |
|-------|-------|
| **Abbreviation** | CWP |
| **Full Name** | Appropriate Testing for Pharyngitis (also known as Appropriate Testing for Children with Pharyngitis) |
| **Age Range** | 3-17 years |
| **Gender** | All |
| **Denominator** | Children with pharyngitis/sore throat episode and antibiotic dispensing |
| **Numerator** | Group A strep test performed in the 3 days prior to or on the date of the antibiotic dispensing event |
| **Key Exclusions** | Competing diagnosis (e.g., peritonsillar abscess); hospice |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD |

#### URI -- Appropriate Treatment for Upper Respiratory Infection
| Field | Value |
|-------|-------|
| **Abbreviation** | URI |
| **Full Name** | Appropriate Treatment for Upper Respiratory Infection |
| **Age Range** | 3 months to 17 years |
| **Gender** | All |
| **Denominator** | Children with URI diagnosis during MY |
| **Numerator** | Percentage who were NOT prescribed an antibiotic within 3 days (higher = better -- inverse measure) |
| **Key Exclusions** | Competing bacterial diagnosis; hospice |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD |

#### AAB -- Avoidance of Antibiotic Treatment for Acute Bronchitis/Bronchiolitis
| Field | Value |
|-------|-------|
| **Abbreviation** | AAB |
| **Full Name** | Avoidance of Antibiotic Treatment for Acute Bronchitis/Bronchiolitis |
| **Age Range** | 3 months and older |
| **Gender** | All |
| **Denominator** | Members with acute bronchitis/bronchiolitis diagnosis |
| **Numerator** | Percentage NOT dispensed an antibiotic within 3 days (higher = better -- inverse measure) |
| **Key Exclusions** | Competing bacterial diagnosis; hospice; COPD; HIV |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD |

#### PCE -- Pharmacotherapy Management of COPD Exacerbation
| Field | Value |
|-------|-------|
| **Abbreviation** | PCE |
| **Full Name** | Pharmacotherapy Management of COPD Exacerbation |
| **Age Range** | 40+ years |
| **Gender** | All |
| **Denominator** | Members 40+ discharged from inpatient for COPD exacerbation or had ED visit for COPD exacerbation |
| **Numerator** | Dispensed systemic corticosteroid AND/OR bronchodilator within 30 days of event |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Rate 1: Systemic corticosteroid within 14 days of event; Rate 2: Bronchodilator within 30 days |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

### 2.4 Cardiovascular Conditions

#### CBP -- Controlling High Blood Pressure
| Field | Value |
|-------|-------|
| **Abbreviation** | CBP |
| **Full Name** | Controlling High Blood Pressure |
| **Age Range** | 18-85 years |
| **Gender** | All |
| **Denominator** | Members 18-85 with hypertension diagnosis |
| **Numerator** | Blood pressure adequately controlled (< 140/90 mmHg) during MY |
| **Key Exclusions** | ESRD; kidney transplant; pregnancy; hospice; advanced illness; non-acute inpatient admission |
| **Sub-measures** | None |
| **Data Sources** | Hybrid (admin + medical record), transitioning to ECDS |
| **Product Lines** | C, MCD, MCR |
| **Notes** | Being replaced by BPC-E / BPH-E over time |

#### BPC-E / BPH-E -- Blood Pressure Control for Patients with Hypertension
| Field | Value |
|-------|-------|
| **Abbreviation** | BPC-E / BPH-E |
| **Full Name** | Blood Pressure Control for Patients with Hypertension |
| **Age Range** | 18-85 years |
| **Gender** | All |
| **Denominator** | Members 18-85 with hypertension diagnosis (expanded criteria vs. CBP) |
| **Numerator** | Blood pressure adequately controlled (< 140/90 mmHg) |
| **Key Exclusions** | ESRD; kidney transplant; pregnancy; hospice |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |
| **Notes** | New ECDS measure added MY 2025; will eventually replace hybrid CBP |

#### SPC / SPC-E -- Statin Therapy for Patients with Cardiovascular Disease
| Field | Value |
|-------|-------|
| **Abbreviation** | SPC-E (ECDS-only as of MY 2026) |
| **Full Name** | Statin Therapy for Patients with Cardiovascular Disease |
| **Age Range** | 21-75 years (sex-specific age bands removed MY 2026) |
| **Gender** | All |
| **Denominator** | Members with ASCVD (atherosclerotic cardiovascular disease) |
| **Numerator** | Received statin therapy during MY |
| **Key Exclusions** | ESRD; cirrhosis; myalgia/myopathy/rhabdomyolysis; hospice; pregnancy |
| **Sub-measures** | Rate 1: Received statin therapy; Rate 2: Statin adherence (80% PDC) |
| **Data Sources** | ECDS (previously admin; transitioned MY 2026) |
| **Product Lines** | C, MCD, MCR |

### 2.5 Diabetes Care

#### HBD -- Hemoglobin A1c Control for Patients with Diabetes
| Field | Value |
|-------|-------|
| **Abbreviation** | HBD |
| **Full Name** | Hemoglobin A1c Control for Patients with Diabetes (formerly part of CDC) |
| **Age Range** | 18-75 years |
| **Gender** | All |
| **Denominator** | Members 18-75 with diabetes (type 1 and type 2) |
| **Numerator** | HbA1c testing AND/OR HbA1c control at various thresholds |
| **Key Exclusions** | Hospice; advanced illness; pregnancy (gestational diabetes excluded) |
| **Sub-measures** | HbA1c Testing (test exists); HbA1c Poor Control > 9% (inverse -- lower is better); HbA1c Control < 8% |
| **Data Sources** | Hybrid, ECDS |
| **Product Lines** | C, MCD, MCR |
| **Notes** | Separated from CDC (Comprehensive Diabetes Care) in ~MY 2022 |

#### EED -- Eye Exam for Patients with Diabetes
| Field | Value |
|-------|-------|
| **Abbreviation** | EED |
| **Full Name** | Eye Exam for Patients with Diabetes |
| **Age Range** | 18-75 years |
| **Gender** | All |
| **Denominator** | Members 18-75 with diabetes (type 1 and type 2) |
| **Numerator** | Retinal eye exam performed by an eye care professional during MY or prior year |
| **Key Exclusions** | Hospice; advanced illness |
| **Sub-measures** | None |
| **Data Sources** | Administrative (claims only as of MY 2025; hybrid reporting eliminated) |
| **Product Lines** | C, MCD, MCR |

#### KED -- Kidney Health Evaluation for Patients with Diabetes
| Field | Value |
|-------|-------|
| **Abbreviation** | KED |
| **Full Name** | Kidney Health Evaluation for Patients with Diabetes |
| **Age Range** | 18-85 years |
| **Gender** | All |
| **Denominator** | Members 18-85 with diabetes (type 1 and type 2) |
| **Numerator** | Kidney health evaluation (both estimated GFR and urine albumin-creatinine ratio) during MY |
| **Key Exclusions** | ESRD; dialysis; kidney transplant; hospice; advanced illness |
| **Sub-measures** | None |
| **Data Sources** | Administrative, ECDS |
| **Product Lines** | C, MCD, MCR |

#### SPD / SPD-E -- Statin Therapy for Patients with Diabetes
| Field | Value |
|-------|-------|
| **Abbreviation** | SPD-E (ECDS-only as of MY 2026) |
| **Full Name** | Statin Therapy for Patients with Diabetes |
| **Age Range** | 40-75 years (sex-specific age bands removed MY 2026) |
| **Gender** | All |
| **Denominator** | Members 40-75 with diabetes (type 1 or type 2) |
| **Numerator** | Received statin therapy during MY |
| **Key Exclusions** | ESRD; cirrhosis; myalgia/myopathy/rhabdomyolysis; hospice; pregnancy |
| **Sub-measures** | Rate 1: Received statin therapy; Rate 2: Statin adherence (80% PDC) |
| **Data Sources** | ECDS (previously admin; transitioned MY 2026) |
| **Product Lines** | C, MCD, MCR |

#### BPD-E -- Blood Pressure Control for Patients with Diabetes
| Field | Value |
|-------|-------|
| **Abbreviation** | BPD-E |
| **Full Name** | Blood Pressure Control for Patients with Diabetes |
| **Age Range** | 18-75 years |
| **Gender** | All |
| **Denominator** | Members 18-75 with diabetes (type 1 and type 2) |
| **Numerator** | Blood pressure adequately controlled (< 140/90 mmHg) |
| **Key Exclusions** | ESRD; kidney transplant; pregnancy; hospice |
| **Data Sources** | ECDS (voluntary ECDS reporting as of MY 2026) |
| **Product Lines** | C, MCD, MCR |

### 2.6 Behavioral Health

#### DSF-E -- Depression Screening and Follow-Up for Adolescents and Adults
| Field | Value |
|-------|-------|
| **Abbreviation** | DSF-E |
| **Full Name** | Depression Screening and Follow-Up for Adolescents and Adults |
| **Age Range** | 12+ years |
| **Gender** | All |
| **Denominator** | Members 12+ with an outpatient encounter during MY |
| **Numerator** | Screened for depression using a standardized tool AND follow-up plan documented if positive |
| **Key Exclusions** | Active depression diagnosis or bipolar disorder; hospice |
| **Sub-measures** | Screening rate; Follow-up rate for positive screens |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |
| **Notes** | MY 2026 allows PROMIS Emotional Distress tool for adults 18+ |

#### DMS-E -- Utilization of the PHQ-9 to Monitor Depression Symptoms
| Field | Value |
|-------|-------|
| **Abbreviation** | DMS-E |
| **Full Name** | Utilization of the PHQ-9 to Monitor Depression Symptoms for Adolescents and Adults |
| **Age Range** | 12+ years |
| **Gender** | All |
| **Denominator** | Members 12+ with new depression diagnosis or episode |
| **Numerator** | PHQ-9 administered within specified intervals after diagnosis/treatment initiation |
| **Key Exclusions** | Hospice; bipolar disorder |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |

#### DRR-E -- Depression Remission or Response for Adolescents and Adults
| Field | Value |
|-------|-------|
| **Abbreviation** | DRR-E |
| **Full Name** | Depression Remission or Response for Adolescents and Adults |
| **Age Range** | 12+ years |
| **Gender** | All |
| **Denominator** | Members 12+ with new depression diagnosis and elevated PHQ-9 score |
| **Numerator** | Remission (PHQ-9 < 5) or Response (50%+ reduction in PHQ-9) at follow-up |
| **Key Exclusions** | Hospice; bipolar disorder; personality disorder |
| **Sub-measures** | Remission rate; Response rate |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |

#### PND-E -- Prenatal Depression Screening and Follow-Up
| Field | Value |
|-------|-------|
| **Abbreviation** | PND-E |
| **Full Name** | Prenatal Depression Screening and Follow-Up |
| **Age Range** | Any age (pregnant women) |
| **Gender** | Female |
| **Denominator** | Deliveries during MY |
| **Numerator** | Depression screening during pregnancy with follow-up if positive |
| **Key Exclusions** | Active depression/bipolar diagnosis |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD |

#### PDS-E -- Postpartum Depression Screening and Follow-Up
| Field | Value |
|-------|-------|
| **Abbreviation** | PDS-E |
| **Full Name** | Postpartum Depression Screening and Follow-Up |
| **Age Range** | Any age (postpartum women) |
| **Gender** | Female |
| **Denominator** | Deliveries during MY |
| **Numerator** | Depression screening within 7-84 days postpartum with follow-up if positive |
| **Key Exclusions** | Active depression/bipolar diagnosis |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD |

#### ASF-E -- Unhealthy Alcohol Use Screening and Follow-Up
| Field | Value |
|-------|-------|
| **Abbreviation** | ASF-E |
| **Full Name** | Unhealthy Alcohol Use Screening and Follow-Up |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ with an outpatient encounter during MY |
| **Numerator** | Screened for unhealthy alcohol use AND brief counseling or follow-up if positive |
| **Key Exclusions** | Hospice; dementia |
| **Sub-measures** | Screening rate; Brief counseling/intervention for positive screens |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |

#### ADD / ADD-E -- Follow-Up Care for Children Prescribed ADHD Medication
| Field | Value |
|-------|-------|
| **Abbreviation** | ADD-E (ECDS) |
| **Full Name** | Follow-Up Care for Children Prescribed ADHD Medication |
| **Age Range** | 6-12 years |
| **Gender** | All |
| **Denominator** | Children 6-12 newly prescribed ADHD medication |
| **Numerator** | Follow-up visit with prescriber within 30 days (Initiation Phase); at least 2 additional visits within 9 months (Continuation Phase) |
| **Key Exclusions** | Prior ADHD medication in lookback period; narcolepsy; hospice |
| **Sub-measures** | Rate 1: Initiation Phase (30-day follow-up); Rate 2: Continuation Phase |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD |

#### APM / APM-E -- Metabolic Monitoring for Children and Adolescents on Antipsychotics
| Field | Value |
|-------|-------|
| **Abbreviation** | APM-E (ECDS) |
| **Full Name** | Metabolic Monitoring for Children and Adolescents on Antipsychotics |
| **Age Range** | 1-17 years |
| **Gender** | All |
| **Denominator** | Children/adolescents 1-17 on antipsychotic medications |
| **Numerator** | Received glucose/HbA1c test AND cholesterol test during MY |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Blood glucose testing rate; Cholesterol testing rate; Both (combined) |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD |

#### APP -- Use of First-Line Psychosocial Care for Children and Adolescents on Antipsychotics
| Field | Value |
|-------|-------|
| **Abbreviation** | APP |
| **Full Name** | Use of First-Line Psychosocial Care for Children and Adolescents on Antipsychotics |
| **Age Range** | 1-17 years |
| **Gender** | All |
| **Denominator** | Children/adolescents 1-17 with new antipsychotic prescription |
| **Numerator** | Documentation of psychosocial care prior to or concurrent with antipsychotic prescribing |
| **Key Exclusions** | Hospice; schizophrenia; bipolar with manic episode; autism spectrum disorder (some years) |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD |

#### SAA -- Adherence to Antipsychotic Medications for Individuals with Schizophrenia
| Field | Value |
|-------|-------|
| **Abbreviation** | SAA |
| **Full Name** | Adherence to Antipsychotic Medications for Individuals with Schizophrenia |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ with schizophrenia or schizoaffective disorder |
| **Numerator** | Antipsychotic medication adherence >= 80% PDC during MY |
| **Key Exclusions** | Hospice; members in a clinical trial |
| **Data Sources** | Claims (pharmacy) |
| **Product Lines** | C, MCD, MCR |

#### SSD -- Diabetes Screening for People with Schizophrenia or Bipolar Disorder Using Antipsychotics
| Field | Value |
|-------|-------|
| **Abbreviation** | SSD |
| **Full Name** | Diabetes Screening for People with Schizophrenia or Bipolar Disorder Who Are Using Antipsychotic Medications |
| **Age Range** | 18-64 years |
| **Gender** | All |
| **Denominator** | Members 18-64 with schizophrenia/schizoaffective or bipolar disorder, dispensed an antipsychotic |
| **Numerator** | Glucose or HbA1c test during MY |
| **Key Exclusions** | Diabetes diagnosis; hospice |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD |

#### FUH -- Follow-Up After Hospitalization for Mental Illness
| Field | Value |
|-------|-------|
| **Abbreviation** | FUH |
| **Full Name** | Follow-Up After Hospitalization for Mental Illness |
| **Age Range** | 6+ years |
| **Gender** | All |
| **Denominator** | Members 6+ discharged from inpatient psychiatric hospitalization |
| **Numerator** | Follow-up visit with a mental health provider |
| **Key Exclusions** | Transfer/readmission within time window; hospice; deceased |
| **Sub-measures** | Rate 1: Follow-up within 7 days; Rate 2: Follow-up within 30 days |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

#### FUM -- Follow-Up After Emergency Department Visit for Mental Illness
| Field | Value |
|-------|-------|
| **Abbreviation** | FUM |
| **Full Name** | Follow-Up After Emergency Department Visit for Mental Illness |
| **Age Range** | 6+ years |
| **Gender** | All |
| **Denominator** | Members 6+ with ED visit with principal mental illness diagnosis |
| **Numerator** | Follow-up visit with mental health provider |
| **Key Exclusions** | Inpatient admission directly from ED; hospice |
| **Sub-measures** | Rate 1: Follow-up within 7 days; Rate 2: Follow-up within 30 days |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |
| **Notes** | MY 2026 allows intentional self-harm diagnoses in any position; new diagnoses included |

#### FUA -- Follow-Up After Emergency Department Visit for Substance Use
| Field | Value |
|-------|-------|
| **Abbreviation** | FUA |
| **Full Name** | Follow-Up After Emergency Department Visit for Substance Use (formerly "Alcohol and Other Drug Abuse or Dependence") |
| **Age Range** | 13+ years |
| **Gender** | All |
| **Denominator** | Members 13+ with ED visit with principal substance use disorder diagnosis |
| **Numerator** | Follow-up visit within specified timeframe |
| **Key Exclusions** | Inpatient admission directly from ED; hospice |
| **Sub-measures** | Rate 1: Follow-up within 7 days; Rate 2: Follow-up within 30 days |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

#### FUI -- Follow-Up After High-Intensity Care for Substance Use Disorder
| Field | Value |
|-------|-------|
| **Abbreviation** | FUI |
| **Full Name** | Follow-Up After High-Intensity Care for Substance Use Disorder |
| **Age Range** | 13+ years |
| **Gender** | All |
| **Denominator** | Members 13+ discharged from inpatient or residential SUD treatment |
| **Numerator** | Follow-up visit within specified timeframe |
| **Key Exclusions** | Hospice; transfer/readmission |
| **Sub-measures** | Rate 1: Follow-up within 7 days; Rate 2: Follow-up within 30 days |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |
| **Notes** | MY 2026: SUD diagnoses allowed in any claim position; peer support added as follow-up option |

#### IET -- Initiation and Engagement of Substance Use Disorder Treatment
| Field | Value |
|-------|-------|
| **Abbreviation** | IET |
| **Full Name** | Initiation and Engagement of Substance Use Disorder Treatment |
| **Age Range** | 13+ years |
| **Gender** | All |
| **Denominator** | Members 13+ with new SUD diagnosis |
| **Numerator** | Initiation: Treatment within 14 days of diagnosis; Engagement: 2+ services within 34 days |
| **Key Exclusions** | Hospice; prior SUD treatment in lookback period |
| **Sub-measures** | Rate 1: Initiation (14-day); Rate 2: Engagement (34-day) |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

#### POD -- Pharmacotherapy for Opioid Use Disorder
| Field | Value |
|-------|-------|
| **Abbreviation** | POD |
| **Full Name** | Pharmacotherapy for Opioid Use Disorder |
| **Age Range** | 16+ years |
| **Gender** | All |
| **Denominator** | Members 16+ with OUD diagnosis |
| **Numerator** | Pharmacotherapy with buprenorphine, naltrexone, or methadone for >= 180 days |
| **Key Exclusions** | Hospice; cancer; sickle cell disease |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

### 2.7 Overuse and Appropriateness

#### LBP -- Use of Imaging Studies for Low Back Pain
| Field | Value |
|-------|-------|
| **Abbreviation** | LBP |
| **Full Name** | Use of Imaging Studies for Low Back Pain |
| **Age Range** | 18-75 years |
| **Gender** | All |
| **Denominator** | Members 18-75 with new low back pain diagnosis |
| **Numerator** | Members who did NOT have imaging (X-ray, MRI, CT) within 28 days (higher = better -- inverse measure) |
| **Key Exclusions** | Cancer; recent trauma; IV drug use; neurologic impairment; hospice |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

#### APC -- Use of Multiple Concurrent Antipsychotics in Children and Adolescents
| Field | Value |
|-------|-------|
| **Abbreviation** | APC |
| **Full Name** | Use of Multiple Concurrent Antipsychotics in Children and Adolescents |
| **Age Range** | 1-17 years |
| **Gender** | All |
| **Denominator** | Children/adolescents on 2+ antipsychotics concurrently for >= 90 days |
| **Numerator** | Percentage on multiple concurrent antipsychotics (lower = better -- inverse measure) |
| **Key Exclusions** | Hospice |
| **Data Sources** | Claims (pharmacy) |
| **Product Lines** | C, MCD |

#### DDE -- Potentially Harmful Drug-Disease Interactions in the Elderly
| Field | Value |
|-------|-------|
| **Abbreviation** | DDE |
| **Full Name** | Potentially Harmful Drug-Disease Interactions in the Elderly |
| **Age Range** | 65+ years |
| **Gender** | All |
| **Denominator** | Members 65+ with specific conditions (dementia, falls/hip fracture, chronic kidney disease) |
| **Numerator** | Received potentially harmful medication for their condition (lower = better -- inverse measure) |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Rate 1: Dementia + anticholinergics/etc.; Rate 2: Falls/hip fracture + CNS-active drugs; Rate 3: CKD + NSAIDs |
| **Data Sources** | Claims |
| **Product Lines** | MCR |

#### DAE -- Use of High-Risk Medications in Older Adults
| Field | Value |
|-------|-------|
| **Abbreviation** | DAE |
| **Full Name** | Use of High-Risk Medications in Older Adults (also called "Use of High-Risk Medications in the Elderly") |
| **Age Range** | 65+ years |
| **Gender** | All |
| **Denominator** | Members 65+ enrolled during MY |
| **Numerator** | Received at least one high-risk medication (lower = better -- inverse measure) |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Rate 1: At least one high-risk medication; Rate 2: At least two different high-risk medications |
| **Data Sources** | Claims (pharmacy) |
| **Product Lines** | MCR |

#### HDO -- Use of Opioids at High Dosage
| Field | Value |
|-------|-------|
| **Abbreviation** | HDO |
| **Full Name** | Use of Opioids at High Dosage |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ with 2+ opioid dispensing events on different dates |
| **Numerator** | Average daily MME (morphine milligram equivalent) >= 90 (lower = better -- inverse measure) |
| **Key Exclusions** | Cancer; sickle cell; hospice; palliative care |
| **Data Sources** | Claims (pharmacy) |
| **Product Lines** | C, MCD, MCR |

#### UOP -- Use of Opioids from Multiple Providers
| Field | Value |
|-------|-------|
| **Abbreviation** | UOP |
| **Full Name** | Use of Opioids from Multiple Providers |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ with 2+ opioid dispensing events on different dates |
| **Numerator** | Received opioids from 4+ prescribers AND 4+ pharmacies (lower = better -- inverse measure) |
| **Key Exclusions** | Cancer; sickle cell; hospice; palliative care |
| **Data Sources** | Claims (pharmacy) |
| **Product Lines** | C, MCD, MCR |

### 2.8 Medication Management and Care Coordination

#### TRC -- Transitions of Care
| Field | Value |
|-------|-------|
| **Abbreviation** | TRC |
| **Full Name** | Transitions of Care |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ discharged from acute inpatient stay |
| **Numerator** | Varies by rate (see sub-measures) |
| **Key Exclusions** | Hospice; deceased; discharge to SNF/rehab/LTAC |
| **Sub-measures** | Rate 1: Notification of Inpatient Admission; Rate 2: Receipt of Discharge Information; Rate 3: Patient Engagement After Inpatient Discharge; Rate 4: Medication Reconciliation Post-Discharge (within 30 days) |
| **Data Sources** | Claims, hybrid |
| **Product Lines** | C, MCD, MCR |

#### FMC -- Follow-Up After ED Visit for People with Multiple High-Risk Chronic Conditions
| Field | Value |
|-------|-------|
| **Abbreviation** | FMC |
| **Full Name** | Follow-Up After Emergency Department Visit for People with Multiple High-Risk Chronic Conditions |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ with 2+ high-risk chronic conditions and an ED visit during MY |
| **Numerator** | Follow-up visit within 7 days of ED visit |
| **Key Exclusions** | Inpatient admission from ED; hospice |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |
| **Notes** | MY 2026: Enrollment gaps prohibited on eligible ED visit date |

#### MAC -- Medication Adherence for Cholesterol (Statins)
| Field | Value |
|-------|-------|
| **Abbreviation** | MAC |
| **Full Name** | Medication Adherence for Cholesterol (Statins) |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ dispensed at least 2 statin fills during MY |
| **Numerator** | PDC (Proportion of Days Covered) >= 80% |
| **Key Exclusions** | Hospice; ESRD |
| **Data Sources** | Claims (pharmacy -- Part D) |
| **Product Lines** | MCR |

#### MAD -- Medication Adherence for Diabetes Medications
| Field | Value |
|-------|-------|
| **Abbreviation** | MAD |
| **Full Name** | Medication Adherence for Diabetes Medications |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ dispensed at least 2 fills of oral diabetes medications during MY |
| **Numerator** | PDC >= 80% |
| **Key Exclusions** | Hospice; ESRD; insulin-only therapy |
| **Data Sources** | Claims (pharmacy -- Part D) |
| **Product Lines** | MCR |

#### MAH -- Medication Adherence for Hypertension (RAS Antagonists)
| Field | Value |
|-------|-------|
| **Abbreviation** | MAH |
| **Full Name** | Medication Adherence for Hypertension (RAS Antagonists) |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ dispensed at least 2 fills of RAS antagonists during MY |
| **Numerator** | PDC >= 80% |
| **Key Exclusions** | Hospice; ESRD |
| **Data Sources** | Claims (pharmacy -- Part D) |
| **Product Lines** | MCR |

### 2.9 Well-Care and Preventive Visits

#### WCV -- Child and Adolescent Well-Care Visits
| Field | Value |
|-------|-------|
| **Abbreviation** | WCV |
| **Full Name** | Child and Adolescent Well-Care Visits |
| **Age Range** | 3-21 years |
| **Gender** | All |
| **Denominator** | Members 3-21 enrolled during MY |
| **Numerator** | At least one well-care visit with PCP or OB/GYN during MY |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Stratified by age bands (3-11, 12-17, 18-21) |
| **Data Sources** | Claims, hybrid |
| **Product Lines** | C, MCD |
| **Notes** | Combines former W34 and AWC measures |

#### W30 -- Well-Child Visits in the First 30 Months of Life
| Field | Value |
|-------|-------|
| **Abbreviation** | W30 |
| **Full Name** | Well-Child Visits in the First 30 Months of Life |
| **Age Range** | 0-30 months |
| **Gender** | All |
| **Denominator** | Children who turn 15 months or 30 months during MY |
| **Numerator** | >= 6 visits by 15 months of age; >= 2 visits between 15 and 30 months |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Rate 1: Well-child visits in first 15 months (>= 6 visits); Rate 2: Well-child visits from 15 to 30 months (>= 2 visits) |
| **Data Sources** | Claims, hybrid |
| **Product Lines** | C, MCD |
| **Notes** | Replaces former W15 measure |

#### WCC -- Weight Assessment and Counseling for Nutrition and Physical Activity for Children/Adolescents
| Field | Value |
|-------|-------|
| **Abbreviation** | WCC |
| **Full Name** | Weight Assessment and Counseling for Nutrition and Physical Activity for Children/Adolescents |
| **Age Range** | 3-17 years |
| **Gender** | All |
| **Denominator** | Children/adolescents 3-17 with outpatient visit during MY |
| **Numerator** | BMI percentile documented AND counseling for nutrition AND counseling for physical activity |
| **Key Exclusions** | Pregnancy; hospice |
| **Sub-measures** | Rate 1: BMI percentile; Rate 2: Counseling for nutrition; Rate 3: Counseling for physical activity |
| **Data Sources** | Hybrid |
| **Product Lines** | C, MCD |

### 2.10 Maternal Care

#### PPC -- Prenatal and Postpartum Care
| Field | Value |
|-------|-------|
| **Abbreviation** | PPC |
| **Full Name** | Prenatal and Postpartum Care |
| **Age Range** | Any age (women with live deliveries) |
| **Gender** | Female |
| **Denominator** | Deliveries during MY |
| **Numerator** | Timeliness of prenatal care AND postpartum visit |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Rate 1: Timeliness of Prenatal Care (visit in first trimester or within 42 days of enrollment); Rate 2: Postpartum Care (visit 7-84 days after delivery) |
| **Data Sources** | Hybrid |
| **Product Lines** | C, MCD |

### 2.11 Musculoskeletal Conditions

#### COA -- Care for Older Adults
| Field | Value |
|-------|-------|
| **Abbreviation** | COA |
| **Full Name** | Care for Older Adults |
| **Age Range** | 65+ years |
| **Gender** | All |
| **Denominator** | Members 65+ enrolled during MY |
| **Numerator** | Documentation of specific elements of care |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Medication Review; Functional Status Assessment (Pain Assessment retired MY 2025) |
| **Data Sources** | Hybrid |
| **Product Lines** | MCR, MP |

### 2.12 Tobacco Use

#### TSC-E -- Tobacco Use Screening and Cessation Intervention
| Field | Value |
|-------|-------|
| **Abbreviation** | TSC-E |
| **Full Name** | Tobacco Use Screening and Cessation Intervention |
| **Age Range** | 12+ years |
| **Gender** | All |
| **Denominator** | Members 12+ enrolled during MY |
| **Numerator** | Screened for tobacco use AND cessation intervention provided if identified as user |
| **Key Exclusions** | Hospice; palliative care (added MY 2026) |
| **Sub-measures** | Rate 1: Screening; Rate 2: Cessation intervention for identified users |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |
| **Notes** | New MY 2026; replaces CAHPS MSC measure |

### 2.13 Social Determinants / Health Equity

#### SNS-E -- Social Need Screening and Intervention
| Field | Value |
|-------|-------|
| **Abbreviation** | SNS-E |
| **Full Name** | Social Need Screening and Intervention |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Denominator** | Members 18+ enrolled during MY |
| **Numerator** | Screened for social needs AND intervention provided if need identified |
| **Key Exclusions** | Hospice |
| **Sub-measures** | 6 indicators -- screening and intervention for: Food Insecurity, Transportation, Housing Instability |
| **Data Sources** | ECDS |
| **Product Lines** | C, MCD, MCR |
| **Notes** | MY 2026: Updated value sets; incorporated HCPCS G0136 and ICD-10 Z codes |

### 2.14 Dental Care

#### OED -- Oral Evaluation, Dental Services
| Field | Value |
|-------|-------|
| **Abbreviation** | OED |
| **Full Name** | Oral Evaluation, Dental Services |
| **Age Range** | Under 21 years |
| **Gender** | All |
| **Denominator** | Members under 21 enrolled during MY |
| **Numerator** | Comprehensive or periodic oral evaluation with dental provider during MY |
| **Key Exclusions** | Hospice |
| **Data Sources** | Claims (dental CDT codes) |
| **Product Lines** | MCD |
| **Notes** | Replaced former ADV (Annual Dental Visit) measure starting MY 2023 |

#### TFC -- Topical Fluoride for Children
| Field | Value |
|-------|-------|
| **Abbreviation** | TFC |
| **Full Name** | Topical Fluoride for Children |
| **Age Range** | 1-4 years |
| **Gender** | All |
| **Denominator** | Children 1-4 enrolled during MY |
| **Numerator** | At least 2 fluoride varnish applications during MY |
| **Key Exclusions** | Hospice |
| **Data Sources** | Claims (dental/medical) |
| **Product Lines** | MCD |

---

## <a name="access-availability"></a>3. Domain 2: Access/Availability of Care

#### AAP -- Adults' Access to Preventive/Ambulatory Health Services
| Field | Value |
|-------|-------|
| **Abbreviation** | AAP |
| **Full Name** | Adults' Access to Preventive/Ambulatory Health Services |
| **Age Range** | 20+ years |
| **Gender** | All |
| **Denominator** | Members 20+ enrolled during MY |
| **Numerator** | At least one ambulatory or preventive care visit during MY |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Stratified by age bands: 20-44, 45-64, 65+ |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

#### CAP -- Children and Adolescents' Access to Primary Care Practitioners
| Field | Value |
|-------|-------|
| **Abbreviation** | CAP |
| **Full Name** | Children and Adolescents' Access to Primary Care Practitioners |
| **Age Range** | 12 months - 19 years |
| **Gender** | All |
| **Denominator** | Members 12 months - 19 years enrolled during MY |
| **Numerator** | At least one visit with PCP during MY |
| **Key Exclusions** | Hospice |
| **Sub-measures** | Stratified by age: 12-24 months, 25 months-6 years, 7-11 years, 12-19 years |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD |

---

## <a name="experience-of-care"></a>4. Domain 3: Experience of Care (CAHPS Survey-Based)

These measures are survey-based (CAHPS -- Consumer Assessment of Healthcare Providers and Systems) and are NOT evaluable from clinical chart data. They are included here for completeness.

#### CPA -- CAHPS Health Plan Survey (Adult)
| Sub-measure | Description |
|-------------|-------------|
| **Getting Needed Care** | Composite: ease of getting needed care, tests, treatment |
| **Getting Care Quickly** | Composite: timeliness of urgent and routine care |
| **How Well Doctors Communicate** | Composite: doctor communication quality |
| **Customer Service** | Composite: health plan customer service quality |
| **Rating of All Health Care** | Global: overall health care rating (0-10 scale) |
| **Rating of Health Plan** | Global: overall health plan rating (0-10 scale) |
| **Rating of Personal Doctor** | Global: personal doctor rating (0-10 scale) |
| **Rating of Specialist** | Global: specialist rating (0-10 scale) |
| **Claims Processing** | Composite: claims handling (Commercial only) |
| **Coordination of Care** | How well providers coordinate care |

#### FVA / FVO -- Flu Vaccinations (CAHPS-Reported)
| Field | Value |
|-------|-------|
| **Abbreviation** | FVA (adults 18-64), FVO (adults 65+) |
| **Full Name** | Flu Vaccinations for Adults |
| **Data Source** | CAHPS survey |
| **Notes** | Survey-reported immunization status |

#### MSC -- Medical Assistance with Smoking and Tobacco Use Cessation (RETIRED MY 2026)
| Field | Value |
|-------|-------|
| **Abbreviation** | MSC |
| **Full Name** | Medical Assistance with Smoking and Tobacco Use Cessation |
| **Status** | **RETIRED effective MY 2026** -- replaced by TSC-E |
| **Data Source** | CAHPS survey |

---

## <a name="utilization"></a>5. Domain 4: Utilization and Risk-Adjusted Utilization

### 5.1 Utilization Measures

#### ABX -- Antibiotic Utilization for Respiratory Conditions
| Field | Value |
|-------|-------|
| **Abbreviation** | ABX (also referenced as AXR) |
| **Full Name** | Antibiotic Utilization for Respiratory Conditions |
| **Age Range** | All ages |
| **Gender** | All |
| **Description** | Reports observed antibiotic dispensing rates by age group for episodes of selected respiratory conditions |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD |
| **Notes** | MY 2026: Added deceased member exclusion |

#### FSP -- Frequency of Selected Procedures
| Field | Value |
|-------|-------|
| **Abbreviation** | FSP |
| **Full Name** | Frequency of Selected Procedures |
| **Description** | Reports utilization rates for selected surgical procedures |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD |

#### MPT -- Mental Health Utilization
| Field | Value |
|-------|-------|
| **Abbreviation** | MPT |
| **Full Name** | Mental Health Utilization |
| **Description** | Reports utilization of mental health services: inpatient, intermediate, outpatient, ED |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

### 5.2 Risk-Adjusted Utilization Measures

#### PCR -- Plan All-Cause Readmissions
| Field | Value |
|-------|-------|
| **Abbreviation** | PCR |
| **Full Name** | Plan All-Cause Readmissions |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected 30-day unplanned readmissions. O/E < 1.0 = better; > 1.0 = worse |
| **Key Exclusions** | Planned readmissions; transfers; hospice; perinatal; cancer chemotherapy |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

#### AHU -- Acute Hospital Utilization
| Field | Value |
|-------|-------|
| **Abbreviation** | AHU |
| **Full Name** | Acute Hospital Utilization |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected acute inpatient and observation stay discharges |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

#### EDU -- Emergency Department Utilization
| Field | Value |
|-------|-------|
| **Abbreviation** | EDU |
| **Full Name** | Emergency Department Utilization |
| **Age Range** | 18+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected ED visits during MY |
| **Data Sources** | Claims |
| **Product Lines** | C, MCD, MCR |

#### HPC -- Hospitalization for Potentially Preventable Complications
| Field | Value |
|-------|-------|
| **Abbreviation** | HPC |
| **Full Name** | Hospitalization for Potentially Preventable Complications |
| **Age Range** | 67+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected hospitalizations for ambulatory care-sensitive conditions |
| **Data Sources** | Claims |
| **Product Lines** | MCR |

#### HFS -- Hospitalization Following Discharge from a Skilled Nursing Facility
| Field | Value |
|-------|-------|
| **Abbreviation** | HFS |
| **Full Name** | Hospitalization Following Discharge from a Skilled Nursing Facility |
| **Age Range** | 65+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected hospitalizations within 30 days of SNF discharge |
| **Key Exclusions** | Hospice; MY 2026: Removed pregnancy principal diagnosis exclusion |
| **Data Sources** | Claims |
| **Product Lines** | MCR |

#### EDH -- Emergency Department Visits for Hypoglycemia in Older Adults with Diabetes
| Field | Value |
|-------|-------|
| **Abbreviation** | EDH |
| **Full Name** | Emergency Department Visits for Hypoglycemia in Older Adults with Diabetes |
| **Age Range** | 65+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected ED visits for hypoglycemia among older adults with diabetes |
| **Data Sources** | Claims |
| **Product Lines** | MCR |

#### HFO -- Acute Hospitalizations Following Outpatient Orthopedic Surgery (NEW MY 2026)
| Field | Value |
|-------|-------|
| **Abbreviation** | HFO |
| **Full Name** | Acute Hospitalizations Following Outpatient Orthopedic Surgery |
| **Age Range** | 65+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected unplanned acute hospitalizations within 15 days of outpatient orthopedic surgery |
| **Data Sources** | Claims |
| **Product Lines** | MCR |
| **Notes** | New MY 2026 |

#### HFG -- Acute Hospitalizations Following Outpatient General Surgery (NEW MY 2026)
| Field | Value |
|-------|-------|
| **Abbreviation** | HFG |
| **Full Name** | Acute Hospitalizations Following Outpatient General Surgery |
| **Age Range** | 65+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected unplanned acute hospitalizations within 15 days of outpatient general surgery |
| **Data Sources** | Claims |
| **Product Lines** | MCR |
| **Notes** | New MY 2026 |

#### HFC -- Acute Hospitalizations Following Outpatient Colonoscopy (NEW MY 2026)
| Field | Value |
|-------|-------|
| **Abbreviation** | HFC |
| **Full Name** | Acute Hospitalizations Following Outpatient Colonoscopy |
| **Age Range** | 65+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected unplanned acute hospitalizations within 15 days of outpatient colonoscopy |
| **Data Sources** | Claims |
| **Product Lines** | MCR |
| **Notes** | New MY 2026 |

#### HFU -- Acute Hospitalizations Following Outpatient Urologic Surgery (NEW MY 2026)
| Field | Value |
|-------|-------|
| **Abbreviation** | HFU |
| **Full Name** | Acute Hospitalizations Following Outpatient Urologic Surgery |
| **Age Range** | 65+ years |
| **Gender** | All |
| **Description** | Risk-adjusted ratio of observed-to-expected unplanned acute hospitalizations within 15 days of outpatient urologic surgery |
| **Data Sources** | Claims |
| **Product Lines** | MCR |
| **Notes** | New MY 2026 |

---

## <a name="descriptive-info"></a>6. Domain 5: Health Plan Descriptive Information

These are reporting/descriptive measures, not clinical quality measures. They are NOT evaluable from clinical chart data.

| Abbreviation | Full Name | Description |
|-------------|-----------|-------------|
| **BCR** | Board Certification | Percentage of plan's physicians who are board certified |
| **ENP** | Enrollment by Product Line | Membership counts by product line |
| **EBS** | Enrollment by State | Membership counts by state |
| **LDM** | Language Diversity of Membership | Primary language distribution of members |
| **RDM** | Race/Ethnicity Diversity of Membership | Race and ethnicity distribution of members |
| **TLM** | Total Membership | Total plan membership |
| **DDM** | Disability Description of Membership | Disability status distribution (NEW MY 2026) |

---

## <a name="ecds-measures"></a>7. Domain 6: Measures Reported Using ECDS

As of MY 2025-2026, the following measures are reported exclusively or optionally via the Electronic Clinical Data Systems (ECDS) method. Many of these are also listed above in their respective clinical domains.

### ECDS-Only Measures (MY 2026)

| Abbreviation | Full Name | Domain |
|-------------|-----------|--------|
| BCS-E | Breast Cancer Screening | Prevention |
| CCS-E | Cervical Cancer Screening | Prevention |
| COL-E | Colorectal Cancer Screening | Prevention |
| CIS-E | Childhood Immunization Status | Immunizations |
| IMA-E | Immunizations for Adolescents | Immunizations |
| AIS-E | Adult Immunization Status | Immunizations |
| PRS-E | Prenatal Immunization Status | Immunizations |
| LSC-E | Lead Screening in Children | Prevention |
| DSF-E | Depression Screening and Follow-Up | Behavioral Health |
| DMS-E | Utilization of PHQ-9 to Monitor Depression | Behavioral Health |
| DRR-E | Depression Remission or Response | Behavioral Health |
| PND-E | Prenatal Depression Screening and Follow-Up | Behavioral Health |
| PDS-E | Postpartum Depression Screening and Follow-Up | Behavioral Health |
| ASF-E | Unhealthy Alcohol Use Screening and Follow-Up | Behavioral Health |
| ADD-E | Follow-Up for Children Prescribed ADHD Medication | Behavioral Health |
| APM-E | Metabolic Monitoring on Antipsychotics | Behavioral Health |
| SNS-E | Social Need Screening and Intervention | Health Equity |
| BPC-E / BPH-E | Blood Pressure Control for Hypertension | Cardiovascular |
| BPD-E | Blood Pressure Control for Diabetes | Diabetes |
| SPC-E | Statin Therapy for Cardiovascular Disease | Cardiovascular |
| SPD-E | Statin Therapy for Diabetes | Diabetes |
| AAF-E | Follow-Up After Acute/Urgent Asthma Care | Respiratory |
| TSC-E | Tobacco Use Screening and Cessation | Prevention |
| DBM-E | Documented BI-RADS Assessment | Prevention |
| FAM-E | Follow-Up After Abnormal Mammogram | Prevention |

---

## <a name="retired-measures"></a>8. Retired Measures (2020-2026)

### Retired MY 2020-2021
| Abbreviation | Full Name | Replaced By |
|-------------|-----------|-------------|
| W15 | Well-Child Visits First 15 Months | W30 (Well-Child Visits First 30 Months) |
| W34 | Well-Child Visits 3rd-6th Year | WCV (Child and Adolescent Well-Care Visits) |
| AWC | Adolescent Well-Care Visits | WCV |
| ART | Disease-Modifying Anti-Rheumatic Drug Therapy for RA | Retired |
| MRP | Medication Reconciliation Post-Discharge | Incorporated into TRC |
| ADV | Annual Dental Visit | OED (Oral Evaluation, Dental Services) |
| PBH | Persistence of Beta-Blocker Treatment After Heart Attack | Retired |

### Retired MY 2024
| Abbreviation | Full Name | Replaced By |
|-------------|-----------|-------------|
| AMB | Ambulatory Care (Medicaid utilization) | Risk-adjusted measures (AHU) |
| IPU | Inpatient Utilization - General Hospital/Acute Care (Medicaid) | Risk-adjusted measures |
| NCS | Non-Recommended Cervical Cancer Screening in Adolescent Females | Retired (high performance achieved) |
| SPR | Use of Spirometry Testing in Assessment of COPD | Retired (narrow scope) |

### Retired MY 2025
| Abbreviation | Full Name | Replaced By |
|-------------|-----------|-------------|
| AMM | Antidepressant Medication Management | DSF-E, DMS-E, DRR-E (depression screening/monitoring/outcome measures) |
| COA (Pain) | Care for Older Adults - Pain Assessment | Planned new chronic pain measure |
| CDC | Comprehensive Diabetes Care (as unified measure) | Split into HBD, EED, KED |

### Retired MY 2026
| Abbreviation | Full Name | Replaced By |
|-------------|-----------|-------------|
| AMR | Asthma Medication Ratio | AAF-E (Follow-Up After Acute Asthma Care) |
| MSC | Medical Assistance with Smoking and Tobacco Use Cessation | TSC-E (Tobacco Use Screening and Cessation) |

---

## <a name="summary"></a>9. Summary Count and Index

### Active Measures by Category (Approximate as of MY 2026)

| Category | Count | Measures |
|----------|-------|----------|
| **Prevention & Screening** | 11 | BCS-E, CCS-E, COL-E, CHL, LSC-E, PSA, DBM-E, FAM-E, OED, TFC, TSC-E |
| **Immunizations** | 4 | CIS-E, IMA-E, AIS-E, PRS-E |
| **Diabetes Care** | 5 | HBD, EED, KED, SPD-E, BPD-E |
| **Cardiovascular** | 3 | CBP/BPC-E, SPC-E, (MAH pharmacy-based) |
| **Respiratory** | 4 | AAF-E, CWP, URI, AAB, PCE |
| **Behavioral Health** | 14 | DSF-E, DMS-E, DRR-E, PND-E, PDS-E, ASF-E, ADD-E, APM-E, APP, SAA, SSD, FUH, FUM, FUA |
| **Substance Use** | 3 | FUI, IET, POD |
| **Overuse/Appropriateness** | 5 | LBP, APC, DDE, DAE, HDO, UOP |
| **Medication Adherence** | 3 | MAC, MAD, MAH |
| **Care Coordination** | 2 | TRC, FMC |
| **Well-Care Visits** | 4 | W30, WCV, WCC, PPC |
| **Geriatric Care** | 1 | COA |
| **Social/Health Equity** | 1 | SNS-E |
| **Access/Availability** | 2 | AAP, CAP |
| **Utilization (Risk-Adjusted)** | 9 | PCR, AHU, EDU, HPC, HFS, EDH, HFO, HFG, HFC, HFU |
| **Utilization (Descriptive)** | 3 | ABX, FSP, MPT |
| **Descriptive Information** | 7 | BCR, ENP, EBS, LDM, RDM, TLM, DDM |
| **Experience of Care (CAHPS)** | ~10 | CPA composites, FVA, FVO |
| **TOTAL** | **~95+** | |

### Alphabetical Index of All Current Measures (MY 2026)

| Abbrev | Full Name | Evaluable from Chart? |
|--------|-----------|----------------------|
| AAB | Avoidance of Antibiotic Treatment for Acute Bronchitis | Partially (needs Rx) |
| AAF-E | Follow-Up After Acute/Urgent Asthma Care | Partially (needs claims) |
| AAP | Adults' Access to Preventive/Ambulatory Services | Claims only |
| ABX | Antibiotic Utilization for Respiratory Conditions | Claims/Rx only |
| ADD-E | Follow-Up for Children Prescribed ADHD Medication | Partially (needs Rx) |
| AHU | Acute Hospital Utilization | Claims only |
| AIS-E | Adult Immunization Status | Yes (chart + immunization records) |
| APC | Use of Multiple Concurrent Antipsychotics | Pharmacy only |
| APM-E | Metabolic Monitoring on Antipsychotics | Yes (labs) |
| APP | First-Line Psychosocial Care for Youth on Antipsychotics | Partially |
| ASF-E | Unhealthy Alcohol Use Screening and Follow-Up | Yes (chart data) |
| BCS-E | Breast Cancer Screening | Yes (procedures) |
| BCR | Board Certification | N/A (plan-level) |
| BPC-E | Blood Pressure Control for Hypertension | Yes (vitals) |
| BPD-E | Blood Pressure Control for Diabetes | Yes (vitals) |
| CAP | Children/Adolescents' Access to Primary Care | Claims only |
| CBP | Controlling High Blood Pressure | Yes (vitals) |
| CCS-E | Cervical Cancer Screening | Yes (procedures) |
| CHL | Chlamydia Screening | Yes (labs) |
| CIS-E | Childhood Immunization Status | Yes (immunization records) |
| COA | Care for Older Adults | Yes (chart review) |
| COL-E | Colorectal Cancer Screening | Yes (procedures) |
| CWP | Appropriate Testing for Pharyngitis | Partially (needs Rx) |
| DAE | Use of High-Risk Medications in Older Adults | Pharmacy only |
| DBM-E | Documented BI-RADS Assessment | Yes (radiology data) |
| DDE | Potentially Harmful Drug-Disease Interactions | Pharmacy + Dx |
| DDM | Disability Description of Membership | N/A (plan-level) |
| DMS-E | PHQ-9 Monitoring for Depression | Yes (chart data) |
| DRR-E | Depression Remission or Response | Yes (chart data) |
| DSF-E | Depression Screening and Follow-Up | Yes (chart data) |
| EBS | Enrollment by State | N/A (plan-level) |
| EDH | ED Visits for Hypoglycemia in Older Diabetics | Claims only |
| EDU | Emergency Department Utilization | Claims only |
| EED | Eye Exam for Patients with Diabetes | Yes (procedures) |
| ENP | Enrollment by Product Line | N/A (plan-level) |
| FAM-E | Follow-Up After Abnormal Mammogram | Yes (procedures) |
| FMC | Follow-Up After ED for Multiple Chronic Conditions | Claims/encounters |
| FSP | Frequency of Selected Procedures | Claims only |
| FUA | Follow-Up After ED for Substance Use | Claims/encounters |
| FUH | Follow-Up After Hospitalization for Mental Illness | Claims/encounters |
| FUI | Follow-Up After High-Intensity SUD Care | Claims/encounters |
| FUM | Follow-Up After ED for Mental Illness | Claims/encounters |
| HBD | Hemoglobin A1c Control for Diabetes | Yes (labs) |
| HFC | Hospitalizations Following Outpatient Colonoscopy | Claims only |
| HFG | Hospitalizations Following Outpatient General Surgery | Claims only |
| HFO | Hospitalizations Following Outpatient Orthopedic Surgery | Claims only |
| HFS | Hospitalization Following SNF Discharge | Claims only |
| HFU | Hospitalizations Following Outpatient Urologic Surgery | Claims only |
| HPC | Hospitalization for Potentially Preventable Complications | Claims only |
| HDO | Use of Opioids at High Dosage | Pharmacy only |
| IET | Initiation/Engagement of SUD Treatment | Claims/encounters |
| IMA-E | Immunizations for Adolescents | Yes (immunization records) |
| KED | Kidney Health Evaluation for Diabetes | Yes (labs) |
| LBP | Use of Imaging for Low Back Pain | Claims + procedures |
| LDM | Language Diversity of Membership | N/A (plan-level) |
| LSC-E | Lead Screening in Children | Yes (labs) |
| MAC | Medication Adherence for Cholesterol | Pharmacy only |
| MAD | Medication Adherence for Diabetes | Pharmacy only |
| MAH | Medication Adherence for Hypertension | Pharmacy only |
| MPT | Mental Health Utilization | Claims only |
| OED | Oral Evaluation, Dental Services | Dental claims |
| PCE | Pharmacotherapy Mgmt of COPD Exacerbation | Partially (needs Rx) |
| PCR | Plan All-Cause Readmissions | Claims only |
| PDS-E | Postpartum Depression Screening | Yes (chart data) |
| PND-E | Prenatal Depression Screening | Yes (chart data) |
| POD | Pharmacotherapy for Opioid Use Disorder | Pharmacy + Dx |
| PPC | Prenatal and Postpartum Care | Yes (chart data) |
| PRS-E | Prenatal Immunization Status | Yes (immunization records) |
| PSA | Non-Recommended PSA Screening in Older Men | Labs/claims |
| RDM | Race/Ethnicity Diversity | N/A (plan-level) |
| SAA | Adherence to Antipsychotic Medications | Pharmacy only |
| SNS-E | Social Need Screening and Intervention | Yes (chart data) |
| SPC-E | Statin Therapy for Cardiovascular Disease | Partially (needs Rx) |
| SPD-E | Statin Therapy for Diabetes | Partially (needs Rx) |
| SSD | Diabetes Screening for Schizophrenia/Bipolar on Antipsychotics | Labs + Dx |
| TFC | Topical Fluoride for Children | Dental/medical claims |
| TLM | Total Membership | N/A (plan-level) |
| TRC | Transitions of Care | Claims + chart |
| TSC-E | Tobacco Use Screening and Cessation | Yes (chart data) |
| URI | Appropriate Treatment for URI | Partially (needs Rx) |
| UOP | Use of Opioids from Multiple Providers | Pharmacy only |
| W30 | Well-Child Visits First 30 Months | Claims/encounters |
| WCC | Weight Assessment/Counseling for Children | Yes (chart review) |
| WCV | Child and Adolescent Well-Care Visits | Claims/encounters |

### Measures Most Evaluable from Clinical Chart Data

The following measures are most suitable for evaluation using extracted clinical chart data (diagnoses, procedures, labs, vitals, medications, encounters). This is the priority list for the HEDIS engine:

**Tier 1 -- Directly evaluable from chart extraction:**
1. HBD -- Hemoglobin A1c (requires lab values)
2. EED -- Eye Exam for Diabetes (requires procedure documentation)
3. KED -- Kidney Health Evaluation (requires lab values)
4. CBP / BPC-E -- Blood Pressure Control (requires vital signs)
5. BPD-E -- Blood Pressure Control for Diabetes (requires vitals + Dx)
6. BCS-E -- Breast Cancer Screening (requires procedure documentation)
7. CCS-E -- Cervical Cancer Screening (requires procedure documentation)
8. COL-E -- Colorectal Cancer Screening (requires procedure documentation)
9. DSF-E -- Depression Screening (requires screening tool documentation)
10. DMS-E -- PHQ-9 Monitoring (requires PHQ-9 scores)
11. DRR-E -- Depression Remission/Response (requires PHQ-9 scores)
12. PND-E -- Prenatal Depression Screening (requires screening documentation)
13. PDS-E -- Postpartum Depression Screening (requires screening documentation)
14. ASF-E -- Alcohol Screening (requires screening documentation)
15. TSC-E -- Tobacco Screening (requires screening documentation)
16. WCC -- Weight Assessment (requires BMI, vitals, counseling documentation)
17. PPC -- Prenatal/Postpartum Care (requires encounter documentation)
18. COA -- Care for Older Adults (requires medication review, functional assessment)
19. SNS-E -- Social Needs Screening (requires screening documentation)
20. CIS-E / IMA-E / AIS-E -- Immunizations (requires immunization documentation)

**Tier 2 -- Partially evaluable (chart + claims/pharmacy needed):**
21. SPD-E / SPC-E -- Statin Therapy (needs Rx data)
22. CHL -- Chlamydia Screening (needs lab orders/results)
23. LSC-E -- Lead Screening (needs lab results)
24. APM-E -- Metabolic Monitoring (needs lab results + Rx data)
25. ADD-E -- ADHD Follow-Up (needs Rx + visit data)
26. PCE -- COPD Pharmacotherapy (needs Rx data)
27. TRC -- Transitions of Care (needs hospital records + follow-up)
28. FUH/FUM/FUA/FUI -- Follow-Up measures (needs encounter data)
29. IET -- SUD Treatment Initiation (needs encounter + treatment data)
30. POD -- Opioid Pharmacotherapy (needs Rx + Dx data)

---

## <a name="sources"></a>10. Sources

All information compiled from publicly available descriptions. No NCQA-licensed specification text reproduced.

- [NCQA HEDIS Measures and Technical Resources](https://www.ncqa.org/hedis/measures/)
- [HEDIS MY 2025 Measure Descriptions (NCQA)](https://wpcdn.ncqa.org/www-prod/wp-content/uploads/HEDIS-MY-2025-Measure-Description.pdf)
- [HEDIS MY 2026: What's New, What's Changed, What's Retired (NCQA Blog)](https://www.ncqa.org/blog/hedis-my-2026-whats-new-whats-changed-whats-retired/)
- [Retiring and Replacing HEDIS Measures, 2024-2026 (NCQA Blog)](https://www.ncqa.org/blog/retiring-and-replacing-hedis-measures-2024-2026/)
- [NCQA HEDIS ECDS Reporting](https://www.ncqa.org/resources/hedis-electronic-clinical-data-systems-ecds-reporting/)
- [2026 Health Plan Ratings Required Measures (NCQA)](https://wpcdn.ncqa.org/www-prod/2026-HPR-List-of-Required-Performance-Measures_April-2025-Posting.pdf)
- [MY 2026 HEDIS Technical Specifications Breakdown (Cotiviti)](https://resources.cotiviti.com/quality-measurement-and-reporting/my-2026-breaking-down-the-latest-hedis-technical-specifications)
- [Decoding the HEDIS MY 2025 Technical Specifications (Cotiviti)](https://resources.cotiviti.com/quality-measurement-and-reporting/decoding-the-hedis-my-2025-technical-specifications)
- [HEDIS MY 2026 Updates (Illinois Meridian)](https://www.ilmeridian.com/newsroom/hedis--updates--revised-and-retired-measures-for-2026.html)
- [HEDIS 2026 Updates: How to Prepare (MedInsight)](https://medinsight.com/healthcare-data-analytics-resources/blog/looking-ahead-preparing-for-key-hedis-2026-updates/)
- [Johns Hopkins HEDIS General Guidelines and Measure Descriptions](https://www.hopkinsmedicine.org/johns-hopkins-health-plans/providers-physicians/health-care-performance-measures/hedis/general-guidelines)
- [RxEconsult: List of HEDIS Measures (2018 historical baseline)](http://www.rxeconsult.com/healthcare-articles/List-Of-HEDIS-Measures-For-2018--1393/)
- [NCQA Child and Adolescent Well-Care Visits](https://www.ncqa.org/hedis/measures/child-and-adolescent-well-care-visits/)
- [NCQA Oral Evaluation, Dental Services (OED)](https://www.ncqa.org/report-cards/health-plans/state-of-health-care-quality-report/oral-evaluation-dental-services-oed/)
- [NCQA Transitions of Care](https://www.ncqa.org/hedis/measures/transitions-of-care/)
- [CMS Healthcare Effectiveness Data and Information Set](https://www.cms.gov/medicare/enrollment-renewal/special-needs-plans/data-information-set)
- [CMS 2026 Quality Rating System Measure Technical Specifications](https://www.cms.gov/files/document/2026-quality-rating-system-measure-technical-specifications.pdf)
- [NCQA Tobacco Cessation HEDIS Measure (MY 2026)](https://www.ncqa.org/blog/tobacco-cessation-hedis-measure-planned-for-my-2026/)
- [Diabetes HEDIS Measures (Stability Health)](https://stabilityhealth.com/hedis-diabetes-measures/)
- [NCQA Health Equity: Data and Measurement](https://www.ncqa.org/health-equity/data-and-measurement/)
- [NCQA Social Need Screening Measure](https://www.ncqa.org/blog/social-need-new-hedis-measure-uses-electronic-data-to-look-at-screening-intervention/)
