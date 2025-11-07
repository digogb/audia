/**
 * Cliente API com suporte a autenticação JWT e refresh automático de tokens
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1';

// Criar instância do axios
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 segundos
});

// Interceptor de request - adiciona token de autenticação
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor de response - trata refresh de token
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Se erro 401 e não é tentativa de retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Tentar refresh do token
        if (typeof window === 'undefined') {
          throw new Error('Not in browser');
        }

        const refreshToken = localStorage.getItem('refresh_token');

        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await axios.post(`${API_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: new_refresh_token } = response.data;

        // Salvar novos tokens
        localStorage.setItem('access_token', access_token);
        if (new_refresh_token) {
          localStorage.setItem('refresh_token', new_refresh_token);
        }

        // Atualizar header da requisição original
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        // Repetir requisição original
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Falha no refresh - deslogar usuário
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// ============================================================================
// API Methods
// ============================================================================

export const api = {
  // Expor o apiClient para uso direto quando necessário
  apiClient,

  // Auth
  auth: {
    register: (data: { email: string; username: string; password: string }) =>
      apiClient.post('/auth/register', data),

    login: (data: { email: string; password: string }) =>
      apiClient.post('/auth/login', data),

    me: () => apiClient.get('/auth/me'),
  },

  // Upload
  upload: {
    file: (file: File, onProgress?: (progress: number) => void) => {
      const formData = new FormData();
      formData.append('file', file);

      return apiClient.post('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        },
      });
    },
  },

  // Jobs
  jobs: {
    getStatus: (jobId: string) => apiClient.get(`/jobs/${jobId}/status`),
  },

  // Transcriptions
  transcriptions: {
    get: (jobId: string) => apiClient.get(`/transcriptions/${jobId}`),

    list: (params?: { page?: number; page_size?: number; status_filter?: string }) =>
      apiClient.get('/transcriptions/', { params }),

    download: (jobId: string, format: 'txt' | 'json' = 'txt') =>
      apiClient.get(`/transcriptions/${jobId}/download`, {
        params: { format },
        responseType: 'blob',
      }),

    updateSpeakers: (jobId: string, speakerNames: Record<string, string>) =>
      apiClient.put(`/transcriptions/${jobId}/speakers`, { speaker_names: speakerNames }),

    updateText: (jobId: string, editedText: string) =>
      apiClient.put(`/transcriptions/${jobId}/edit`, { edited_text: editedText }),
  },

  // Chat
  chat: {
    send: (jobId: string, data: { question: string; chat_history?: any[] }) =>
      apiClient.post(`/chat/${jobId}`, data),
  },

  // Summary
  summary: {
    get: (jobId: string) => apiClient.get(`/summary/${jobId}`),

    generate: (jobId: string, params?: { max_tokens?: number; temperature?: number }) =>
      apiClient.post(`/summary/${jobId}`, params),

    delete: (jobId: string) => apiClient.delete(`/summary/${jobId}`),
  },

  // Meeting Minutes
  meetingMinutes: {
    get: (jobId: string) => apiClient.get(`/meeting-minutes/${jobId}`),

    generate: (jobId: string, params?: { max_tokens?: number; temperature?: number }) =>
      apiClient.post(`/meeting-minutes/${jobId}`, params),

    delete: (jobId: string) => apiClient.delete(`/meeting-minutes/${jobId}`),
  },
};

export default api;
