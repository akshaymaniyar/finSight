import apiClient from './client';
import type { CategoryBreakdown, MonthlyTrend, TopMerchant, CardComparison } from '../types';

export interface AnalyticsFilters {
  date_from?: string;
  date_to?: string;
  card_type?: string;
}

export async function getCategoryBreakdown(filters: AnalyticsFilters = {}): Promise<CategoryBreakdown[]> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      params.append(key, String(value));
    }
  });
  const { data } = await apiClient.get<{ categories: CategoryBreakdown[] }>(`/api/analytics/by-category?${params.toString()}`);
  return data.categories;
}

export async function getMonthlyTrend(): Promise<MonthlyTrend[]> {
  const { data } = await apiClient.get<{ months: MonthlyTrend[] }>('/api/analytics/monthly-trend');
  return data.months;
}

export async function getTopMerchants(): Promise<TopMerchant[]> {
  const { data } = await apiClient.get<{ merchants: TopMerchant[] }>('/api/analytics/top-merchants');
  return data.merchants;
}

export async function getCardComparison(): Promise<CardComparison> {
  const { data } = await apiClient.get<CardComparison>('/api/analytics/card-comparison');
  return data;
}
