import React from 'react';
import {
  FileSpreadsheet,
  Users,
  CheckCircle2,
  Clock,
  PlusCircle,
  Camera,
  ArrowUpRight,
  AlertTriangle,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import { DashboardSummary } from '../../types';
import { TabType } from '../layout/Navigation';

interface DashboardOverviewProps {
  summary: DashboardSummary | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  onNavigate: (tab: TabType) => void;
  onOpenCreateExam: () => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  summary,
  loading,
  error,
  onRefresh,
  onNavigate,
  onOpenCreateExam,
}) => {
  if (loading && !summary) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-500">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-600 mb-3" />
        <p className="text-sm font-medium">Fetching examination dashboard data from MongoDB...</p>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-800 my-6">
        <div className="flex items-center space-x-3 mb-2">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <h3 className="font-semibold text-base">Failed to connect to backend service</h3>
        </div>
        <p className="text-sm text-red-700 mb-4">{error}</p>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-medium rounded-lg inline-flex items-center space-x-1.5 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Retry Connection</span>
        </button>
      </div>
    );
  }

  const stats = [
    {
      label: 'Configured Exams',
      value: summary?.total_exams ?? 0,
      icon: FileSpreadsheet,
      color: 'blue',
      change: 'Active in system',
    },
    {
      label: 'Enrolled Students',
      value: summary?.total_students ?? 0,
      icon: Users,
      color: 'indigo',
      change: 'Across all semesters',
    },
    {
      label: 'Approved Records',
      value: summary?.total_approved_records ?? 0,
      icon: CheckCircle2,
      color: 'emerald',
      change: 'Faculty signed-off',
    },
    {
      label: 'Pending Verification',
      value: summary?.pending_verification_records ?? 0,
      icon: Clock,
      color: 'amber',
      change: 'Requires review',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner / Actions */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Faculty Examination Dashboard</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Academic Session 2025–2026 • Examination Marks Digitization & Pattern Verification
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={onRefresh}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
            title="Refresh Data"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onOpenCreateExam}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium shadow-sm hover:shadow transition-all inline-flex items-center space-x-2"
          >
            <PlusCircle className="h-4 w-4" />
            <span>New Examination</span>
          </button>
          <button
            onClick={() => onNavigate('scan')}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium shadow-sm hover:shadow transition-all inline-flex items-center space-x-2"
          >
            <Camera className="h-4 w-4 text-blue-400" />
            <span>Scan Marks Strip</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm hover:border-slate-300 transition-all"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {stat.label}
                </span>
                <div
                  className={`h-9 w-9 rounded-lg flex items-center justify-center ${
                    stat.color === 'blue'
                      ? 'bg-blue-50 text-blue-600'
                      : stat.color === 'indigo'
                      ? 'bg-indigo-50 text-indigo-600'
                      : stat.color === 'emerald'
                      ? 'bg-emerald-50 text-emerald-600'
                      : 'bg-amber-50 text-amber-600'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-3 flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-slate-900">{stat.value}</span>
                <span className="text-xs text-slate-500">{stat.change}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Grid: Recent Exams + Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Recent Examination Sessions */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div className="flex items-center space-x-2">
              <FileSpreadsheet className="h-4 w-4 text-blue-600" />
              <h3 className="font-semibold text-sm text-slate-800">Recent Examination Sessions</h3>
            </div>
            <button
              onClick={() => onNavigate('exams')}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium inline-flex items-center space-x-1"
            >
              <span>View All</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-100 flex-1">
            {!summary?.recent_exams || summary.recent_exams.length === 0 ? (
              <div className="py-12 text-center text-slate-400">
                <FileSpreadsheet className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                <p className="text-sm">No examinations configured yet.</p>
                <button
                  onClick={onOpenCreateExam}
                  className="mt-3 text-xs text-blue-600 hover:underline font-medium"
                >
                  Create your first exam configuration
                </button>
              </div>
            ) : (
              summary.recent_exams.map((exam) => (
                <div
                  key={exam.exam_id}
                  className="p-4 hover:bg-slate-50/80 transition-colors flex items-center justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-sm text-slate-900">
                        {exam.subject_code}
                      </span>
                      <span className="text-xs text-slate-500">•</span>
                      <span className="text-sm text-slate-700 font-medium">{exam.subject_name}</span>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          exam.exam_type === 'MID_SEMESTER'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-purple-100 text-purple-700'
                        }`}
                      >
                        {exam.exam_type === 'MID_SEMESTER' ? 'Mid-Sem' : 'End-Sem'}
                      </span>
                    </div>
                    <div className="flex items-center space-x-3 text-xs text-slate-500">
                      <span>Semester {exam.semester}</span>
                      <span>•</span>
                      <span>{exam.questions.length} Questions configured</span>
                      <span>•</span>
                      <span>Total: {exam.total_marks} Marks</span>
                    </div>
                  </div>
                  <div className="text-right flex flex-col items-end">
                    <span className="text-xs font-semibold text-slate-700">
                      {exam.marks_count ?? 0} Scans Processed
                    </span>
                    <button
                      onClick={() => onNavigate('scan')}
                      className="mt-1.5 text-xs text-blue-600 hover:text-blue-800 font-medium inline-flex items-center space-x-1"
                    >
                      <span>Scan Marksheet</span>
                      <ArrowUpRight className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Live Audit Activity */}
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div className="flex items-center space-x-2">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <h3 className="font-semibold text-sm text-slate-800">Recent Audit Activity</h3>
            </div>
            <button
              onClick={() => onNavigate('activity')}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              All Logs
            </button>
          </div>

          <div className="p-4 flex-1 space-y-3.5 overflow-y-auto max-h-[380px]">
            {!summary?.recent_activities || summary.recent_activities.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-8">No recent events recorded.</p>
            ) : (
              summary.recent_activities.map((act, idx) => (
                <div key={act.event_id || idx} className="flex items-start space-x-3 text-xs">
                  <div className="mt-1 h-2 w-2 rounded-full bg-blue-500 ring-4 ring-blue-50 shrink-0" />
                  <div className="flex-1 space-y-0.5">
                    <p className="text-slate-800 font-medium leading-relaxed">{act.description}</p>
                    <div className="flex items-center space-x-2 text-[10px] text-slate-400">
                      <span>{act.user_id}</span>
                      <span>•</span>
                      <span>{new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
