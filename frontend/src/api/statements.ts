import apiClient from './client';
import type { StatementsResponse, Statement } from '../types';

export interface StatementFilters {
  bank_name?: string;
  month?: string;
  parse_status?: string;
  limit?: number;
  offset?: number;
}

export async function getStatements(filters: StatementFilters = {}): Promise<StatementsResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      params.append(key, String(value));
    }
  });
  const { data } = await apiClient.get<StatementsResponse>(`/api/statements?${params.toString()}`);
  return data;
}

export async function getStatement(id: number): Promise<Statement> {
  const { data } = await apiClient.get<Statement>(`/api/statements/${id}`);
  return data;
}
