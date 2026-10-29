import React from 'react';
import {
  Camera,
  UploadCloud,
  AlertCircle,
  Sparkles
} from 'lucide-react';
import { Exam } from '../../types';

interface ScanMarksViewProps {
  selectedExam: Exam | null;
  exams: Exam[];
  onSelectExam: (exam: Exam) => void;
  onOpenCreateExam: () => void;
}

export const ScanMarksView: React.FC<ScanMarksViewProps> = ({
  selectedExam,
  exams,
  onSelectExam,
  onOpenCreateExam,
}) => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-3 border-b border-slate-200">
        <h2 className="text-xl font-bold text-slate-900">Scan & Digitize Marks Strip</h2>
        <p className="text-xs text-slate-500">
          Capture marks strips using browser camera or high-resolution upload for computer vision preprocessing
        </p>
      </div>

      {/* Examination Session Selector */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <label className="block text-xs font-semibold text-slate-700">
          Active Examination Session *
        </label>
        {exams.length === 0 ? (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
              <span>No examinations configured. You must configure an examination pattern before scanning.</span>
            </div>
            <button
              onClick={onOpenCreateExam}
              className="px-3 py-1 bg-amber-600 text-white rounded font-medium hover:bg-amber-700"
            >
              Configure Exam
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {exams.map((exam) => {
              const isSelected = selectedExam?.exam_id === exam.exam_id;
              return (
                <div
                  key={exam.exam_id}
                  onClick={() => onSelectExam(exam)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-blue-600 bg-blue-50/50 ring-2 ring-blue-500/20'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-slate-900">{exam.subject_code}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      exam.exam_type === 'MID_SEMESTER' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                    }`}>
                      {exam.exam_type === 'MID_SEMESTER' ? 'Mid-Sem' : 'End-Sem'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 font-medium truncate mt-1">{exam.subject_name}</p>
                  <div className="mt-2 text-[11px] text-slate-500 flex justify-between">
                    <span>{exam.questions.length} Questions</span>
                    <span className="font-semibold text-blue-600">{exam.total_marks} Marks</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Capture Canvas / Upload Card */}
      {selectedExam && (
        <div className="bg-white p-8 rounded-2xl border-2 border-dashed border-slate-300 text-center space-y-4 hover:border-blue-400 transition-colors">
          <div className="h-16 w-16 mx-auto rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Camera className="h-8 w-8" />
          </div>
          <div>
            <h3 className="font-bold text-base text-slate-800">
              Ready to Scan Marksheet for {selectedExam.subject_code} ({selectedExam.exam_type.replace('_', ' ')})
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Position the student marks strip under clear lighting. Align with the camera guide for optimal OpenCV boundary detection.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={() => alert(`Camera Scanner will activate OpenCV & OCR pipeline in Phase 4 for exam ${selectedExam.exam_id}.`)}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-sm inline-flex items-center space-x-2 transition-all"
            >
              <Camera className="h-4 w-4" />
              <span>Launch Live Camera</span>
            </button>
            <button
              onClick={() => alert(`Image upload fallback ready for Phase 4 computer vision preprocessing.`)}
              className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold inline-flex items-center space-x-2 transition-all"
            >
              <UploadCloud className="h-4 w-4" />
              <span>Upload Scanned Image</span>
            </button>
          </div>
          <div className="text-[11px] text-slate-400 pt-2 flex items-center justify-center space-x-1.5">
            <Sparkles className="h-3.5 w-3.5 text-blue-500" />
            <span>OpenCV perspective rectification & OCR extraction ready in Phase 4.</span>
          </div>
        </div>
      )}
    </div>
  );
};
