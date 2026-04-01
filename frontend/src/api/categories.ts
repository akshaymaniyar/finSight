import apiClient from './client';

export interface Subcategory {
  id: number;
  name: string;
  keywords: string | null;
}

export interface Category {
  id: number;
  name: string;
  icon: string | null;
  color: string | null;
  is_income: boolean;
  is_system: boolean;
  sort_order: number;
  subcategories: Subcategory[];
}

export interface CategoryListResponse {
  categories: Category[];
}

export async function getCategories(): Promise<Category[]> {
  const { data } = await apiClient.get<CategoryListResponse>('/api/categories');
  return data.categories;
}

export async function createCategory(payload: {
  name: string;
  icon?: string;
  color?: string;
  is_income?: boolean;
  parent_id?: number;
}): Promise<Category> {
  const { data } = await apiClient.post<Category>('/api/categories', payload);
  return data;
}

export async function updateCategory(
  id: number,
  payload: { name?: string; icon?: string; color?: string; keywords?: string }
): Promise<Category> {
  const { data } = await apiClient.put<Category>(`/api/categories/${id}`, payload);
  return data;
}

export async function deleteCategory(id: number): Promise<void> {
  await apiClient.delete(`/api/categories/${id}`);
}
