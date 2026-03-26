import type { Chart } from '../types/chart';

export function getChartFileName(chartId: string, chart?: Partial<Chart> | null): string {
  const rawPath = chart?.filename || chart?.file_path || `${chartId}.pdf`;
  const parts = String(rawPath).split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] || `${chartId}.pdf`;
}

export function getChartPdfUrl(chartId: string, chart?: Partial<Chart> | null): string {
  return `/api/charts/${encodeURIComponent(chartId)}/file`;
}
