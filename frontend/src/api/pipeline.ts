import apiClient from './client';
import type { PipelineRun, PipelineLog } from '../types/api';

export async function getPipelineRuns(): Promise<{ runs: PipelineRun[] }> {
  const { data } = await apiClient.get<{ runs: PipelineRun[] }>('/pipeline/runs');
  return data;
}

export async function getPipelineRunsByChart(
  chartId: string,
): Promise<{ runs: PipelineRun[] }> {
  const { data } = await apiClient.get<{ runs: PipelineRun[] }>(
    `/pipeline/runs/chart/${chartId}`,
  );
  return data;
}

export async function getPipelineStats(
  chartId: string,
): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get<Record<string, unknown>>(
    `/pipeline/stats/${chartId}`,
  );
  return data;
}

export async function getPipelineLogs(
  runId: string,
): Promise<{ logs?: PipelineLog[]; pipeline_log?: PipelineLog[] }> {
  try {
    const { data } = await apiClient.get<{ logs?: PipelineLog[]; pipeline_log?: PipelineLog[] }>(
      `/pipeline/runs/${runId}`,
    );
    return data;
  } catch {
    return { logs: [] };
  }
}

export async function rerunPipeline(runId: string): Promise<{ message: string; run_id: string }> {
  try {
    const { data } = await apiClient.post<{ message: string; run_id: string }>(
      `/pipeline/runs/${runId}/rerun`,
    );
    return data;
  } catch {
    return { message: 'Rerun not available', run_id: runId };
  }
}
