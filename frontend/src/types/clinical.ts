export type NegationStatus = 'active' | 'negated' | 'resolved' | 'historical' | 'family_history' | 'uncertain';

export interface ClinicalEvidence {
  page_number?: number | null;
  exact_quote?: string | null;
  category?: string | null;
  concept?: string | null;
}

export interface Diagnosis {
  id?: number;
  icd10_code: string;
  icd9_code: string | null;
  snomed_code: string | null;
  description: string;
  negation_status: NegationStatus;
  negation_trigger: string | null;
  supporting_text: string | null;
  source_section: string | null;
  date_of_service: string | null;
  provider: string | null;
}

export interface Vital {
  date: string;
  weight: string | null;
  height: string | null;
  bmi: string | null;
  blood_pressure: string | null;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  pulse: string | null;
  temperature: string | null;
  oxygen_saturation: string | null;
  page_number?: number | null;
  exact_quote?: string | null;
}

export interface LabResult {
  test_name: string;
  result_value: string;
  result_date: string | null;
  reference_range: string | null;
  hedis_measure: string | null;
  within_target: boolean | null;
  page_number?: number | null;
  exact_quote?: string | null;
}

export interface Medication {
  name: string;
  dose_form: string | null;
  instructions: string | null;
  indication: string | null;
  action: string | null;
  page_number?: number | null;
  exact_quote?: string | null;
}

export interface ClinicalSentence {
  text: string;
  category: string;
  is_negated: boolean;
  negation_trigger: string | null;
  negated_item: string | null;
}

export interface Encounter {
  date: string;
  encounter_id: string | null;
  provider: string | null;
  facility: string | null;
  type: string | null;
  chief_complaint: string | null;
  page_number?: number | null;
  evidence?: string | null;
  evidence_items?: ClinicalEvidence[];
  assertion_count?: number;
  categories?: string[];
  telehealth_details?: { platform?: string; type?: string; prearranged?: boolean };
  procedures?: { name: string; cpt_code: string; status?: string; result?: string }[];
  medications?: Medication[];
  diagnoses?: { icd10_code: string; description: string; negation_status: NegationStatus; supporting_text?: string }[];
}
