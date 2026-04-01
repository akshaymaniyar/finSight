import apiClient from './client';
import type { AuthResponse, DemoAuthResponse, MeResponse } from '../types';

export async function getLoginUrl(email?: string): Promise<AuthResponse> {
  const params = email ? { email } : {};
  const { data } = await apiClient.get<AuthResponse>('/api/auth/login', { params });
  return data;
}

export async function getMe(): Promise<MeResponse> {
  const { data } = await apiClient.get<MeResponse>('/api/auth/me');
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/auth/logout');
}

export async function loginDemo(): Promise<DemoAuthResponse> {
  const { data } = await apiClient.post<DemoAuthResponse>('/api/auth/demo');
  return data;
}
