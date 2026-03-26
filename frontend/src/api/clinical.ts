import apiClient from './client';
import type {
  ClinicalEvidence,
  ClinicalSentence,
  Diagnosis,
  Encounter,
  LabResult,
  Medication,
  Vital,
} from '../types/clinical';

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function parseIcdCode(text: string): string {
  const match = text.match(/\b([A-TV-Z][0-9][0-9AB](?:\.[A-Z0-9]{1,4})?)\b/i);
  return match?.[1]?.toUpperCase() ?? '';
}

function stripIcdFromDescription(text: string): string {
  return text
    .replace(/\s*\(([A-TV-Z][0-9][0-9AB](?:\.[A-Z0-9]{1,4})?)\)\.?/gi, '')
    .replace(/^\d+\.\s*/, '')
    .trim();
}

function normalizeDiagnosis(raw: Record<string, unknown>): Diagnosis {
  const text = String(raw.canonical_concept ?? raw.concept ?? raw.text ?? '');
  const icdPrimary = Array.isArray(raw.icd_codes_primary) ? raw.icd_codes_primary[0] : null;
  const icdAny = Array.isArray(raw.icd_codes) ? raw.icd_codes[0] : null;
  const primaryCode = asRecord(icdPrimary).code ?? asRecord(icdAny).code;
  const section = String(raw.category ?? raw.source_section ?? '').replaceAll('_', ' ');

  return {
    id: typeof raw.id === 'number' ? raw.id : undefined,
    icd10_code: String(primaryCode ?? parseIcdCode(text)),
    icd9_code: null,
    snomed_code: null,
    description: stripIcdFromDescription(text || String(raw.text ?? '')),
    negation_status: (raw.status as Diagnosis['negation_status']) ?? 'active',
    negation_trigger: null,
    supporting_text: String(raw.exact_quote ?? raw.text ?? '') || null,
    source_section: section || null,
    date_of_service: (raw.effective_date as string | null) ?? null,
    provider: (asRecord(raw.structured).provider as string | null) ?? null,
  };
}

function normalizeVital(raw: Record<string, unknown>): Vital {
  const structured = asRecord(raw.structured);
  const systolic = asNumber(structured.bp_systolic ?? raw.systolic ?? raw.bp_systolic);
  const diastolic = asNumber(structured.bp_diastolic ?? raw.diastolic ?? raw.bp_diastolic);
  const hasValidBP =
    systolic !== null &&
    diastolic !== null &&
    systolic >= 70 &&
    systolic <= 260 &&
    diastolic >= 40 &&
    diastolic <= 160 &&
    systolic > diastolic;

  return {
    date: String(raw.effective_date ?? ''),
    weight: (raw.weight as string | null) ?? (structured.weight as string | null) ?? null,
    height: (raw.height as string | null) ?? (structured.height as string | null) ?? null,
    bmi: (raw.bmi as string | null) ?? (structured.bmi as string | null) ?? null,
    blood_pressure:
      (raw.blood_pressure as string | null) ??
      (hasValidBP ? `${systolic}/${diastolic}` : null),
    bp_systolic: hasValidBP ? systolic : null,
    bp_diastolic: hasValidBP ? diastolic : null,
    pulse: (raw.pulse as string | null) ?? (structured.pulse as string | null) ?? null,
    temperature:
      (raw.temperature as string | null) ??
      (structured.temperature as string | null) ??
      (structured.temp_f as string | null) ??
      (structured.temp_c as string | null) ??
      null,
    oxygen_saturation:
      (raw.oxygen_saturation as string | null) ??
      (structured.oxygen_saturation as string | null) ??
      (structured.spo2 as string | null) ??
      null,
    page_number: asNumber(raw.page_number),
    exact_quote: String(raw.exact_quote ?? raw.text ?? '') || null,
  };
}

function normalizeLab(raw: Record<string, unknown>): LabResult {
  const structured = asRecord(raw.structured);
  const value = raw.value ?? raw.result_value ?? structured.value ?? null;
  const unit = raw.unit ?? structured.unit ?? null;
  const valueText =
    value !== null && value !== undefined && String(value).trim().length > 0
      ? `${String(value)}${unit ? ` ${String(unit)}` : ''}`.trim()
      : String(raw.text ?? '');
  return {
    test_name: String(raw.test_name ?? raw.concept ?? raw.text ?? 'Unknown lab'),
    result_value: valueText,
    result_date: (raw.effective_date as string | null) ?? null,
    reference_range: (structured.reference_range as string | null) ?? null,
    hedis_measure: (structured.hedis_measure as string | null) ?? null,
    within_target: typeof structured.within_target === 'boolean' ? structured.within_target : null,
    page_number: asNumber(raw.page_number),
    exact_quote: String(raw.exact_quote ?? raw.text ?? '') || null,
  };
}

