import apiClient from './client';
import type { Chart, ChartUploadResponse } from '../types/chart';

export interface GetChartsParams {
  status?: string;
  patient_name?: string;
  from_date?: string;
  to_date?: string;
}

export interface GetChartsResponse {
  charts: Chart[];
  total: number;
}

function normalizeChart(raw: Record<string, unknown>): Chart {
  const id = raw.id ?? raw.chart_id;
  const ra = (raw.risk_adjustment ?? raw.raf_summary ?? null) as Record<string, unknown> | null;
  const hs = (raw.hedis_summary ?? raw.hedis ?? null) as Record<string, unknown> | null;
  return {
    chart_id: String(id ?? ''),
    filename: String(raw.filename ?? ''),
    file_path: String(raw.file_path ?? ''),
    status: (raw.status as Chart['status']) ?? 'uploaded',
    started_at: (raw.created_at ?? raw.started_at ?? null) as string | null,
    completed_at: (raw.updated_at ?? raw.completed_at ?? null) as string | null,
    total_seconds: (raw.total_seconds as number | null) ?? null,
    pages_processed: (raw.page_count as number | null) ?? (raw.pages_processed as number | null) ?? null,
    quality_score_avg: (raw.quality_score_avg as number | null) ?? null,
    run_id: String(raw.run_id ?? ''),
    mode: (raw.mode as string | null) ?? null,
    patient_name: (raw.patient_name as string | null) ?? null,
    patient_dob: (raw.patient_dob as string | null) ?? null,
    raf_summary: ra
      ? {
          total_raf_score: Number(ra.total_raf_score ?? 0),
          demographic_raf: Number(ra.demographic_raf ?? 0),
          hcc_raf: Number(ra.hcc_raf ?? 0),
          hcc_count: Number(ra.hcc_count ?? ra.payable_hcc_count ?? 0),
          payable_hcc_count: Number(ra.payable_hcc_count ?? 0),
          suppressed_hcc_count: Number(ra.suppressed_hcc_count ?? 0),
          hcc_details: Array.isArray(ra.hcc_details)
            ? (ra.hcc_details as Array<{ hcc_code: string; hcc_description: string; raf_weight: number; icd_count: number }>)
            : [],
          segment: String(ra.segment ?? ''),
        }
      : null,
    hedis_summary: hs
      ? {
          total_measures: Number(hs.total_measures ?? 0),
          met_count: Number(hs.met_count ?? hs.met ?? 0),
          gap_count: Number(hs.gap_count ?? hs.gap ?? 0),
        }
      : null,
  };
}

export async function getCharts(params?: GetChartsParams): Promise<GetChartsResponse> {
  const { data } = await apiClient.get<Record<string, unknown>>('/charts', { params });
  const rawCharts = Array.isArray(data.charts) ? data.charts as Record<string, unknown>[] : [];
  return {
    charts: rawCharts.map(normalizeChart),
    total: Number(data.total ?? rawCharts.length),
  };
}

export async function getChart(chartId: string): Promise<Chart> {
  const { data } = await apiClient.get<Record<string, unknown>>(`/charts/${chartId}`);
  return normalizeChart(data);
}

export async function uploadChart(file: File): Promise<ChartUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<Record<string, unknown>>('/charts/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
  return {
    chart_id: String(data.id ?? data.chart_id ?? ''),
    run_id: String(data.run_id ?? ''),
    status: String(data.status ?? 'uploaded'),
    message: typeof data.message === 'string' ? data.message : undefined,
  };
}

export async function processChart(_chartId: string): Promise<{ message: string }> {
  return {
    message: 'Chart reprocessing is currently handled by the backend batch/CLI pipeline in this build.',
  };
}

export async function deleteChart(chartId: string): Promise<void> {
  await apiClient.delete(`/charts/${chartId}`);
}
