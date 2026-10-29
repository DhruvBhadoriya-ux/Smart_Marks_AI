import React from 'react';
import {
  LayoutDashboard,
  FileSpreadsheet,
  Scan,
  Users,
  Activity,
  Download,
  Award,
  ChevronRight,
  ShieldCheck,
  Menu,
  X
} from 'lucide-react';

export type TabType = 'dashboard' | 'exams' | 'scan' | 'students' | 'export' | 'activity';

interface NavigationProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onTabChange,
  mobileMenuOpen,
  setMobileMenuOpen,
}) => {
  const navItems = [
    { id: 'dashboard' as TabType, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'exams' as TabType, label: 'Examinations', icon: FileSpreadsheet },
    { id: 'scan' as TabType, label: 'Scan & Digitization', icon: Scan },
    { id: 'students' as TabType, label: 'Students', icon: Users },
    { id: 'export' as TabType, label: 'Export Records', icon: Download },
    { id: 'activity' as TabType, label: 'Activity Logs', icon: Activity },
  ];

  return (
    <>
      {/* Top Mobile Bar */}
      <div className="lg:hidden bg-slate-900 text-white px-4 py-3 flex items-center justify-between shadow-md sticky top-0 z-50">
        <div className="flex items-center space-x-2.5">
          <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-sm">
            SM
          </div>
          <div>
            <span className="font-semibold text-sm tracking-tight block">SmartMarks AI</span>
            <span className="text-[10px] text-blue-300 block -mt-1">Faculty Digitizer</span>
          </div>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1.5 rounded-md hover:bg-slate-800 text-slate-300"
          aria-label="Toggle Menu"
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Sidebar Navigation */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-slate-900 text-slate-300 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        } border-r border-slate-800 shadow-xl`}
      >
        {/* Brand Header */}
        <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
              <Award className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-base text-white tracking-tight leading-none">SmartMarks AI</h1>
              <span className="text-xs text-blue-400 font-medium">Evaluation Portal</span>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Core Modules
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onTabChange(item.id);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                    : 'text-slate-300 hover:bg-slate-800/70 hover:text-white'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {isActive && <ChevronRight className="h-4 w-4 text-blue-200" />}
              </button>
            );
          })}
        </nav>

        {/* Faculty Status Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/40">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-xs font-semibold text-slate-200">
              Prof
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-200 truncate">Dr. S. K. Mehta</p>
              <p className="text-[11px] text-slate-400 truncate">Dept. of Computer Science</p>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between px-2 py-1.5 rounded bg-emerald-950/40 border border-emerald-800/40 text-[11px] text-emerald-400">
            <span className="flex items-center space-x-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>System Online</span>
            </span>
            <span className="flex items-center space-x-1 text-slate-400">
              <ShieldCheck className="h-3 w-3 text-emerald-400" />
              <span>RBAC Active</span>
            </span>
          </div>
        </div>
      </aside>

      {/* Backdrop for mobile */}
      {mobileMenuOpen && (
        <div
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 bg-slate-900/60 z-30 lg:hidden backdrop-blur-sm"
        />
      )}
    </>
  );
};
