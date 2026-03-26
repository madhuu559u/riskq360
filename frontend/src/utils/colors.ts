import type { NegationStatus } from '../types/clinical';
import type { MeasureStatus } from '../types/hedis';

export const STATUS_COLORS: Record<string, string> = {
  uploaded: 'blue',
  processing: 'yellow',
  running: 'yellow',
  completed: 'green',
  failed: 'red',
  error: 'red',
  pending: 'orange',
};

export function getStatusColor(status: string): string {
  return STATUS_COLORS[status.toLowerCase()] || 'gray';
}

export const NEGATION_COLORS: Record<NegationStatus, string> = {
  active: 'green',
  negated: 'red',
  resolved: 'blue',
  historical: 'gray',
  family_history: 'violet',
  uncertain: 'yellow',
};

export function getNegationColor(status: NegationStatus): string {
  return NEGATION_COLORS[status] || 'gray';
}

export const NEGATION_LABELS: Record<NegationStatus, string> = {
  active: 'Active',
  negated: 'Negated',
  resolved: 'Resolved',
  historical: 'Historical',
  family_history: 'Family Hx',
  uncertain: 'Uncertain',
};

export function getNegationLabel(status: NegationStatus): string {
  return NEGATION_LABELS[status] || status;
}

export const MEASURE_STATUS_COLORS: Record<MeasureStatus, string> = {
  met: 'green',
  gap: 'red',
  not_applicable: 'gray',
  excluded: 'dimmed',
  indeterminate: 'yellow',
  inactive: 'gray',
};

export function getMeasureStatusColor(status: MeasureStatus): string {
  return MEASURE_STATUS_COLORS[status] || 'gray';
}

export const MEASURE_STATUS_LABELS: Record<MeasureStatus, string> = {
  met: 'Met',
  gap: 'Gap',
  not_applicable: 'N/A',
  excluded: 'Excluded',
  indeterminate: 'Indeterminate',
  inactive: 'Inactive',
};

export function getMeasureStatusLabel(status: MeasureStatus): string {
  return MEASURE_STATUS_LABELS[status] || status;
}

export const RISK_LEVEL_COLORS: Record<string, string> = {
  low: 'green',
  medium: 'yellow',
  high: 'red',
  critical: 'red',
};

export function getRiskLevelColor(level: string): string {
  return RISK_LEVEL_COLORS[level.toLowerCase()] || 'gray';
}

export const HIGHLIGHT_COLORS: Record<string, { fill: string; stroke: string; opacity: number }> = {
  diagnosis: { fill: '#3B82F6', stroke: '#2563EB', opacity: 0.25 },
  hedis: { fill: '#10B981', stroke: '#059669', opacity: 0.25 },
  negated: { fill: '#EF4444', stroke: '#DC2626', opacity: 0.25 },
  meat: { fill: '#F59E0B', stroke: '#D97706', opacity: 0.25 },
  ml: { fill: '#8B5CF6', stroke: '#7C3AED', opacity: 0.25 },
  search: { fill: '#FBBF24', stroke: '#F59E0B', opacity: 0.35 },
  icd: { fill: '#3B82F6', stroke: '#2563EB', opacity: 0.25 },
};

export function getHighlightColor(
  type: string,
): { fill: string; stroke: string; opacity: number } {
  return HIGHLIGHT_COLORS[type] || HIGHLIGHT_COLORS.diagnosis;
}

export const CONFIDENCE_COLORS = {
  high: 'green',
  medium: 'yellow',
  low: 'red',
} as const;

export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return CONFIDENCE_COLORS.high;
  if (confidence >= 0.5) return CONFIDENCE_COLORS.medium;
  return CONFIDENCE_COLORS.low;
}

export const PIPELINE_STEP_COLORS: Record<string, string> = {
  ingestion: '#3B82F6',
  extraction: '#8B5CF6',
  ml_prediction: '#EC4899',
  icd_retrieval: '#F97316',
  verification: '#10B981',
  decisioning: '#06B6D4',
  hedis: '#14B8A6',
  audit: '#F59E0B',
};

export function getPipelineStepColor(step: string): string {
  const normalized = step.toLowerCase().replace(/[\s-]/g, '_');
  return PIPELINE_STEP_COLORS[normalized] || '#6B7280';
}
