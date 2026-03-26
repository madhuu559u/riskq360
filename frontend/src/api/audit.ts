import apiClient from './client';
import type { AuditPack, ReviewUpdate } from '../types/api';

export async function getAuditPack(chartId: string): Promise<AuditPack> {
  // Backend returns {reviews: [], count: 0} — normalize to AuditPack shape
  // Also fetch pipeline data to populate the audit panel
  const [reviewsRes, pipelineRes, statsRes] = await Promise.allSettled([
    apiClient.get(`/audit/${chartId}/reviews`),
    apiClient.get(`/pipeline/runs/chart/${chartId}`),
    apiClient.get(`/pipeline/stats/${chartId}`),
  ]);

  const reviews = reviewsRes.status === 'fulfilled' ? (reviewsRes.value.data as Record<string, unknown>) : {};
  const pipeline = pipelineRes.status === 'fulfilled' ? (pipelineRes.value.data as Record<string, unknown>) : {};
  const stats = statsRes.status === 'fulfilled' ? (statsRes.value.data as Record<string, unknown>) : {};

  const runs = (pipeline.runs ?? []) as Array<Record<string, unknown>>;
  const latestRun = runs[0];

  return {
    chart_id: chartId,
    run_id: String(latestRun?.id ?? latestRun?.run_id ?? ''),
    pipeline_log: runs.map((r) => ({
      step: String(r.mode ?? 'processing'),
      status: String(r.status ?? 'unknown'),
      duration_seconds: (r.duration_seconds as number) ?? null,
      timestamp: String(r.started_at ?? r.completed_at ?? ''),
    })),
    assertions_summary: {
      total: stats.assertions_raw ?? 0,
      audited: stats.assertions_audited ?? 0,
      model: stats.model_used ?? '',
    },
    reviews: (reviews.reviews ?? []) as Array<Record<string, unknown>>,
  };
}

export async function reviewDiagnosis(
  id: number | string,
  update: ReviewUpdate,
): Promise<ReviewUpdate> {
  const { data } = await apiClient.put<ReviewUpdate>(`/audit/review/assertion/${id}`, update);
  return data;
}

export async function reviewHCC(
  id: number | string,
  update: ReviewUpdate,
): Promise<ReviewUpdate> {
  const { data } = await apiClient.put<ReviewUpdate>(`/audit/review/assertion/${id}`, update);
  return data;
}

export interface PendingReviewItem {
  id: number;
  chart_id: string;
  type: string;
  icd10_code?: string;
  hcc_code?: string;
  description: string;
  status: string;
  [key: string]: unknown;
}

export async function getPendingReviews(): Promise<{
  pending?: PendingReviewItem[];
  items?: PendingReviewItem[];
}> {
  const { data } = await apiClient.get<{
    pending?: PendingReviewItem[];
    items?: PendingReviewItem[];
  }>('/audit/pending');
  return data;
}
