import {
  DashboardSummary,
  Exam,
  ExamCreatePayload,
  Student,
  StudentCreatePayload,
  AuditEvent,
} from '../types';

const API_BASE = '/api/v1';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorDetail = 'An unexpected error occurred';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = `HTTP ${response.status} ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Health
  checkHealth: () => request<{ status: string; database: any }>('/health'),

  // Dashboard
  getDashboardSummary: () => request<DashboardSummary>('/dashboard/summary'),

  // Examinations
  getExams: (params?: { exam_type?: string; semester?: number; subject_code?: string }) => {
    const query = new URLSearchParams();
    if (params?.exam_type) query.append('exam_type', params.exam_type);
    if (params?.semester) query.append('semester', params.semester.toString());
    if (params?.subject_code) query.append('subject_code', params.subject_code);
    const qs = query.toString();
    return request<Exam[]>(`/exams${qs ? `?${qs}` : ''}`);
  },

  getExam: (examId: string) => request<Exam>(`/exams/${examId}`),

  createExam: (payload: ExamCreatePayload) =>
    request<Exam>('/exams', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  deleteExam: (examId: string) =>
    request<void>(`/exams/${examId}`, {
      method: 'DELETE',
    }),

  // Students
  getStudents: (params?: { search?: string; semester?: number; branch?: string }) => {
    const query = new URLSearchParams();
    if (params?.search) query.append('search', params.search);
    if (params?.semester) query.append('semester', params.semester.toString());
    if (params?.branch) query.append('branch', params.branch);
    const qs = query.toString();
    return request<Student[]>(`/students${qs ? `?${qs}` : ''}`);
  },

  createStudent: (payload: StudentCreatePayload) =>
    request<Student>('/students', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Activity
  getRecentActivities: (limit = 20) =>
    request<AuditEvent[]>(`/activity?limit=${limit}`),
};
