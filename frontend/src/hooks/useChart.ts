import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import {
  getCharts,
  getChart,
  uploadChart,
  deleteChart,
  processChart,
  type GetChartsParams,
} from '../api/charts';
import {
  getDiagnoses,
  getVitals,
  getLabs,
  getMedications,
  getSentences,
  getEncounters,
} from '../api/clinical';
import {
  getHCCPack,
  getRAFSummary,
  getHierarchy,
  getMLPredictions,
  getVerifiedICDs,
} from '../api/risk';
import { getHEDISMeasures, getHEDISGaps } from '../api/hedis';
import { getAuditPack, reviewDiagnosis } from '../api/audit';
import {
  addDiagnosis as apiAddDiagnosis,
  acceptDiagnosis as apiAcceptDiagnosis,
  rejectDiagnosis as apiRejectDiagnosis,
  updateDiagnosis as apiUpdateDiagnosis,
  deleteDiagnosis as apiDeleteDiagnosis,
  addHCC as apiAddHCC,
  acceptHCC as apiAcceptHCC,
  rejectHCC as apiRejectHCC,
  addHEDIS as apiAddHEDIS,
  acceptHEDIS as apiAcceptHEDIS,
  rejectHEDIS as apiRejectHEDIS,
  updateHEDIS as apiUpdateHEDIS,
  saveDocument as apiSaveDocument,
  getReviewSummary,
  suggestCodes,
  type AddDiagnosisPayload,
  type AcceptDiagnosisPayload,
  type ReviewPayload,
  type UpdateDiagnosisPayload,
  type AddHCCPayload,
  type AddHEDISPayload,
  type UpdateHEDISPayload,
  type SaveDocumentPayload,
} from '../api/review';
import { getPipelineRuns, getPipelineLogs } from '../api/pipeline';
import { getDashboardStats, getDBStats, getRecentActivity } from '../api/dashboard';
import {
  getConfig,
  updateConfig,
  getPrompts,
  getFeatureFlags,
  updateFeatureFlags,
  getHedisMeasureCatalog,
  updateHedisMeasureProfile,
  getHedisMeasureDefinition,
  saveHedisMeasureDefinition,
  deleteHedisMeasureDefinition,
} from '../api/config';
import type { ReviewUpdate, SystemConfig, FeatureFlags } from '../types/api';

const QUERY_DEFAULTS = {
  staleTime: 30000,
  retry: 1,
  refetchOnWindowFocus: false,
} as const;

// ---------------------------------------------------------------------------
// Chart Management
// ---------------------------------------------------------------------------

export function useCharts(params?: GetChartsParams) {
  return useQuery({
    queryKey: ['charts', params],
    queryFn: () => getCharts(params),
    ...QUERY_DEFAULTS,
    refetchInterval: 10000,
  });
}

export function useChart(chartId: string | null | undefined) {
  const validId = chartId && chartId !== 'undefined' ? chartId : null;
  return useQuery({
    queryKey: ['chart', validId],
    queryFn: () => getChart(validId!),
    enabled: !!validId,
    ...QUERY_DEFAULTS,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'processing' || status === 'running') return 5000;
      return false;
    },
  });
}

export function useUploadChart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadChart(file),
    onSuccess: (data) => {
      notifications.show({
        title: 'Chart Uploaded',
        message: `Chart ${data.chart_id} uploaded and processing started.`,
        color: 'green',
        autoClose: 4000,
      });
      queryClient.invalidateQueries({ queryKey: ['charts'] });
    },
    onError: () => {
      // Error notification handled by axios interceptor
    },
  });
}

export function useDeleteChart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (chartId: string) => deleteChart(chartId),
    onSuccess: (_data, chartId) => {
      notifications.show({
        title: 'Chart Deleted',
        message: `Chart ${chartId} has been deleted.`,
        color: 'green',
        autoClose: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['charts'] });
      queryClient.removeQueries({ queryKey: ['chart', chartId] });
    },
  });
}

