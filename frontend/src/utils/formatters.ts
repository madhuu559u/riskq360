import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '--';
  const d = dayjs(iso);
  if (!d.isValid()) return '--';
  return d.format('MMM D, YYYY');
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '--';
  const d = dayjs(iso);
  if (!d.isValid()) return '--';
  return d.format('MMM D, YYYY h:mm A');
}

export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return '--';
  const d = dayjs(iso);
  if (!d.isValid()) return '--';
  return d.fromNow();
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '--';
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins < 60) return `${mins}m ${secs}s`;
  const hours = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return `${hours}h ${remainMins}m`;
}

export function formatNumber(n: number | null | undefined, decimals?: number): string {
  if (n === null || n === undefined) return '--';
  return n.toLocaleString('en-US', {
    minimumFractionDigits: decimals ?? 0,
    maximumFractionDigits: decimals ?? 2,
  });
}

export function formatPercent(n: number | null | undefined): string {
  if (n === null || n === undefined) return '--';
  return `${(n * 100).toFixed(1)}%`;
}

export function formatPercentValue(n: number | null | undefined): string {
  if (n === null || n === undefined) return '--';
  return `${n.toFixed(1)}%`;
}

export function formatRAF(n: number | null | undefined): string {
  if (n === null || n === undefined) return '--';
  return n.toFixed(3);
}

export function truncate(str: string | null | undefined, max: number): string {
  if (!str) return '';
  if (str.length <= max) return str;
  return str.slice(0, max) + '...';
}

export function formatCategory(raw: string | null | undefined): string {
  if (!raw) return '';
  return raw
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatConfidence(n: number | null | undefined): string {
  if (n === null || n === undefined) return '--';
  return `${(n * 100).toFixed(0)}%`;
}

export function formatChartId(chartId: string | null | undefined, filename?: string): string {
  // Prefer showing filename without .pdf extension for readability
  if (filename) {
    const name = filename.replace(/\.pdf$/i, '');
    return name.length > 20 ? name.slice(0, 20) + '...' : name;
  }
  if (!chartId) return '--';
  if (chartId.length <= 12) return chartId;
  return chartId.slice(0, 12);
}

