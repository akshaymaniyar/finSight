import apiClient from './client';
import type { SyncStatusResponse, SyncResult, SyncHistoryResponse } from '../types';

export async function getSyncStatus(): Promise<SyncStatusResponse> {
  const { data } = await apiClient.get<SyncStatusResponse>('/api/sync/status');
  return data;
}

export async function syncMonth(month: string, force = false): Promise<SyncResult> {
  const { data } = await apiClient.post<SyncResult>('/api/sync/month', { month, force });
  return data;
}

export async function resyncMonth(month: string): Promise<SyncResult> {
  const { data } = await apiClient.post<SyncResult>('/api/sync/resync', { month });
  return data;
}

export async function getSyncHistory(): Promise<SyncHistoryResponse> {
  const { data } = await apiClient.get<SyncHistoryResponse>('/api/sync/history');
  return data;
}
