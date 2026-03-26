export interface Chart {
  chart_id: string;
  filename: string;
  file_path: string;
  status: 'uploaded' | 'processing' | 'running' | 'completed' | 'failed';
  started_at: string | null;
  completed_at: string | null;
  total_seconds: number | null;
  raf_summary: ChartRAFSummary | null;
  hedis_summary: ChartHEDISSummary | null;
  pages_processed: number | null;
  quality_score_avg: number | null;
  run_id: string;
  mode: string | null;
  patient_name: string | null;
  patient_dob: string | null;
}

export interface ChartRAFSummary {
  total_raf_score: number;
  demographic_raf: number;
  hcc_raf: number;
  hcc_count: number;
  payable_hcc_count: number;
  suppressed_hcc_count: number;
  hcc_details: { hcc_code: string; hcc_description: string; raf_weight: number; icd_count: number }[];
  segment: string;
}

export interface ChartHEDISSummary {
  total_measures: number;
  met_count: number;
  gap_count: number;
}

export interface ChartUploadResponse {
  chart_id: string;
  run_id: string;
  status: string;
  message?: string;
}
