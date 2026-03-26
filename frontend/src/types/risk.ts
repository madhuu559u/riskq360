export interface MEATEvidence {
  monitored: boolean;
  evaluated: boolean;
  assessed: boolean;
  assessment_text: string | null;
  treated: boolean;
  treatment_text?: string | null;
  monitoring_text?: string | null;
  evaluation_text?: string | null;
}

export interface ICDEvidenceSpan {
  text: string;
  section: string | null;
  start: number | null;
  end: number | null;
}

export interface HCCSupportingICD {
  icd10_code: string;
  icd10_description: string;
  hcc_code: string;
  hcc_description: string;
  raf_weight: number;
  confidence: number;
  ml_confidence: number;
  llm_confidence: number;
  polarity: string | null;
  meat_evidence: MEATEvidence | null;
  evidence_spans: ICDEvidenceSpan[];
  date_of_service: string | null;
  provider: string | null;
  is_suppressed: boolean;
  suppressed_by: string | null;
}

export interface HCCCode {
  hcc_code: string;
  hcc_description: string;
  raf_weight: number;
  hierarchy_applied: boolean;
  suppresses: string[];
  supported_icds: HCCSupportingICD[];
  audit_risk: string | null;
}

export interface HCCPack {
  chart_id: string;
  patient: Record<string, unknown> | null;
  measurement_year: number | null;
  processing_timestamp: string | null;
  payable_hccs: HCCCode[];
  unsupported_candidates: UnsupportedCandidate[];
  raf_summary: RAFSummary;
  pipeline_metadata: Record<string, unknown> | null;
}

export interface UnsupportedCandidate {
  icd10_code: string;
  icd10_description: string;
  reason: string;
  confidence: number;
  ml_confidence: number;
  llm_confidence: number;
}

export interface RAFSummary {
  total_raf_score: number;
  demographic_raf: number;
  hcc_raf: number;
  hcc_count: number;
  payable_hcc_count: number;
  suppressed_hcc_count: number;
  hcc_details: { hcc_code: string; hcc_description: string; raf_weight: number; icd_count: number }[];
  segment: string;
}

export interface HierarchyDetail {
  chart_id: string;
  hierarchy_details: { suppressed: string; by: string; group: string }[];
}
