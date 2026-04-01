import apiClient from './client';
import type { ChatResponse, ChatHistoryResponse } from '../types';

export async function sendMessage(message: string, sessionId?: string): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>('/api/chat', {
    message,
    session_id: sessionId,
  });
  return data;
}

export async function getChatHistory(
  sessionId?: string,
  limit = 50,
  offset = 0
): Promise<ChatHistoryResponse> {
  const params = new URLSearchParams();
  if (sessionId) params.append('session_id', sessionId);
  params.append('limit', String(limit));
  params.append('offset', String(offset));
  const { data } = await apiClient.get<ChatHistoryResponse>(`/api/chat/history?${params.toString()}`);
  return data;
}
