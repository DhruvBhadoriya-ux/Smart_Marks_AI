import React, { useState, useEffect, useCallback } from 'react';
import { Navigation, TabType } from './components/layout/Navigation';
import { DashboardOverview } from './components/dashboard/DashboardOverview';
import { ExamManagement } from './components/exams/ExamManagement';
import { ExamCreateModal } from './components/exams/ExamCreateModal';
import { StudentManagement } from './components/students/StudentManagement';
import { RecentActivityPanel } from './components/activity/RecentActivityPanel';
import { ScanMarksView } from './components/camera/ScanMarksView';
import { api } from './services/api';
import {
  DashboardSummary,
  Exam,
  ExamCreatePayload,
  Student,
  StudentCreatePayload,
  AuditEvent,
} from './types';
import { CheckCircle2, AlertCircle, X } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Data States
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [activities, setActivities] = useState<AuditEvent[]>([]);
  const [selectedExam, setSelectedExam] = useState<Exam | null>(null);

  // UI States
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const loadAllData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [summaryData, examsData, studentsData, activitiesData] = await Promise.all([
        api.getDashboardSummary(),
        api.getExams(),
        api.getStudents(),
        api.getRecentActivities(),
      ]);

      setSummary(summaryData);
      setExams(examsData);
      setStudents(studentsData);
      setActivities(activitiesData);

      // If selected exam is not set or was deleted, default to first available
      if (examsData.length > 0 && !selectedExam) {
        setSelectedExam(examsData[0]);
      }
    } catch (err: any) {
      console.error('Error fetching data from FastAPI:', err);
      setError(err.message || 'Failed to connect to backend.');
    } finally {
      setLoading(false);
    }
  }, [selectedExam]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Handle Exam Creation
  const handleCreateExam = async (payload: ExamCreatePayload) => {
    const created = await api.createExam(payload);
    showToast(`Examination session "${created.subject_code}" configured successfully!`);
    await loadAllData();
    setSelectedExam(created);
  };

  // Handle Exam Deletion
  const handleDeleteExam = async (examId: string) => {
    try {
      await api.deleteExam(examId);
      showToast('Examination deleted successfully.');
      if (selectedExam?.exam_id === examId) {
        setSelectedExam(null);
      }
      await loadAllData();
    } catch (err: any) {
      showToast(err.message || 'Failed to delete exam', 'error');
    }
  };

  // Handle Student Enrollment
  const handleCreateStudent = async (payload: StudentCreatePayload) => {
    const student = await api.createStudent(payload);
    showToast(`Student ${student.name} (${student.student_id}) enrolled successfully!`);
    await loadAllData();
  };

  const handleSelectExamForScan = (exam: Exam) => {
    setSelectedExam(exam);
    setActiveTab('scan');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col lg:flex-row">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed top-5 right-5 z-50 flex items-center space-x-2.5 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium transition-all bg-white animate-in slide-in-from-top-3">
          {toast.type === 'success' ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
          )}
          <span className="text-slate-800">{toast.message}</span>
          <button
            onClick={() => setToast(null)}
            className="p-1 text-slate-400 hover:text-slate-600 rounded"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Navigation (Sidebar & Mobile Drawer) */}
      <Navigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
        mobileMenuOpen={mobileMenuOpen}
        setMobileMenuOpen={setMobileMenuOpen}
      />

      {/* Main Content Area */}
      <main className="flex-1 lg:ml-64 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full transition-all">
        {activeTab === 'dashboard' && (
          <DashboardOverview
            summary={summary}
            loading={loading}
            error={error}
            onRefresh={loadAllData}
            onNavigate={setActiveTab}
            onOpenCreateExam={() => setIsCreateModalOpen(true)}
          />
        )}

        {activeTab === 'exams' && (
          <ExamManagement
            exams={exams}
            loading={loading}
            onRefresh={loadAllData}
            onOpenCreate={() => setIsCreateModalOpen(true)}
            onDeleteExam={handleDeleteExam}
            onSelectExamForScan={handleSelectExamForScan}
          />
        )}

        {activeTab === 'scan' && (
          <ScanMarksView
            selectedExam={selectedExam}
            exams={exams}
            onSelectExam={setSelectedExam}
            onOpenCreateExam={() => setIsCreateModalOpen(true)}
          />
        )}

        {activeTab === 'students' && (
          <StudentManagement
            students={students}
            loading={loading}
            onRefresh={loadAllData}
            onCreateStudent={handleCreateStudent}
          />
        )}

        {activeTab === 'activity' && (
          <RecentActivityPanel
            activities={activities}
            loading={loading}
            onRefresh={loadAllData}
          />
        )}
      </main>

      {/* Exam Creation Modal */}
      <ExamCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateExam}
      />
    </div>
  );
};

export default App;
