export interface DashboardStats {
  total_charts: number;
  completed: number;
  failed: number;
  success_rate: number;
  avg_processing_seconds: number;
  total_processing_seconds: number;
}

export interface DBStats {
  message: string;
  tables: { name: string; rows: number }[] | Record<string, number>;
}

export interface RecentActivityItem {
  chart_id: string;
  event: string;
  timestamp: string;
  status?: string;
  [key: string]: unknown;
}

export interface PipelineRun {
  chart_id: string;
  run_id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  total_seconds: number | null;
  raf_summary: { total_raf_score: number; hcc_count: number; payable_hcc_count: number } | null;
  pages_processed: number | null;
  mode: string | null;
}

export interface PipelineLog {
  step: string;
  status: string;
  duration_seconds: number | null;
  duration?: number | null;
  timestamp: string | null;
  created_at?: string | null;
  [key: string]: unknown;
}

export interface AuditPack {
  chart_id: string;
  run_id: string;
  pipeline_log: PipelineLog[];
  assertions_summary?: Record<string, unknown>;
  hcc_summary?: Record<string, unknown>;
  hedis_summary?: Record<string, unknown>;
  reviews?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export interface ReviewUpdate {
  action: 'approved' | 'rejected';
  reviewer: string;
  notes?: string | null;
}

export interface SystemConfig {
  llm: { provider: string; model: string; temperature: number; max_tokens: number };
  pipeline: { chunk_size: number; chunk_overlap: number; quality_threshold: number; measurement_year: number };
  ml: { ml_confidence_threshold: number; tfidf_similarity_threshold: number };
  feature_flags: Record<string, boolean>;
}

export interface FeatureFlags {
  [key: string]: boolean;
}

export interface PromptTemplates {
  db_prompts: Record<string, Record<string, unknown>>;
  file_prompts: Record<string, string>;
}

export interface HedisMeasureCatalogItem {
  measure_id: string;
  name: string;
  description: string;
  domain: string;
  version: string;
  active: boolean;
  rules_summary: string[];
  valuesets_needed: string[];
  data_sources: string[];
}

export interface HedisMeasureProfile {
  profile_id: string;
  active_measure_ids: string[];
  updated_at?: string;
  updated_by?: string;
}

export interface HedisMeasureCatalogResponse {
  profile: HedisMeasureProfile;
  total_measures: number;
  active_count: number;
  inactive_count: number;
  measures: HedisMeasureCatalogItem[];
}