export function useProcessChart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (chartId: string) => processChart(chartId),
    onSuccess: (_data, chartId) => {
      notifications.show({
        title: 'Processing Started',
        message: `Re-processing chart ${chartId}.`,
        color: 'blue',
        autoClose: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['chart', chartId] });
      queryClient.invalidateQueries({ queryKey: ['charts'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Clinical Data
// ---------------------------------------------------------------------------

export function useDiagnoses(chartId: string | null) {
  return useQuery({
    queryKey: ['diagnoses', chartId],
    queryFn: () => getDiagnoses(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
    select: (data) => data.diagnoses,
  });
}

export function useVitals(chartId: string | null) {
  return useQuery({
    queryKey: ['vitals', chartId],
    queryFn: () => getVitals(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
    select: (data) => data.vitals,
  });
}

export function useLabs(chartId: string | null) {
  return useQuery({
    queryKey: ['labs', chartId],
    queryFn: () => getLabs(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
    select: (data) => data.lab_results ?? data.labs ?? [],
  });
}

export function useMedications(chartId: string | null) {
  return useQuery({
    queryKey: ['medications', chartId],
    queryFn: () => getMedications(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
    select: (data) => data.medications,
  });
}

export function useSentences(chartId: string | null) {
  return useQuery({
    queryKey: ['sentences', chartId],
    queryFn: () => getSentences(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
    select: (data) => data.sentences,
  });
}

export function useEncounters(chartId: string | null) {
  return useQuery({
    queryKey: ['encounters', chartId],
    queryFn: () => getEncounters(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
    select: (data) => data.encounters,
  });
}

// ---------------------------------------------------------------------------
// Risk Adjustment
// ---------------------------------------------------------------------------

export function useHCCPack(chartId: string | null) {
  return useQuery({
    queryKey: ['hcc-pack', chartId],
    queryFn: () => getHCCPack(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
  });
}

export function useRAFSummary(chartId: string | null) {
  return useQuery({
    queryKey: ['raf-summary', chartId],
    queryFn: () => getRAFSummary(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
  });
}

export function useHierarchy(chartId: string | null) {
  return useQuery({
    queryKey: ['hierarchy', chartId],
    queryFn: () => getHierarchy(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
  });
}

export function useMLPredictions(chartId: string | null) {
  return useQuery({
    queryKey: ['ml-predictions', chartId],
    queryFn: () => getMLPredictions(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
    select: (data) => data.predictions ?? data.ml_predictions ?? [],
  });
}

export function useVerifiedICDs(chartId: string | null) {
  return useQuery({
    queryKey: ['verified-icds', chartId],
    queryFn: () => getVerifiedICDs(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
    select: (data) => data.verified_icds ?? data.icds ?? [],
  });
}

// ---------------------------------------------------------------------------
// HEDIS
// ---------------------------------------------------------------------------

export function useHEDISMeasures(chartId: string | null) {
  return useQuery({
    queryKey: ['hedis-measures', chartId],
    queryFn: () => getHEDISMeasures(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
  });
}

export function useHEDISGaps(chartId: string | null) {
  return useQuery({
    queryKey: ['hedis-gaps', chartId],
    queryFn: () => getHEDISGaps(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
    select: (data) => data.gaps,
  });
}

// ---------------------------------------------------------------------------
// Audit & Review
// ---------------------------------------------------------------------------

export function useAuditPack(chartId: string | null) {
  return useQuery({
    queryKey: ['audit-pack', chartId],
    queryFn: () => getAuditPack(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
  });
}

export function useReviewDiagnosis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, update }: { id: number | string; update: ReviewUpdate }) =>
      reviewDiagnosis(id, update),
    onSuccess: () => {
      notifications.show({
        title: 'Review Submitted',
        message: 'Diagnosis review has been recorded.',
        color: 'green',
        autoClose: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['diagnoses'] });
      queryClient.invalidateQueries({ queryKey: ['hcc-pack'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Review Workflow — Diagnosis CRUD
// ---------------------------------------------------------------------------

export function useAddDiagnosis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AddDiagnosisPayload) => apiAddDiagnosis(payload),
    onSuccess: () => {
      notifications.show({ title: 'Diagnosis Added', message: 'New diagnosis has been added by coder.', color: 'green', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['diagnoses'] });
      queryClient.invalidateQueries({ queryKey: ['hcc-pack'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

export function useAcceptDiagnosis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number | string; payload: AcceptDiagnosisPayload }) =>
      apiAcceptDiagnosis(id, payload),
    onSuccess: () => {
      notifications.show({ title: 'Diagnosis Accepted', message: 'Diagnosis has been accepted.', color: 'green', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['diagnoses'] });
      queryClient.invalidateQueries({ queryKey: ['hcc-pack'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

export function useRejectDiagnosis2() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number | string; payload: ReviewPayload }) =>
      apiRejectDiagnosis(id, payload),
    onSuccess: () => {
      notifications.show({ title: 'Diagnosis Rejected', message: 'Diagnosis has been rejected.', color: 'orange', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['diagnoses'] });
      queryClient.invalidateQueries({ queryKey: ['hcc-pack'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

export function useUpdateDiagnosis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number | string; payload: UpdateDiagnosisPayload }) =>
      apiUpdateDiagnosis(id, payload),
    onSuccess: () => {
      notifications.show({ title: 'Diagnosis Updated', message: 'Diagnosis has been updated.', color: 'blue', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['diagnoses'] });
      queryClient.invalidateQueries({ queryKey: ['hcc-pack'] });
    },
  });
}

export function useDeleteDiagnosis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reviewer, notes }: { id: number | string; reviewer: string; notes?: string }) =>
      apiDeleteDiagnosis(id, reviewer, notes),
    onSuccess: () => {
      notifications.show({ title: 'Diagnosis Deleted', message: 'Diagnosis has been removed.', color: 'red', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['diagnoses'] });
      queryClient.invalidateQueries({ queryKey: ['hcc-pack'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Review Workflow — HCC CRUD
// ---------------------------------------------------------------------------

export function useAddHCC() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AddHCCPayload) => apiAddHCC(payload),
    onSuccess: () => {
      notifications.show({ title: 'HCC Added', message: 'New HCC code has been added.', color: 'green', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['hcc-pack'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

export function useAcceptHCC() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number | string; payload: ReviewPayload }) =>
      apiAcceptHCC(id, payload),
    onSuccess: () => {
      notifications.show({ title: 'HCC Accepted', message: 'HCC has been accepted.', color: 'green', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['hcc-pack'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

export function useRejectHCC() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number | string; payload: ReviewPayload }) =>
      apiRejectHCC(id, payload),
    onSuccess: () => {
      notifications.show({ title: 'HCC Rejected', message: 'HCC has been moved to suppressed.', color: 'orange', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['hcc-pack'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Review Workflow — HEDIS CRUD
// ---------------------------------------------------------------------------

export function useAddHEDIS() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AddHEDISPayload) => apiAddHEDIS(payload),
    onSuccess: () => {
      notifications.show({ title: 'HEDIS Measure Added', message: 'New HEDIS measure has been added.', color: 'green', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['hedis-measures'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

export function useAcceptHEDIS() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number | string; payload: ReviewPayload }) =>
      apiAcceptHEDIS(id, payload),
    onSuccess: () => {
      notifications.show({ title: 'HEDIS Accepted', message: 'HEDIS measure has been accepted.', color: 'green', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['hedis-measures'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

export function useRejectHEDIS() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number | string; payload: ReviewPayload }) =>
      apiRejectHEDIS(id, payload),
    onSuccess: () => {
      notifications.show({ title: 'HEDIS Rejected', message: 'HEDIS measure has been rejected.', color: 'orange', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['hedis-measures'] });
      queryClient.invalidateQueries({ queryKey: ['audit-pack'] });
    },
  });
}

export function useUpdateHEDIS() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number | string; payload: UpdateHEDISPayload }) =>
      apiUpdateHEDIS(id, payload),
    onSuccess: () => {
      notifications.show({ title: 'HEDIS Updated', message: 'HEDIS measure has been updated.', color: 'blue', autoClose: 3000 });
      queryClient.invalidateQueries({ queryKey: ['hedis-measures'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Document Save & Coding Helper
// ---------------------------------------------------------------------------

export function useSaveDocument() {
  return useMutation({
    mutationFn: ({ chartId, payload }: { chartId: number | string; payload: SaveDocumentPayload }) =>
      apiSaveDocument(chartId, payload),
    onSuccess: () => {
      notifications.show({ title: 'Document Saved', message: 'All reviewed data has been saved.', color: 'green', autoClose: 4000 });
    },
  });
}

export function useReviewSummary(chartId: string | null) {
  return useQuery({
    queryKey: ['review-summary', chartId],
    queryFn: () => getReviewSummary(chartId!),
    enabled: !!chartId,
    ...QUERY_DEFAULTS,
  });
}

export function useCodingSuggestions(query: string, limit = 20, paymentOnly = false) {
  return useQuery({
    queryKey: ['coding-suggestions', query, limit, paymentOnly],
    queryFn: () => suggestCodes(query, limit, paymentOnly),
    enabled: query.trim().length >= 2,
    staleTime: 60000,
    retry: 0,
    refetchOnWindowFocus: false,
  });
}

// ---------------------------------------------------------------------------
// Pipeline
// ---------------------------------------------------------------------------

export function usePipelineRuns() {
  return useQuery({
    queryKey: ['pipeline-runs'],
    queryFn: getPipelineRuns,
    ...QUERY_DEFAULTS,
    select: (data) => data.runs,
  });
}

export function usePipelineLogs(runId: string | null) {
  return useQuery({
    queryKey: ['pipeline-logs', runId],
    queryFn: () => getPipelineLogs(runId!),
    enabled: !!runId,
    ...QUERY_DEFAULTS,
    select: (data) => data.logs ?? data.pipeline_log ?? [],
  });
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
    ...QUERY_DEFAULTS,
    refetchInterval: 30000,
  });
}

export function useDBStats() {
  return useQuery({
    queryKey: ['db-stats'],
    queryFn: getDBStats,
    ...QUERY_DEFAULTS,
  });
}

export function useRecentActivity() {
  return useQuery({
    queryKey: ['recent-activity'],
    queryFn: getRecentActivity,
    ...QUERY_DEFAULTS,
    refetchInterval: 15000,
    select: (data) => data.recent_activity,
  });
}

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: getConfig,
    ...QUERY_DEFAULTS,
    staleTime: 60000,
  });
}

export function useUpdateConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: Partial<SystemConfig>) => updateConfig(config),
    onSuccess: () => {
      notifications.show({
        title: 'Configuration Saved',
        message: 'System configuration has been updated.',
        color: 'green',
        autoClose: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export function usePrompts() {
  return useQuery({
    queryKey: ['prompts'],
    queryFn: getPrompts,
    ...QUERY_DEFAULTS,
    staleTime: 60000,
  });
}

export function useFeatureFlags() {
  return useQuery({
    queryKey: ['feature-flags'],
    queryFn: getFeatureFlags,
    ...QUERY_DEFAULTS,
    staleTime: 60000,
  });
}

export function useUpdateFeatureFlags() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (flags: FeatureFlags) => updateFeatureFlags(flags),
    onSuccess: () => {
      notifications.show({
        title: 'Feature Flags Updated',
        message: 'Feature flag settings have been saved.',
        color: 'green',
        autoClose: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['feature-flags'] });
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export function useHedisMeasureCatalog() {
  return useQuery({
    queryKey: ['hedis-measure-catalog'],
    queryFn: getHedisMeasureCatalog,
    ...QUERY_DEFAULTS,
    staleTime: 30000,
  });
}

export function useUpdateHedisMeasureProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (activeMeasureIds: string[]) => updateHedisMeasureProfile(activeMeasureIds),
    onSuccess: () => {
      notifications.show({
        title: 'HEDIS Profile Updated',
        message: 'Active/inactive measures saved to database profile.',
        color: 'green',
        autoClose: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['hedis-measure-catalog'] });
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export function useHedisMeasureDefinition(measureId: string | null) {
  return useQuery({
    queryKey: ['hedis-measure-definition', measureId],
    queryFn: () => getHedisMeasureDefinition(measureId!),
    enabled: !!measureId,
    ...QUERY_DEFAULTS,
    staleTime: 0,
  });
}

export function useSaveHedisMeasureDefinition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ measureId, definition }: { measureId: string; definition: Record<string, unknown> }) =>
      saveHedisMeasureDefinition(measureId, definition),
    onSuccess: () => {
      notifications.show({
        title: 'Measure Definition Saved',
        message: 'HEDIS measure YAML was updated.',
        color: 'green',
      });
      queryClient.invalidateQueries({ queryKey: ['hedis-measure-catalog'] });
    },
  });
}

export function useDeleteHedisMeasureDefinition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (measureId: string) => deleteHedisMeasureDefinition(measureId),
    onSuccess: () => {
      notifications.show({
        title: 'Measure Definition Deleted',
        message: 'HEDIS measure YAML was deleted.',
        color: 'orange',
      });
      queryClient.invalidateQueries({ queryKey: ['hedis-measure-catalog'] });
    },
  });
}
