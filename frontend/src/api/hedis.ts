import apiClient from './client';
import type { HEDISMeasuresResponse, HEDISGapItem, HEDISMeasure, HEDISEvidenceItem, MeasureStatus } from '../types/hedis';

function normalizeStatus(status: unknown, compliant: unknown): MeasureStatus {
  const value = String(status ?? '').toLowerCase();
  if (
    value === 'met' ||
    value === 'gap' ||
    value === 'not_applicable' ||
    value === 'excluded' ||
    value === 'indeterminate' ||
    value === 'inactive'
  ) {
    return value as MeasureStatus;
  }
  if (compliant === true) return 'met';
  if (compliant === false) return 'gap';
  return 'not_applicable';
}

function asEvidenceItems(raw: unknown): HEDISEvidenceItem[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      if (typeof item === 'string') {
        return {
          type: 'narrative',
          exact_quote: item,
          source: { exact_quote: item },
        } as HEDISEvidenceItem;
      }
      if (item && typeof item === 'object') {
        const ev = item as Record<string, unknown>;
        const source = (ev.source && typeof ev.source === 'object') ? (ev.source as Record<string, unknown>) : undefined;
        return {
          ...(ev as HEDISEvidenceItem),
          exact_quote: String(ev.exact_quote ?? source?.exact_quote ?? ''),
          page_number: Number(ev.page_number ?? source?.page) || undefined,
          source: source
            ? {
                ...source,
                page: Number(source.page) || undefined,
                exact_quote: String(source.exact_quote ?? ''),
              }
            : undefined,
        } as HEDISEvidenceItem;
      }
      return null;
    })
    .filter((x): x is HEDISEvidenceItem => Boolean(x));
}

function normalizeMeasureGap(raw: unknown): NonNullable<HEDISMeasure['gaps']>[number] {
  const item = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
  return {
    type: typeof item.type === 'string' ? item.type : undefined,
    description: String(item.description ?? item.actionable_reason ?? 'Evidence gap identified'),
    required_event: typeof item.required_event === 'string' ? item.required_event : undefined,
    required_event_name: typeof item.required_event_name === 'string' ? item.required_event_name : undefined,
    required_event_description: typeof item.required_event_description === 'string' ? item.required_event_description : undefined,
    actionable_reason: typeof item.actionable_reason === 'string' ? item.actionable_reason : undefined,
    window_start: typeof item.window_start === 'string' ? item.window_start : undefined,
    window_end: typeof item.window_end === 'string' ? item.window_end : undefined,
    window: typeof item.window === 'string' ? item.window : undefined,
  };
}

function normalizeMeasure(raw: Record<string, unknown>): HEDISMeasure {
  const status = normalizeStatus(raw.status, raw.compliant);
  const measureCode = String(raw.measure_code ?? raw.measure_id ?? raw.id ?? '');
  const measureName = String(raw.measure_name ?? raw.name ?? measureCode);
  const previewRaw =
    typeof raw.clinical_only_preview === 'object' && raw.clinical_only_preview
      ? (raw.clinical_only_preview as Record<string, unknown>)
      : null;

  return {
    measure_code: measureCode,
    measure_name: measureName,
    measure_id: String(raw.measure_id ?? raw.id ?? measureCode),
    id: String(raw.id ?? raw.measure_id ?? measureCode),
    eligible: Boolean(raw.eligible ?? raw.applicable),
    status,
    evidence: asEvidenceItems(raw.evidence ?? raw.evidence_used),
    target: (raw.target as string | null) ?? null,
    trace: Array.isArray(raw.trace) ? raw.trace as HEDISMeasure['trace'] : [],
    gaps: Array.isArray(raw.gaps) ? raw.gaps.map((g) => normalizeMeasureGap(g)) : [],
    confidence: typeof raw.confidence === 'number' ? raw.confidence : undefined,
    eligibility_reason: Array.isArray(raw.eligibility_reason) ? raw.eligibility_reason as string[] : [],
    compliance_reason: Array.isArray(raw.compliance_reason) ? raw.compliance_reason as string[] : [],
    missing_data: Array.isArray(raw.missing_data) ? raw.missing_data as string[] : [],
    exclusion_reason: typeof raw.exclusion_reason === 'string' ? raw.exclusion_reason : undefined,
    decision_reasoning: typeof raw.decision_reasoning === 'object' && raw.decision_reasoning
      ? raw.decision_reasoning as HEDISMeasure['decision_reasoning']
      : undefined,
    enrollment_dependency: typeof raw.enrollment_dependency === 'string' ? raw.enrollment_dependency : undefined,
    measure_definition: typeof raw.measure_definition === 'object' && raw.measure_definition
      ? raw.measure_definition as HEDISMeasure['measure_definition']
      : undefined,
    clinical_only_preview: previewRaw
      ? {
          ...(previewRaw as HEDISMeasure['clinical_only_preview']),
          evidence_used: asEvidenceItems(previewRaw.evidence_used),
          gaps: Array.isArray(previewRaw.gaps) ? previewRaw.gaps.map((g) => normalizeMeasureGap(g)) : [],
        }
      : undefined,
  };
}

