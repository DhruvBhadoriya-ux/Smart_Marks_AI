import React, { useState, useEffect, useCallback } from 'react';
import {
  FileSpreadsheet,
  Download,
  Cloud,
  CheckCircle2,
  Clock,
  ExternalLink,
  ShieldAlert,
  Sparkles,
  Info,
  RefreshCw,
  FolderSync
} from 'lucide-react';
import { Exam } from '../../types';
import { api } from '../../services/api';

interface ExportViewProps {
  exams: Exam[];
  selectedExam: Exam | null;
  onSelectExam: (exam: Exam) => void;
  onOpenCreateExam: () => void;
}

export const ExportView: React.FC<ExportViewProps> = ({
  exams,
  selectedExam,
  onSelectExam,
  onOpenCreateExam,
}) => {
  const [onlyApproved, setOnlyApproved] = useState(true);
  const [preview, setPreview] = useState<any | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Microsoft OneDrive state
  const [msAuthUrl, setMsAuthUrl] = useState<string | null>(null);
  const [msConfigured, setMsConfigured] = useState<boolean>(false);
  const [msTokenInput, setMsTokenInput] = useState<string>('');
  const [oneDriveUploading, setOneDriveUploading] = useState(false);
  const [oneDriveResult, setOneDriveResult] = useState<any | null>(null);
  const [oneDriveError, setOneDriveError] = useState<string | null>(null);

  const loadPreview = useCallback(async (examId: string) => {
    try {
      setLoadingPreview(true);
      const data = await api.getExportPreview(examId);
      setPreview(data);
      setMsConfigured(data.microsoft_integration_configured);

      // Fetch MS auth URL
      const authData = await api.getOneDriveAuthUrl(examId);
      if (authData.configured && authData.auth_url) {
        setMsAuthUrl(authData.auth_url);
      }
    } catch (err) {
      console.error('Failed to load export preview:', err);
    } finally {
      setLoadingPreview(false);
    }
  }, []);

  useEffect(() => {
    if (selectedExam) {
      loadPreview(selectedExam.exam_id);
    } else if (exams.length > 0) {
      onSelectExam(exams[0]);
    }
  }, [selectedExam, exams, loadPreview, onSelectExam]);

  // Handle direct local XLSX download
  const handleDownloadExcel = () => {
    if (!selectedExam) return;
    setDownloading(true);
    const downloadUrl = api.getDownloadExcelUrl(selectedExam.exam_id, onlyApproved);

    // Create hidden download trigger
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', preview?.suggested_filename || 'SmartMarks_Evaluation.xlsx');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => setDownloading(false), 1200);
  };

  // Handle OneDrive Upload
  const handleOneDriveUpload = async () => {
    if (!selectedExam) return;
    setOneDriveError(null);
    setOneDriveResult(null);

    if (!msTokenInput.trim()) {
      setOneDriveError('Please enter a Microsoft Graph access token or sign in above.');
      return;
    }

    try {
      setOneDriveUploading(true);
      const res = await api.uploadToOneDrive({
        exam_id: selectedExam.exam_id,
        access_token: msTokenInput.trim(),
        only_approved: onlyApproved,
        folder_name: 'SmartMarks_AI',
      });
      setOneDriveResult(res.onedrive_result);
    } catch (err: any) {
      setOneDriveError(err.message || 'Failed to upload workbook to OneDrive.');
    } finally {
      setOneDriveUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-3 border-b border-slate-200">
        <h2 className="text-xl font-bold text-slate-900">Export Examination Records</h2>
        <p className="text-xs text-slate-500">
          Generate formatted Excel (.xlsx) workbooks from verified MongoDB records and sync to Microsoft OneDrive
        </p>
      </div>

      {/* Examination Selector */}
      {exams.length === 0 ? (
        <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
          <FileSpreadsheet className="h-10 w-10 text-slate-300 mx-auto mb-2" />
          <h3 className="font-semibold text-sm text-slate-700">No Examinations Configured</h3>
          <p className="text-xs text-slate-500 mt-1 mb-4">
            Create an examination session first before exporting marks records.
          </p>
          <button
            onClick={onOpenCreateExam}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold"
          >
            Create Examination
          </button>
        </div>
      ) : (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
          <label className="block text-xs font-semibold text-slate-700">
            Select Examination Session to Export *
          </label>
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
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        exam.exam_type === 'MID_SEMESTER'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-purple-100 text-purple-700'
                      }`}
                    >
                      {exam.exam_type === 'MID_SEMESTER' ? 'Mid-Sem' : 'End-Sem'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 font-medium truncate mt-1">
                    {exam.subject_name}
                  </p>
                  <div className="mt-2 text-[11px] text-slate-500 flex justify-between">
                    <span>Sem {exam.semester}</span>
                    <span className="font-semibold text-blue-600">{exam.total_marks} Marks</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {selectedExam && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Export Controls & Statistics */}
          <div className="lg:col-span-2 space-y-5">
            {/* Export Scope Selector */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
                <FileSpreadsheet className="h-4 w-4 text-blue-600" />
                <span>Export Configuration & Scope</span>
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div
                  onClick={() => setOnlyApproved(true)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    onlyApproved
                      ? 'border-emerald-600 bg-emerald-50/40 ring-2 ring-emerald-500/20'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <CheckCircle2
                      className={`h-4 w-4 ${onlyApproved ? 'text-emerald-600' : 'text-slate-400'}`}
                    />
                    <span className="font-bold text-xs text-slate-800">
                      Approved Records Only
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Official export standard. Excludes unverified drafts to prevent incomplete records.
                  </p>
                </div>

                <div
                  onClick={() => setOnlyApproved(false)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    !onlyApproved
                      ? 'border-blue-600 bg-blue-50/40 ring-2 ring-blue-500/20'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <Clock
                      className={`h-4 w-4 ${!onlyApproved ? 'text-blue-600' : 'text-slate-400'}`}
                    />
                    <span className="font-bold text-xs text-slate-800">
                      Include All Records
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Includes both verified and pending review records with clear status flags.
                  </p>
                </div>
              </div>

              {/* Status & Counts Banner */}
              {preview && (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between font-semibold text-slate-800">
                    <div className="flex items-center space-x-2">
                      <span>Export Readiness Summary:</span>
                      <button
                        onClick={() => selectedExam && loadPreview(selectedExam.exam_id)}
                        className="p-1 text-slate-400 hover:text-slate-600 rounded"
                        title="Refresh Preview Counts"
                      >
                        <RefreshCw className={`h-3 w-3 ${loadingPreview ? 'animate-spin text-blue-600' : ''}`} />
                      </button>
                    </div>
                    <span className="font-mono text-[11px] text-slate-500">
                      {preview.suggested_filename}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 text-center">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">
                        Total Scanned
                      </div>
                      <div className="text-base font-bold text-slate-800">
                        {preview.total_records}
                      </div>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 text-center">
                      <div className="text-emerald-600 text-[10px] uppercase font-semibold">
                        Faculty Approved
                      </div>
                      <div className="text-base font-bold text-emerald-600">
                        {preview.approved_records}
                      </div>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 text-center">
                      <div className="text-amber-600 text-[10px] uppercase font-semibold">
                        Pending Review
                      </div>
                      <div className="text-base font-bold text-amber-600">
                        {preview.pending_records}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Local Download Primary Button */}
              <div className="pt-2">
                <button
                  onClick={handleDownloadExcel}
                  disabled={downloading}
                  className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-sm inline-flex items-center justify-center space-x-2 transition-all hover:shadow"
                >
                  <Download className={`h-4 w-4 ${downloading ? 'animate-bounce' : ''}`} />
                  <span>
                    {downloading
                      ? 'Generating Excel Workbook...'
                      : `Download Formatted Excel Workbook (${onlyApproved ? preview?.approved_records ?? 0 : preview?.total_records ?? 0} Records)`}
                  </span>
                </button>
                <p className="text-[11px] text-slate-400 text-center mt-2 flex items-center justify-center space-x-1">
                  <Sparkles className="h-3 w-3 text-emerald-500" />
                  <span>Generated with openpyxl • Includes question-wise marks, totals, and metadata</span>
                </p>
              </div>
            </div>
          </div>

          {/* Right Column: Microsoft OneDrive Cloud Sync */}
          <div className="space-y-5">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
                    <Cloud className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-slate-900">Microsoft OneDrive</h3>
                    <span className="text-[10px] text-slate-500">Microsoft 365 Cloud Sync</span>
                  </div>
                </div>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    msConfigured
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {msConfigured ? 'MSAL Active' : 'Optional'}
                </span>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">
                Save the examination workbook directly into your institutional OneDrive repository via Microsoft Graph API.
              </p>

              {msConfigured && msAuthUrl && (
                <a
                  href={msAuthUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full py-2 px-3 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-lg text-xs font-semibold inline-flex items-center justify-center space-x-1.5 transition-colors"
                >
                  <span>Sign In with Microsoft</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}

              {/* Token / Upload form */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <label className="block text-xs font-semibold text-slate-700">
                  Microsoft Graph Access Token
                </label>
                <input
                  type="password"
                  placeholder="Paste Bearer token or sign in above..."
                  value={msTokenInput}
                  onChange={(e) => setMsTokenInput(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500 outline-none"
                />

                <button
                  onClick={handleOneDriveUpload}
                  disabled={oneDriveUploading}
                  className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold inline-flex items-center justify-center space-x-1.5 transition-colors shadow-xs"
                >
                  <FolderSync className={`h-3.5 w-3.5 ${oneDriveUploading ? 'animate-spin' : ''}`} />
                  <span>{oneDriveUploading ? 'Uploading to OneDrive...' : 'Upload to OneDrive'}</span>
                </button>
              </div>

              {/* Error Alert */}
              {oneDriveError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-start space-x-2">
                  <ShieldAlert className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                  <span>{oneDriveError}</span>
                </div>
              )}

              {/* Success Alert */}
              {oneDriveResult && (
                <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1.5 text-xs text-emerald-900">
                  <div className="flex items-center space-x-1.5 font-bold">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    <span>Uploaded Successfully!</span>
                  </div>
                  <p className="text-[11px] text-emerald-700">
                    Saved to folder: <span className="font-semibold">{oneDriveResult.destination_folder}</span>
                  </p>
                  {oneDriveResult.web_url && (
                    <a
                      href={oneDriveResult.web_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center space-x-1 font-semibold text-blue-700 hover:underline pt-1"
                    >
                      <span>Open in Excel Online</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              )}

              {/* Fallback Notice */}
              {!msConfigured && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-500 space-y-1">
                  <div className="flex items-center space-x-1 text-slate-700 font-semibold">
                    <Info className="h-3.5 w-3.5 text-blue-500" />
                    <span>Local Download is Always Active</span>
                  </div>
                  <p>
                    Microsoft OneDrive export is an optional cloud feature. To enable it, configure <code className="bg-slate-200 px-1 rounded">AZURE_CLIENT_ID</code> in your <code className="bg-slate-200 px-1 rounded">.env</code> file.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
