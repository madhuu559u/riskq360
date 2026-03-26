import apiClient from './client';
import type { HCCPack, RAFSummary, HierarchyDetail, HCCCode, HCCSupportingICD } from '../types/risk';

function normalizeSupportingICD(raw: Record<string, unknown>): HCCSupportingICD {
  const supportingText = String(raw.supporting_text ?? '');
  return {
    icd10_code: String(raw.icd10_code ?? ''),
    icd10_description: String(raw.icd10_description ?? raw.description ?? ''),
    hcc_code: String(raw.hcc_code ?? ''),
    hcc_description: String(raw.hcc_description ?? ''),
    raf_weight: Number(raw.raf_weight ?? 0),
    confidence: Number(raw.confidence ?? 0.85),
    ml_confidence: Number(raw.ml_confidence ?? raw.confidence ?? 0.85),
    llm_confidence: Number(raw.llm_confidence ?? raw.confidence ?? 0.85),
    polarity: (raw.polarity as string | null) ?? 'active',
    meat_evidence: (raw.meat_evidence as HCCSupportingICD['meat_evidence']) ?? null,
    evidence_spans: supportingText
      ? [{ text: supportingText, section: (raw.source_section as string | null) ?? null, start: null, end: null }]
      : [],
    date_of_service: (raw.date_of_service as string | null) ?? null,
    provider: (raw.provider as string | null) ?? null,
    is_suppressed: Boolean(raw.is_suppressed),
    suppressed_by: (raw.suppressed_by as string | null) ?? null,
  };
}

function normalizeHCC(raw: Record<string, unknown>): HCCCode {
  return {
    hcc_code: String(raw.hcc_code ?? ''),
    hcc_description: String(raw.hcc_description ?? ''),
    raf_weight: Number(raw.raf_weight ?? 0),
    hierarchy_applied: Boolean(raw.hierarchy_applied),
    suppresses: Array.isArray(raw.suppresses) ? raw.suppresses.map(String) : [],
    supported_icds: Array.isArray(raw.supported_icds)
      ? (raw.supported_icds as Record<string, unknown>[]).map(normalizeSupportingICD)
      : [],
    audit_risk: (raw.audit_risk as string | null) ?? null,
  };
}

export async function getHCCPack(chartId: string): Promise<HCCPack> {
  const { data } = await apiClient.get<Record<string, unknown>>(`/risk/${chartId}/hcc-pack`);
  return {
    chart_id: String(data.chart_id ?? chartId),
    patient: (data.patient as Record<string, unknown> | null) ?? null,
    measurement_year: (data.measurement_year as number | null) ?? null,
    processing_timestamp: (data.processing_timestamp as string | null) ?? null,
    payable_hccs: Array.isArray(data.payable_hccs)
      ? (data.payable_hccs as Record<string, unknown>[]).map(normalizeHCC)
      : [],
    unsupported_candidates: Array.isArray(data.unsupported_candidates)
      ? data.unsupported_candidates as HCCPack['unsupported_candidates']
      : [],
    raf_summary: (data.raf_summary as RAFSummary) ?? {
      total_raf_score: 0,
      demographic_raf: 0,
      hcc_raf: 0,
      hcc_count: Number(data.payable_hcc_count ?? 0),
      payable_hcc_count: Number(data.payable_hcc_count ?? 0),
      suppressed_hcc_count: Number(data.suppressed_hcc_count ?? 0),
      hcc_details: [],
      segment: '',
    },
    pipeline_metadata: (data.pipeline_metadata as Record<string, unknown> | null) ?? null,
  };
}

export async function getRAFSummary(chartId: string): Promise<RAFSummary> {
  const { data } = await apiClient.get<RAFSummary>(`/risk/${chartId}/raf-summary`);
  return data;
}

export async function getHierarchy(chartId: string): Promise<HierarchyDetail> {
  const { data } = await apiClient.get<Record<string, unknown>>(`/risk/${chartId}/hierarchy`);
  return {
    chart_id: String(data.chart_id ?? chartId),
    hierarchy_details: Array.isArray(data.hierarchy_details)
      ? data.hierarchy_details as HierarchyDetail['hierarchy_details']
      : [],
  };
}

export interface MLPrediction {
  icd10_code: string;
  icd10_description: string;
  hcc_code: string | null;
  hcc_description: string | null;
  confidence: number;
  supporting_text: string | null;
  [key: string]: unknown;
}

export interface MLPredictionsResponse {
  predictions?: MLPrediction[];
  ml_predictions?: MLPrediction[];
}

export async function getMLPredictions(chartId: string): Promise<MLPredictionsResponse> {
  try {
    const { data } = await apiClient.get<Record<string, unknown>>(`/clinical/${chartId}/ra-candidates`);
    const rows = Array.isArray(data.predictions)
      ? data.predictions
      : Array.isArray(data.ra_candidates)
        ? data.ra_candidates
        : [];
    return {
      predictions: (rows as Record<string, unknown>[]).map((row) => ({
        icd10_code: String(row.icd10_code ?? ''),
        icd10_description: String(row.icd10_description ?? row.description ?? row.concept ?? ''),
        hcc_code: row.hcc_code ? String(row.hcc_code) : null,
        hcc_description: row.hcc_description ? String(row.hcc_description) : null,
        confidence: Number(row.confidence ?? 0),
        supporting_text: row.supporting_text ? String(row.supporting_text) : null,
      })),
    };
  } catch {
    return { predictions: [] };
  }
}

export interface VerifiedICD {
  icd10_code: string;
  icd10_description: string;
  hcc_code: string | null;
  confidence: number;
  ml_confidence: number;
  llm_confidence: number;
  meat_evidence: {
    monitored: boolean;
    evaluated: boolean;
    assessed: boolean;
    treated: boolean;
  } | null;
  verification_status: string;
  [key: string]: unknown;
}

export interface VerifiedICDsResponse {
  verified_icds?: VerifiedICD[];
  icds?: VerifiedICD[];
}

export async function getVerifiedICDs(chartId: string): Promise<VerifiedICDsResponse> {
  try {
    const pack = await getHCCPack(chartId);
    const flattened = (pack.payable_hccs ?? []).flatMap((hcc) =>
      (hcc.supported_icds ?? []).map((icd) => ({
        icd10_code: icd.icd10_code,
        icd10_description: icd.icd10_description,
        hcc_code: hcc.hcc_code || null,
        confidence: Number(icd.confidence ?? 0),
        ml_confidence: Number(icd.ml_confidence ?? icd.confidence ?? 0),
        llm_confidence: Number(icd.llm_confidence ?? icd.confidence ?? 0),
        meat_evidence: icd.meat_evidence ?? null,
        verification_status: 'verified',
      })),
    );
    return { verified_icds: flattened };
  } catch {
    return { verified_icds: [] };
  }
}
