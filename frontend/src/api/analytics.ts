import apiClient from './client';
import type { CategoryBreakdown, MonthlyTrend, TopMerchant, CardComparison } from '../types';

export interface AnalyticsFilters {
  date_from?: string;
  date_to?: string;
  card_type?: string;
}

function buildParams(filters: AnalyticsFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      params.append(key, String(value));
    }
  });
  const str = params.toString();
  return str ? `?${str}` : '';
}

export async function getCategoryBreakdown(filters: AnalyticsFilters = {}): Promise<CategoryBreakdown[]> {
  const { data } = await apiClient.get<{ categories: CategoryBreakdown[] }>(`/api/analytics/by-category${buildParams(filters)}`);
  return data.categories;
}

export async function getMonthlyTrend(filters: AnalyticsFilters = {}): Promise<MonthlyTrend[]> {
  const { data } = await apiClient.get<{ months: MonthlyTrend[] }>(`/api/analytics/monthly-trend${buildParams(filters)}`);
  return data.months;
}

export async function getTopMerchants(filters: AnalyticsFilters = {}): Promise<TopMerchant[]> {
  const { data } = await apiClient.get<{ merchants: TopMerchant[] }>(`/api/analytics/top-merchants${buildParams(filters)}`);
  return data.merchants;
}

export async function getCardComparison(filters: AnalyticsFilters = {}): Promise<CardComparison> {
  const { data } = await apiClient.get<CardComparison>(`/api/analytics/card-comparison${buildParams(filters)}`);
  return data;
}
