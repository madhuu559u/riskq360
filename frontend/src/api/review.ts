import apiClient from './client';

/* -------------------------------------------------------------------------- */
/* Types                                                                       */
/* -------------------------------------------------------------------------- */
export interface AddDiagnosisPayload {
  chart_id: number;
  icd10_code: string;
  description: string;
  reviewer: string;
  notes?: string | null;
  date_of_service?: string | null;
  page_number?: number | null;
  exact_quote?: string | null;
  hcc_code?: string | null;
  status?: string;
}

export interface ReviewPayload {
  reviewer: string;
  notes?: string | null;
}

export interface AcceptDiagnosisPayload extends ReviewPayload {
  date_of_service?: string | null;
}

export interface UpdateDiagnosisPayload {
  reviewer: string;
  icd10_code?: string | null;
  description?: string | null;
  notes?: string | null;
  date_of_service?: string | null;
  status?: string | null;
}

export interface AddHCCPayload {
  chart_id: number;
  hcc_code: string;
  hcc_description: string;
  raf_weight: number;
  reviewer: string;
  notes?: string | null;
  supported_icds?: Array<Record<string, unknown>> | null;
  measurement_year?: number | null;
}

export interface AddHEDISPayload {
  chart_id: number;
  measure_id: string;
  measure_name: string;
  status: string;
  reviewer: string;
  notes?: string | null;
  evidence?: Array<Record<string, unknown>> | null;
  measurement_year?: number | null;
}

export interface UpdateHEDISPayload {
  reviewer: string;
  status?: string | null;
  evidence?: Array<Record<string, unknown>> | null;
  notes?: string | null;
}

export interface SaveDocumentPayload {
  reviewer: string;
  comments?: string | null;
}

export interface CodingHelperResult {
  icd10_code: string;
  description: string;
  hcc_code: string;
  hcc_label: string;
  is_payment_hcc: boolean;
  score: number;
}

export interface CodingHelperResponse {
  query: string;
  results: CodingHelperResult[];
  count: number;
  index_size: number;
}

export interface ReviewSummary {
  chart_id: number;
  diagnoses: Record<string, unknown>;
  hccs: Record<string, unknown>;
  hedis: Record<string, unknown>;
  review_actions: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* Diagnosis Review API                                                        */
/* -------------------------------------------------------------------------- */
export async function addDiagnosis(payload: AddDiagnosisPayload) {
  const { data } = await apiClient.post('/review/diagnosis', payload);
  return data;
}

export async function acceptDiagnosis(assertionId: number | string, payload: AcceptDiagnosisPayload) {
  const { data } = await apiClient.put(`/review/diagnosis/${assertionId}/accept`, payload);
  return data;
}

export async function rejectDiagnosis(assertionId: number | string, payload: ReviewPayload) {
  const { data } = await apiClient.put(`/review/diagnosis/${assertionId}/reject`, payload);
  return data;
}

export async function updateDiagnosis(assertionId: number | string, payload: UpdateDiagnosisPayload) {
  const { data } = await apiClient.put(`/review/diagnosis/${assertionId}`, payload);
  return data;
}

export async function deleteDiagnosis(assertionId: number | string, reviewer: string, notes?: string) {
  const params: Record<string, string> = { reviewer };
  if (notes) params.notes = notes;
  const { data } = await apiClient.delete(`/review/diagnosis/${assertionId}`, { params });
  return data;
}

/* -------------------------------------------------------------------------- */
/* HCC Review API                                                              */
/* -------------------------------------------------------------------------- */
export async function addHCC(payload: AddHCCPayload) {
  const { data } = await apiClient.post('/review/hcc', payload);
  return data;
}

export async function acceptHCC(hccId: number | string, payload: ReviewPayload) {
  const { data } = await apiClient.put(`/review/hcc/${hccId}/accept`, payload);
  return data;
}

export async function rejectHCC(hccId: number | string, payload: ReviewPayload) {
  const { data } = await apiClient.put(`/review/hcc/${hccId}/reject`, payload);
  return data;
}

/* -------------------------------------------------------------------------- */
/* HEDIS Review API                                                            */
/* -------------------------------------------------------------------------- */
export async function addHEDIS(payload: AddHEDISPayload) {
  const { data } = await apiClient.post('/review/hedis', payload);
  return data;
}

export async function acceptHEDIS(hedisId: number | string, payload: ReviewPayload) {
  const { data } = await apiClient.put(`/review/hedis/${hedisId}/accept`, payload);
  return data;
}

export async function rejectHEDIS(hedisId: number | string, payload: ReviewPayload) {
  const { data } = await apiClient.put(`/review/hedis/${hedisId}/reject`, payload);
  return data;
}

export async function updateHEDIS(hedisId: number | string, payload: UpdateHEDISPayload) {
  const { data } = await apiClient.put(`/review/hedis/${hedisId}`, payload);
  return data;
}

/* -------------------------------------------------------------------------- */
/* Document Save & Summary                                                     */
/* -------------------------------------------------------------------------- */
export async function saveDocument(chartId: number | string, payload: SaveDocumentPayload) {
  const { data } = await apiClient.post(`/review/save-document/${chartId}`, payload);
  return data;
}

export async function getReviewSummary(chartId: number | string): Promise<ReviewSummary> {
  const { data } = await apiClient.get<ReviewSummary>(`/review/summary/${chartId}`);
  return data;
}

/* -------------------------------------------------------------------------- */
/* Coding Helper API                                                           */
/* -------------------------------------------------------------------------- */
export async function suggestCodes(
  query: string,
  limit = 20,
  paymentOnly = false,
): Promise<CodingHelperResponse> {
  const { data } = await apiClient.get<CodingHelperResponse>('/coding-helper/suggest', {
    params: { q: query, limit, payment_only: paymentOnly },
  });
  return data;
}
