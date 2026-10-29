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

  // Marks Records & Verification
  getExamMarksRecords: (examId: string, statusFilter?: string) => {
    const qs = statusFilter ? `?status_filter=${statusFilter}` : '';
    return request<any[]>(`/marks/${examId}${qs}`);
  },

  approveMarksRecord: (recordId: string, notes?: string) =>
    request<any>(`/marks/record/${recordId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ faculty_id: 'FAC001', approval_notes: notes }),
    }),

  updateMarksRecord: (recordId: string, scores: any[], studentId?: string, reason?: string) =>
    request<any>(`/marks/record/${recordId}`, {
      method: 'PUT',
      body: JSON.stringify({
        scores,
        student_id: studentId,
        faculty_id: 'FAC001',
        reason: reason || 'Manual correction during faculty review',
      }),
    }),

  // Export & OneDrive
  getExportPreview: (examId: string) =>
    request<{
      exam_id: string;
      subject_code: string;
      subject_name: string;
      exam_type: string;
      total_records: number;
      approved_records: number;
      pending_records: number;
      questions_count: number;
      total_marks: number;
      suggested_filename: string;
      microsoft_integration_configured: boolean;
    }>(`/export/preview/${examId}`),

  getDownloadExcelUrl: (examId: string, onlyApproved: boolean = true) =>
    `/api/v1/export/excel/${examId}?only_approved=${onlyApproved}`,

  getOneDriveAuthUrl: (state?: string) => {
    const qs = state ? `?state=${encodeURIComponent(state)}` : '';
    return request<{ configured: boolean; auth_url?: string; message?: string }>(
      `/export/onedrive/auth-url${qs}`
    );
  },

  uploadToOneDrive: (payload: {
    exam_id: string;
    access_token: string;
    only_approved?: boolean;
    folder_name?: string;
  }) =>
    request<{
      success: boolean;
      message: string;
      onedrive_result: any;
    }>('/export/onedrive/upload', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
