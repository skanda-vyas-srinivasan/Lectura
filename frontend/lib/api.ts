/**
 * API client for communicating with the backend
 */
import axios from 'axios';
import type {
  LectureSession,
  GlobalContextPlan,
  NarrationSegment,
  UploadResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  /**
   * Upload a lecture file
   */
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<UploadResponse>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Get session status and details
   */
  async getSession(sessionId: string): Promise<LectureSession> {
    const response = await apiClient.get<LectureSession>(`/session/${sessionId}`);
    return response.data;
  },

  /**
   * Get the global context plan for a lecture
   */
  async getGlobalPlan(sessionId: string): Promise<GlobalContextPlan> {
    const response = await apiClient.get<GlobalContextPlan>(
      `/session/${sessionId}/global-plan`
    );
    return response.data;
  },

  /**
   * Get narration for a specific slide
   */
  async getNarration(
    sessionId: string,
    slideIndex: number
  ): Promise<NarrationSegment> {
    const response = await apiClient.get<NarrationSegment>(
      `/narration/${sessionId}/${slideIndex}`
    );
    return response.data;
  },

  /**
   * Get all narrations for a lecture
   */
  async getAllNarrations(
    sessionId: string
  ): Promise<{ narrations: NarrationSegment[] }> {
    const response = await apiClient.get<{ narrations: NarrationSegment[] }>(
      `/session/${sessionId}/narrations`
    );
    return response.data;
  },

  /**
   * Regenerate narration for a specific slide with optional context
   */
  async regenerateNarration(
    sessionId: string,
    slideIndex: number,
    auxiliaryContext?: string
  ): Promise<NarrationSegment> {
    const response = await apiClient.post<NarrationSegment>(
      `/session/${sessionId}/regenerate/${slideIndex}`,
      { auxiliary_context: auxiliaryContext }
    );
    return response.data;
  },

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<{ success: boolean }> {
    const response = await apiClient.delete<{ success: boolean }>(
      `/session/${sessionId}`
    );
    return response.data;
  },

  /**
   * Subscribe to real-time progress updates via Server-Sent Events
   */
  subscribeToProgress(
    sessionId: string,
    onUpdate: (data: any) => void,
    onError?: (error: Event) => void
  ): EventSource {
    const eventSource = new EventSource(`${API_BASE}/stream/${sessionId}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onUpdate(data);
      } catch (error) {
        console.error('Failed to parse SSE data:', error);
      }
    };

    if (onError) {
      eventSource.onerror = onError;
    }

    return eventSource;
  },
};