function normalizeMedication(raw: Record<string, unknown>): Medication {
  const normalized = asRecord(raw.medication_normalized);
  return {
    name: String(normalized.name ?? raw.name ?? raw.concept ?? raw.text ?? 'Unknown medication'),
    dose_form: (normalized.dose_form as string | null) ?? (raw.dose_form as string | null) ?? null,
    instructions:
      (normalized.sig as string | null) ??
      (raw.instructions as string | null) ??
      (raw.text as string | null) ??
      null,
    indication: (normalized.indication as string | null) ?? (raw.indication as string | null) ?? null,
    action: (normalized.action as string | null) ?? (raw.action as string | null) ?? null,
    page_number: asNumber(raw.page_number),
    exact_quote: String(raw.exact_quote ?? raw.evidence ?? raw.text ?? '') || null,
  };
}

function normalizeSentence(raw: Record<string, unknown>): ClinicalSentence {
  return {
    text: String(raw.text ?? raw.clean_text ?? ''),
    category: String(raw.category ?? 'clinical'),
    is_negated: String(raw.status ?? 'active') !== 'active',
    negation_trigger: null,
    negated_item: null,
  };
}

function normalizeEncounter(raw: Record<string, unknown>): Encounter {
  const evidenceItemsRaw = Array.isArray(raw.evidence_items) ? raw.evidence_items : [];
  const evidence_items: ClinicalEvidence[] = evidenceItemsRaw.map((item) => {
    const ev = asRecord(item);
    return {
      page_number: asNumber(ev.page_number),
      exact_quote: String(ev.exact_quote ?? '') || null,
      category: String(ev.category ?? '') || null,
      concept: String(ev.concept ?? '') || null,
    };
  });

  const medsRaw = Array.isArray(raw.medications) ? raw.medications : [];
  const normalizedMeds = medsRaw.map((m) => normalizeMedication(asRecord(m)));

  return {
    date: String(raw.date ?? ''),
    encounter_id: (raw.encounter_id as string | null) ?? null,
    provider: (raw.provider as string | null) ?? null,
    facility: (raw.facility as string | null) ?? null,
    type: (raw.type as string | null) ?? null,
    chief_complaint: (raw.chief_complaint as string | null) ?? null,
    page_number: asNumber(raw.page_number),
    evidence: String(raw.evidence ?? '') || null,
    evidence_items,
    assertion_count: asNumber(raw.assertion_count) ?? undefined,
    categories: Array.isArray(raw.categories) ? raw.categories.map((c) => String(c)) : undefined,
    telehealth_details: undefined,
    procedures: Array.isArray(raw.procedures) ? (raw.procedures as Encounter['procedures']) : [],
    medications: normalizedMeds,
    diagnoses: Array.isArray(raw.diagnoses) ? (raw.diagnoses as Encounter['diagnoses']) : [],
  };
}

export async function getDiagnoses(chartId: string): Promise<{ diagnoses: Diagnosis[] }> {
  const { data } = await apiClient.get<{ diagnoses?: Record<string, unknown>[] }>(`/clinical/${chartId}/diagnoses`);
  return { diagnoses: (data.diagnoses ?? []).map(normalizeDiagnosis) };
}

export async function getVitals(chartId: string): Promise<{ vitals: Vital[] }> {
  const { data } = await apiClient.get<{ vitals?: Record<string, unknown>[] }>(`/clinical/${chartId}/vitals`);
  return { vitals: (data.vitals ?? []).map(normalizeVital) };
}

export async function getLabs(chartId: string): Promise<{ lab_results?: LabResult[]; labs?: LabResult[] }> {
  const { data } = await apiClient.get<{ labs?: Record<string, unknown>[] }>(`/clinical/${chartId}/labs`);
  const labs = (data.labs ?? []).map(normalizeLab);
  return { labs, lab_results: labs };
}

export async function getMedications(chartId: string): Promise<{ medications: Medication[] }> {
  const { data } = await apiClient.get<{ medications?: Record<string, unknown>[] }>(`/clinical/${chartId}/medications`);
  return { medications: (data.medications ?? []).map(normalizeMedication) };
}

export async function getSentences(chartId: string): Promise<{ sentences: ClinicalSentence[] }> {
  const { data } = await apiClient.get<{ assertions?: Record<string, unknown>[]; sentences?: Record<string, unknown>[] }>(`/clinical/${chartId}/assertions`);
  return { sentences: (data.assertions ?? data.sentences ?? []).map(normalizeSentence) };
}

export async function getEncounters(chartId: string): Promise<{ encounters: Encounter[] }> {
  const { data } = await apiClient.get<{ encounters?: Record<string, unknown>[] }>(`/clinical/${chartId}/encounters`);
  return { encounters: (data.encounters ?? []).map(normalizeEncounter) };
}
