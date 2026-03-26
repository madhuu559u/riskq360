import apiClient from './client';
import type { DashboardStats, DBStats, RecentActivityItem } from '../types/api';

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await apiClient.get<DashboardStats>('/dashboard/stats');
  return data;
}

export async function getDBStats(): Promise<DBStats> {
  const { data } = await apiClient.get<DBStats>('/dashboard/db-stats');
  return data;
}

export async function getProcessingMetrics(): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get<Record<string, unknown>>('/dashboard/processing-metrics');
  return data;
}

export async function getModelPerformance(): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get<Record<string, unknown>>('/dashboard/model-performance');
  return data;
}

export async function getRecentActivity(): Promise<{ recent_activity: RecentActivityItem[] }> {
  const { data } = await apiClient.get<{ recent_activity: RecentActivityItem[] }>(
    '/dashboard/recent-activity',
  );
  return data;
}
