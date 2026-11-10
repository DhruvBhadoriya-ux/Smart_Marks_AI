export type ExamType = 'MID_SEMESTER' | 'END_SEMESTER';

export interface QuestionConfig {
  question_id: string;
  display_name: string;
  max_marks: number;
  parent_question?: string | null;
}

export interface Exam {
  exam_id: string;
  title: string;
  subject_code: string;
  subject_name: string;
  exam_type: ExamType;
  semester: number;
  academic_year: string;
  exam_date: string;
  total_marks: number;
  created_by?: string;
  questions: QuestionConfig[];
  created_at: string;
  updated_at: string;
  marks_count?: number;
}

export interface ExamCreatePayload {
  title?: string;
  subject_code: string;
  subject_name: string;
  exam_type: ExamType;
  semester: number;
  academic_year: string;
  exam_date: string;
  questions: QuestionConfig[];
}

export interface Student {
  student_id: string;
  name: string;
  semester: number;
  branch: string;
  email?: string | null;
  created_at?: string;
}

export interface StudentCreatePayload {
  student_id: string;
  name: string;
  semester: number;
  branch: string;
  email?: string;
}

export type VerificationStatus = 'PENDING_REVIEW' | 'NEEDS_CORRECTION' | 'APPROVED';

export interface QuestionScore {
  question_id: string;
  display_name: string;
  obtained_marks: number | null;
  max_marks: number;
  confidence: number;
  is_flagged: boolean;
  is_unrecognized?: boolean;
  is_manually_edited: boolean;
  flag_reason?: string | null;
  cell_box?: number[] | null;
}

export interface EditHistoryEntry {
  field: string;
  old_value: any;
  new_value: any;
  edited_by: string;
  timestamp: string;
  reason?: string | null;
}

export interface MarksRecord {
  record_id: string;
  exam_id: string;
  student_id: string;
  student_name?: string;
  scores: QuestionScore[];
  total_obtained: number | null;
  total_max: number;
  percentage: number | null;
  status: VerificationStatus;
  scan_image_path?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  edit_history: EditHistoryEntry[];
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  event_id?: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  description: string;
  user_id: string;
  timestamp: string;
  metadata?: Record<string, any> | null;
}

export interface DashboardSummary {
  total_exams: number;
  total_students: number;
  total_records_processed: number;
  total_approved_records: number;
  pending_verification_records: number;
  recent_exams: Exam[];
  recent_activities: AuditEvent[];
}
