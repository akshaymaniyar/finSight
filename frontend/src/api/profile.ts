import apiClient from './client';

export interface ProfileData {
  first_name: string | null;
  last_name: string | null;
  dob: string | null;
  pan_first5: string | null;
  mobile_last5: string | null;
  customer_ids: Record<string, string> | null;
  profile_completed: boolean;
}

export interface ProfileUpdateData {
  first_name?: string;
  last_name?: string;
  dob?: string;
  pan_first5?: string;
  mobile_last5?: string;
  customer_ids?: Record<string, string>;
}

export async function getProfile(): Promise<ProfileData> {
  const { data } = await apiClient.get<ProfileData>('/api/profile');
  return data;
}

export async function updateProfile(payload: ProfileUpdateData): Promise<ProfileData> {
  const { data } = await apiClient.put<ProfileData>('/api/profile', payload);
  return data;
}
