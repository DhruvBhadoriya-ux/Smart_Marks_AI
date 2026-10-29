import React from 'react';
import {
  Activity,
  User,
  Tag,
  RefreshCw,
  Clock
} from 'lucide-react';
import { AuditEvent } from '../../types';

interface RecentActivityPanelProps {
  activities: AuditEvent[];
  loading: boolean;
  onRefresh: () => void;
}

export const RecentActivityPanel: React.FC<RecentActivityPanelProps> = ({
  activities,
  loading,
  onRefresh,
}) => {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Audit & Activity Log</h2>
          <p className="text-xs text-slate-500">
            Immutable system audit trails of examinations, student enrollments, and mark alterations
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="p-2 border border-slate-200 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
          title="Refresh Activities"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Activity Timeline List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading && activities.length === 0 ? (
          <div className="py-12 text-center text-slate-400">
            Loading activity log from MongoDB...
          </div>
        ) : activities.length === 0 ? (
          <div className="py-12 text-center text-slate-400">
            <Activity className="h-8 w-8 mx-auto mb-2 text-slate-300" />
            <p className="text-sm font-medium">No activity events recorded yet.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {activities.map((act, index) => {
              const dateObj = new Date(act.timestamp);
              const formattedDate = dateObj.toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              });
              const formattedTime = dateObj.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              });

              return (
                <div key={act.event_id || index} className="p-4 hover:bg-slate-50/70 transition-colors flex items-start space-x-3.5">
                  <div className="mt-0.5 h-8 w-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shrink-0">
                    <Activity className="h-4 w-4" />
                  </div>

                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-slate-800">
                        {act.description}
                      </span>
                      <span className="text-[11px] text-slate-400 flex items-center space-x-1">
                        <Clock className="h-3 w-3" />
                        <span>{formattedDate} at {formattedTime}</span>
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 pt-0.5">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px] font-semibold">
                        {act.event_type}
                      </span>
                      <span>•</span>
                      <span className="flex items-center space-x-1 text-slate-600">
                        <User className="h-3 w-3 text-slate-400" />
                        <span>Operator: {act.user_id}</span>
                      </span>
                      <span>•</span>
                      <span className="flex items-center space-x-1 text-slate-600 font-mono text-[11px]">
                        <Tag className="h-3 w-3 text-slate-400" />
                        <span>Target: {act.entity_id}</span>
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