function normalizeGap(raw: Record<string, unknown>): HEDISGapItem {
  const nestedGaps = Array.isArray(raw.gaps) ? raw.gaps as Record<string, unknown>[] : [];
  const firstGap = nestedGaps[0] ?? {};
  const actionable = raw.actionable_reason ?? firstGap.actionable_reason;
  const requiredEventName = raw.required_event_name ?? firstGap.required_event_name;
  const requiredEvent = raw.required_event ?? firstGap.required_event;
  const windowText = raw.window ?? firstGap.window;
  return {
    measure_code: String(raw.measure_code ?? raw.measure_id ?? raw.id ?? ''),
    measure_name: String(raw.measure_name ?? raw.name ?? ''),
    gap_description: String(actionable ?? raw.description ?? firstGap.description ?? raw.gap_description ?? 'Evidence gap identified'),
    missing_evidence: typeof (requiredEventName ?? requiredEvent) === 'string'
      ? String(requiredEventName ?? requiredEvent)
      : null,
    recommended_action: typeof windowText === 'string'
      ? `Review evidence window ${String(windowText)}`
      : null,
    priority: String(raw.priority ?? 'medium'),
  };
}

export async function getHEDISMeasures(chartId: string): Promise<HEDISMeasuresResponse> {
  const summaryPromise = apiClient
    .get<Record<string, unknown>>(`/hedis/${chartId}/summary`)
    .catch(() => ({ data: {} as Record<string, unknown> }));
  const [measuresRes, gapsRes, summaryRes] = await Promise.all([
    apiClient.get<Record<string, unknown>>(`/hedis/${chartId}/measures`),
    apiClient.get<Record<string, unknown>>(`/hedis/${chartId}/gaps`),
    summaryPromise,
  ]);

  const measuresPayload = measuresRes.data;
  const summaryPayload = summaryRes.data;

  const measures = Array.isArray(measuresPayload.measures)
    ? (measuresPayload.measures as Record<string, unknown>[]).map(normalizeMeasure)
    : [];

  const gapsFromDedicated = Array.isArray(gapsRes.data.gaps)
    ? (gapsRes.data.gaps as Record<string, unknown>[]).map(normalizeGap)
    : [];
  const gapsFromMeasures = Array.isArray(measuresPayload.gaps)
    ? (measuresPayload.gaps as Record<string, unknown>[]).map(normalizeGap)
    : [];
  const gaps = gapsFromDedicated.length > 0 ? gapsFromDedicated : gapsFromMeasures;

  const summary = (typeof measuresPayload.summary === 'object' && measuresPayload.summary
    ? measuresPayload.summary
    : summaryPayload) as Record<string, unknown>;

  const totalEligible = Number(
    summary.applicable ??
      summary.total_eligible ??
      summary.total_measures ??
      measures.filter((m) => m.eligible).length,
  );
  const totalMet = Number(summary.met ?? measures.filter((m) => m.status === 'met').length);
  const totalGaps = Number(summary.gap ?? summary.total_gaps ?? gaps.length);

  return {
    measurement_year: Number(
      measuresPayload.measurement_year ?? summary.measurement_year ?? new Date().getFullYear(),
    ),
    measures,
    gaps,
    total_eligible: Number.isFinite(totalEligible) ? totalEligible : 0,
    total_met: Number.isFinite(totalMet) ? totalMet : 0,
    total_gaps: Number.isFinite(totalGaps) ? totalGaps : 0,
    summary: {
      total_measures: Number(summary.total_measures ?? measures.length),
      applicable: Number(summary.applicable ?? measures.filter((m) => m.eligible).length),
      met: Number(summary.met ?? measures.filter((m) => m.status === 'met').length),
      gap: Number(summary.gap ?? gaps.length),
      excluded: Number(summary.excluded ?? measures.filter((m) => m.status === 'excluded').length),
      not_applicable: Number(summary.not_applicable ?? measures.filter((m) => m.status === 'not_applicable').length),
      indeterminate: Number(summary.indeterminate ?? measures.filter((m) => m.status === 'indeterminate').length),
      inactive: Number(summary.inactive ?? measures.filter((m) => m.status === 'inactive').length),
    },
    summary_preview:
      typeof measuresPayload.summary_preview === 'object' && measuresPayload.summary_preview
        ? {
            total_measures: Number((measuresPayload.summary_preview as Record<string, unknown>).total_measures ?? measures.length),
            applicable: Number((measuresPayload.summary_preview as Record<string, unknown>).applicable ?? 0),
            met: Number((measuresPayload.summary_preview as Record<string, unknown>).met ?? 0),
            gap: Number((measuresPayload.summary_preview as Record<string, unknown>).gap ?? 0),
            excluded: Number((measuresPayload.summary_preview as Record<string, unknown>).excluded ?? 0),
            not_applicable: Number((measuresPayload.summary_preview as Record<string, unknown>).not_applicable ?? 0),
            indeterminate: Number((measuresPayload.summary_preview as Record<string, unknown>).indeterminate ?? 0),
            inactive: Number((measuresPayload.summary_preview as Record<string, unknown>).inactive ?? measures.filter((m) => m.status === 'inactive').length),
          }
        : undefined,
    default_view_mode:
      measuresPayload.default_view_mode === 'clinical_preview' || measuresPayload.default_view_mode === 'strict'
        ? (measuresPayload.default_view_mode as HEDISMeasuresResponse['default_view_mode'])
        : undefined,
    measure_profile:
      typeof measuresPayload.measure_profile === 'object' && measuresPayload.measure_profile
        ? (measuresPayload.measure_profile as HEDISMeasuresResponse['measure_profile'])
        : undefined,
  };
}

export async function getHEDISGaps(chartId: string): Promise<{ gaps: HEDISGapItem[] }> {
  const { data } = await apiClient.get<Record<string, unknown>>(`/hedis/${chartId}/gaps`);
  return {
    gaps: Array.isArray(data.gaps)
      ? (data.gaps as Record<string, unknown>[]).map(normalizeGap)
      : [],
  };
}

