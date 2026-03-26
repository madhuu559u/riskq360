export type MeasureStatus =
  | 'met'
  | 'gap'
  | 'not_applicable'
  | 'excluded'
  | 'indeterminate'
  | 'inactive';

export interface HEDISEvidenceItem {
  date?: string;
  systolic?: number;
  diastolic?: number;
  location?: string;
  within_target?: boolean;
  target_note?: string;
  type?: string;
  code?: string;
  system?: string;
  value?: string | number;
  source?: {
    pdf?: string;
    page?: number;
    exact_quote?: string;
    char_start?: number;
    char_end?: number;
  };
  page_number?: number;
  exact_quote?: string;
  pdf?: string;
  [key: string]: unknown;
}

export interface HEDISTraceItem {
  rule: string;
  result: boolean;
  detail: string;
  evidence?: HEDISEvidenceItem[];
}

export interface HEDISMeasureGap {
  type?: string;
  description: string;
  required_event?: string;
  required_event_name?: string;
  required_event_description?: string;
  actionable_reason?: string;
  window_start?: string;
  window_end?: string;
  window?: string;
}

export interface HEDISMeasureDefinition {
  measure_id?: string;
  measure_name?: string;
  description?: string;
  domain?: string;
  eligibility?: {
    age?: string;
    gender?: string;
    continuous_enrollment_required?: boolean;
  };
  denominator_rules?: string[];
  numerator_logic?: {
    any_of?: string[];
    all_of?: string[];
  };
  exclusion_rules?: string[];
  valuesets_needed?: string[];
  data_sources?: string[];
}

export interface HEDISMeasure {
  measure_code: string;
  measure_name: string;
  measure_id?: string;
  id?: string;
  eligible: boolean;
  status: MeasureStatus;
  evidence: HEDISEvidenceItem[];
  target: string | null;
  trace?: HEDISTraceItem[];
  gaps?: HEDISMeasureGap[];
  confidence?: number;
  eligibility_reason?: string[];
  compliance_reason?: string[];
  missing_data?: string[];
  exclusion_reason?: string;
  decision_reasoning?: {
    status?: string;
    applicable?: boolean;
    eligibility_reason?: string[];
    compliance_reason?: string[];
    exclusion_reason?: string;
    rule_trace_count?: number;
    evidence_count?: number;
    evidence_pages?: number[];
  };
  enrollment_dependency?: string;
  measure_definition?: HEDISMeasureDefinition;
  clinical_only_preview?: {
    status?: MeasureStatus | string;
    applicable?: boolean;
    compliant?: boolean | null;
    eligibility_reason?: string[];
    compliance_reason?: string[];
    gaps?: HEDISMeasureGap[];
    evidence_used?: HEDISEvidenceItem[];
    trace?: HEDISTraceItem[];
  };
}

export interface HEDISMeasuresResponse {
  measurement_year: number;
  measures: HEDISMeasure[];
  gaps: HEDISGapItem[];
  total_eligible: number;
  total_met: number;
  total_gaps: number;
  summary?: {
    total_measures?: number;
    applicable?: number;
    met?: number;
    gap?: number;
    excluded?: number;
    not_applicable?: number;
    indeterminate?: number;
    inactive?: number;
  };
  summary_preview?: {
    total_measures?: number;
    applicable?: number;
    met?: number;
    gap?: number;
    excluded?: number;
    not_applicable?: number;
    indeterminate?: number;
    inactive?: number;
  };
  default_view_mode?: 'strict' | 'clinical_preview';
  measure_profile?: {
    profile_id?: string;
    active_measure_ids?: string[];
    inactive_measure_ids?: string[];
  };
}

export interface HEDISGapItem {
  measure_code: string;
  measure_name: string;
  gap_description: string;
  missing_evidence: string | null;
  recommended_action: string | null;
  priority: string;
}
