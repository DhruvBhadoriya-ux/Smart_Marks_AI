import React, { useState } from 'react';
import {
  X,
  Plus,
  Trash2,
  Check,
  AlertCircle,
  Calculator,
  ListPlus
} from 'lucide-react';
import { ExamCreatePayload, ExamType, QuestionConfig } from '../../types';

interface ExamCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: ExamCreatePayload) => Promise<void>;
}

export const ExamCreateModal: React.FC<ExamCreateModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [subjectCode, setSubjectCode] = useState('');
  const [subjectName, setSubjectName] = useState('');
  const [examType, setExamType] = useState<ExamType>('MID_SEMESTER');
  const [semester, setSemester] = useState<number>(3);
  const [academicYear, setAcademicYear] = useState('2025-2026');
  const [examDate, setExamDate] = useState(new Date().toISOString().split('T')[0]);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Default question template
  const [questions, setQuestions] = useState<QuestionConfig[]>([
    { question_id: 'Q1a', display_name: 'Q1(a)', max_marks: 5, parent_question: 'Q1' },
    { question_id: 'Q1b', display_name: 'Q1(b)', max_marks: 5, parent_question: 'Q1' },
    { question_id: 'Q2', display_name: 'Q2', max_marks: 10, parent_question: null },
    { question_id: 'Q3', display_name: 'Q3', max_marks: 10, parent_question: null },
  ]);

  if (!isOpen) return null;

  const totalCalculatedMarks = questions.reduce(
    (sum, q) => sum + (Number(q.max_marks) || 0),
    0
  );

  const handleAddQuestion = () => {
    const nextIndex = questions.length + 1;
    const newQId = `Q${nextIndex}`;
    setQuestions([
      ...questions,
      {
        question_id: newQId,
        display_name: newQId,
        max_marks: 10,
        parent_question: null,
      },
    ]);
  };

  const handleAddSubquestion = (parentQ: string) => {
    // Count existing subquestions for this parent
    const existingSubs = questions.filter((q) => q.parent_question === parentQ);
    const subLetter = String.fromCharCode(97 + existingSubs.length); // 'a', 'b', 'c'...
    const newQId = `${parentQ}${subLetter}`;
    const newDisplayName = `${parentQ}(${subLetter})`;

    setQuestions([
      ...questions,
      {
        question_id: newQId,
        display_name: newDisplayName,
        max_marks: 5,
        parent_question: parentQ,
      },
    ]);
  };

  const handleRemoveQuestion = (index: number) => {
    if (questions.length <= 1) {
      setFormError('An examination must have at least one question.');
      return;
    }
    setQuestions(questions.filter((_, i) => i !== index));
  };

  const handleUpdateQuestion = (index: number, key: keyof QuestionConfig, val: any) => {
    const updated = [...questions];
    updated[index] = { ...updated[index], [key]: val };
    setQuestions(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!subjectCode.trim() || !subjectName.trim()) {
      setFormError('Please enter subject code and subject name.');
      return;
    }

    if (questions.length === 0) {
      setFormError('Please add at least one question to the pattern.');
      return;
    }

    // Check unique question_ids
    const ids = questions.map((q) => q.question_id.trim().toLowerCase());
    if (new Set(ids).size !== ids.length) {
      setFormError('Each question identifier must be unique.');
      return;
    }

    try {
      setSubmitting(true);
      await onSubmit({
        subject_code: subjectCode.trim().toUpperCase(),
        subject_name: subjectName.trim(),
        exam_type: examType,
        semester: Number(semester),
        academic_year: academicYear,
        exam_date: examDate,
        questions: questions.map((q) => ({
          ...q,
          max_marks: Number(q.max_marks),
        })),
      });
      onClose();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create examination session.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden border border-slate-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Configure Examination Session</h2>
            <p className="text-xs text-slate-500">
              Define subject parameters and question marking pattern
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-xs text-red-700">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <span>{formError}</span>
            </div>
          )}

          {/* Row 1: Subject Code & Name */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Subject Code *
              </label>
              <input
                type="text"
                placeholder="e.g. CS301"
                value={subjectCode}
                onChange={(e) => setSubjectCode(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm uppercase focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                required
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Subject Name *
              </label>
              <input
                type="text"
                placeholder="e.g. Data Structures and Algorithms"
                value={subjectName}
                onChange={(e) => setSubjectName(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                required
              />
            </div>
          </div>

          {/* Row 2: Exam Type, Semester, Academic Year, Date */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Exam Type
              </label>
              <select
                value={examType}
                onChange={(e) => setExamType(e.target.value as ExamType)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                <option value="MID_SEMESTER">Mid-Sem</option>
                <option value="END_SEMESTER">End-Sem</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Semester
              </label>
              <select
                value={semester}
                onChange={(e) => setSemester(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                  <option key={s} value={s}>
                    Semester {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Academic Year
              </label>
              <input
                type="text"
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                placeholder="2025-2026"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Date
              </label>
              <input
                type="date"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                required
              />
            </div>
          </div>

          {/* Row 3: Question Marking Pattern Configuration */}
          <div className="pt-2 border-t border-slate-200">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-800">
                  Question Pattern & Maximum Marks
                </h3>
                <p className="text-[11px] text-slate-500">
                  Configure question IDs, subquestions (e.g. Q1(a)), and maximum marks
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handleAddQuestion}
                  className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md text-xs font-semibold inline-flex items-center space-x-1"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Question</span>
                </button>
              </div>
            </div>

            {/* Questions Table / List */}
            <div className="max-h-60 overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100 bg-slate-50/50">
              {questions.map((q, idx) => (
                <div key={idx} className="p-2.5 flex items-center space-x-2 text-xs">
                  <div className="w-20">
                    <input
                      type="text"
                      title="Internal Question ID"
                      value={q.question_id}
                      onChange={(e) =>
                        handleUpdateQuestion(idx, 'question_id', e.target.value)
                      }
                      className="w-full px-2 py-1 border border-slate-300 rounded text-xs uppercase font-mono font-semibold"
                      placeholder="Q1"
                    />
                  </div>
                  <div className="flex-1">
                    <input
                      type="text"
                      title="Display Label"
                      value={q.display_name}
                      onChange={(e) =>
                        handleUpdateQuestion(idx, 'display_name', e.target.value)
                      }
                      className="w-full px-2 py-1 border border-slate-300 rounded text-xs font-medium"
                      placeholder="Display Label"
                    />
                  </div>
                  <div className="w-24 flex items-center space-x-1">
                    <input
                      type="number"
                      step="0.5"
                      min="0.5"
                      title="Max Marks"
                      value={q.max_marks}
                      onChange={(e) =>
                        handleUpdateQuestion(idx, 'max_marks', parseFloat(e.target.value) || 0)
                      }
                      className="w-16 px-2 py-1 border border-slate-300 rounded text-xs text-right font-semibold"
                    />
                    <span className="text-slate-400 text-[10px]">pts</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      type="button"
                      onClick={() => handleAddSubquestion(q.parent_question || q.question_id)}
                      title="Add subquestion"
                      className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                    >
                      <ListPlus className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRemoveQuestion(idx)}
                      title="Remove question"
                      className="p-1 text-red-500 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Pattern Summary Footer */}
            <div className="mt-3 p-3 bg-blue-50 border border-blue-100 rounded-lg flex items-center justify-between text-xs text-blue-900">
              <div className="flex items-center space-x-2">
                <Calculator className="h-4 w-4 text-blue-600" />
                <span className="font-semibold">Calculated Total Examination Marks:</span>
              </div>
              <span className="text-base font-bold text-blue-700">
                {totalCalculatedMarks} Marks
              </span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-sm transition-all inline-flex items-center space-x-2"
            >
              {submitting ? (
                <span>Saving to MongoDB...</span>
              ) : (
                <>
                  <Check className="h-4 w-4" />
                  <span>Save Examination Session</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
