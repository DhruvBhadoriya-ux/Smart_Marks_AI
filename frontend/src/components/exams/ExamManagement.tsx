import React, { useState } from 'react';
import {
  FileSpreadsheet,
  Plus,
  Search,
  Trash2,
  Calendar,
  Layers,
  ChevronDown,
  ChevronUp,
  Camera,
  RefreshCw
} from 'lucide-react';
import { Exam } from '../../types';

interface ExamManagementProps {
  exams: Exam[];
  loading: boolean;
  onRefresh: () => void;
  onOpenCreate: () => void;
  onDeleteExam: (examId: string) => Promise<void>;
  onSelectExamForScan: (exam: Exam) => void;
}

export const ExamManagement: React.FC<ExamManagementProps> = ({
  exams,
  loading,
  onRefresh,
  onOpenCreate,
  onDeleteExam,
  onSelectExamForScan,
}) => {
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [selectedSem, setSelectedSem] = useState<string>('ALL');
  const [expandedExamId, setExpandedExamId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filteredExams = exams.filter((exam) => {
    const matchesSearch =
      exam.subject_code.toLowerCase().includes(search.toLowerCase()) ||
      exam.subject_name.toLowerCase().includes(search.toLowerCase()) ||
      exam.title.toLowerCase().includes(search.toLowerCase());

    const matchesType =
      selectedType === 'ALL' || exam.exam_type === selectedType;

    const matchesSem =
      selectedSem === 'ALL' || exam.semester.toString() === selectedSem;

    return matchesSearch && matchesType && matchesSem;
  });

  const handleDelete = async (examId: string, title: string) => {
    if (window.confirm(`Are you sure you want to delete examination "${title}"? This will also remove any related marks records.`)) {
      try {
        setDeletingId(examId);
        await onDeleteExam(examId);
      } finally {
        setDeletingId(null);
      }
    }
  };

  return (
    <div className="space-y-5">
      {/* Header & Main Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Examination Configurations</h2>
          <p className="text-xs text-slate-500">
            Manage course examination sessions, question structures, and marking bounds
          </p>
        </div>
        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <button
            onClick={onRefresh}
            className="p-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg transition-colors"
            title="Refresh Examinations"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onOpenCreate}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-sm inline-flex items-center space-x-2 transition-all"
          >
            <Plus className="h-4 w-4" />
            <span>New Examination</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 flex flex-col md:flex-row gap-3 items-center justify-between shadow-sm">
        <div className="relative w-full md:w-80">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by subject code or title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg text-xs font-medium">
            {['ALL', 'MID_SEMESTER', 'END_SEMESTER'].map((type) => (
              <button
                key={type}
                onClick={() => setSelectedType(type)}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  selectedType === type
                    ? 'bg-white text-slate-900 shadow-xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {type === 'ALL' ? 'All Types' : type === 'MID_SEMESTER' ? 'Mid-Sem' : 'End-Sem'}
              </button>
            ))}
          </div>

          <select
            value={selectedSem}
            onChange={(e) => setSelectedSem(e.target.value)}
            className="px-2.5 py-1.5 border border-slate-200 rounded-lg text-xs bg-white text-slate-700 outline-none"
          >
            <option value="ALL">All Semesters</option>
            {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
              <option key={s} value={s.toString()}>
                Sem {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Examinations List */}
      <div className="space-y-3">
        {loading && exams.length === 0 ? (
          <div className="p-12 text-center text-slate-400 bg-white rounded-xl border border-slate-200">
            <p className="text-sm">Loading examination configurations from MongoDB...</p>
          </div>
        ) : filteredExams.length === 0 ? (
          <div className="p-12 text-center text-slate-400 bg-white rounded-xl border border-slate-200">
            <FileSpreadsheet className="h-8 w-8 mx-auto mb-2 text-slate-300" />
            <p className="text-sm font-medium">No examinations match your criteria.</p>
            <button
              onClick={onOpenCreate}
              className="mt-3 text-xs text-blue-600 hover:underline font-semibold"
            >
              Configure a new examination
            </button>
          </div>
        ) : (
          filteredExams.map((exam) => {
            const isExpanded = expandedExamId === exam.exam_id;
            return (
              <div
                key={exam.exam_id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition-all hover:border-slate-300"
              >
                <div className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-base text-slate-900">{exam.subject_code}</span>
                      <span className="text-slate-400">•</span>
                      <span className="font-semibold text-sm text-slate-700">{exam.subject_name}</span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          exam.exam_type === 'MID_SEMESTER'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-purple-100 text-purple-700'
                        }`}
                      >
                        {exam.exam_type === 'MID_SEMESTER' ? 'Mid-Semester' : 'End-Semester'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-3 text-xs text-slate-500">
                      <span className="flex items-center space-x-1">
                        <Layers className="h-3.5 w-3.5 text-slate-400" />
                        <span>Semester {exam.semester} ({exam.academic_year})</span>
                      </span>
                      <span>•</span>
                      <span className="flex items-center space-x-1">
                        <Calendar className="h-3.5 w-3.5 text-slate-400" />
                        <span>Date: {exam.exam_date}</span>
                      </span>
                      <span>•</span>
                      <span className="font-semibold text-blue-600">
                        {exam.total_marks} Total Marks
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 self-end md:self-auto">
                    <button
                      onClick={() => onSelectExamForScan(exam)}
                      className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-xs font-semibold inline-flex items-center space-x-1.5 transition-colors"
                    >
                      <Camera className="h-3.5 w-3.5" />
                      <span>Scan Marksheet</span>
                    </button>

                    <button
                      onClick={() => setExpandedExamId(isExpanded ? null : exam.exam_id)}
                      className="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 rounded-lg text-xs text-slate-600 inline-flex items-center space-x-1"
                    >
                      <span>{exam.questions.length} Questions</span>
                      {isExpanded ? (
                        <ChevronUp className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5" />
                      )}
                    </button>

                    <button
                      onClick={() => handleDelete(exam.exam_id, exam.title)}
                      disabled={deletingId === exam.exam_id}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete Examination"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Expanded Question Pattern Viewer */}
                {isExpanded && (
                  <div className="bg-slate-50/80 px-5 py-3 border-t border-slate-100">
                    <div className="text-xs font-bold text-slate-700 mb-2">
                      Configured Question Schema & Mark Limits:
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
                      {exam.questions.map((q) => (
                        <div
                          key={q.question_id}
                          className="bg-white border border-slate-200 rounded-lg p-2 text-center shadow-xs"
                        >
                          <div className="font-bold text-xs text-slate-800">
                            {q.display_name}
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono">
                            {q.question_id}
                          </div>
                          <div className="text-xs font-semibold text-blue-600 mt-1">
                            {q.max_marks} pts
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
