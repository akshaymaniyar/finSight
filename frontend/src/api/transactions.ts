import apiClient from './client';
import type { TransactionsResponse, TransactionSummary } from '../types';

export interface TransactionFilters {
  category?: string;
  transaction_type?: string;
  bank_name?: string;
  card_type?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  exclude_self_transfers?: boolean;
  exclude_investments?: boolean;
  limit?: number;
  offset?: number;
}

export async function getTransactions(filters: TransactionFilters = {}): Promise<TransactionsResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      params.append(key, String(value));
    }
  });
  const { data } = await apiClient.get<TransactionsResponse>(`/api/transactions?${params.toString()}`);
  return data;
}

export async function getTransactionSummary(): Promise<TransactionSummary> {
  const { data } = await apiClient.get<TransactionSummary>('/api/transactions/summary');
  return data;
}

export async function updateTransaction(
  id: number,
  updates: { category?: string; sub_category?: string; is_excluded?: boolean }
): Promise<void> {
  await apiClient.put(`/api/transactions/${id}`, updates);
}
