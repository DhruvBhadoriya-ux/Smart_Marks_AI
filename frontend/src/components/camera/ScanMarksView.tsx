import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Camera,
  UploadCloud,
  AlertCircle,
  Sparkles,
  CheckCircle2,
  RefreshCw,
  Maximize2,
  RotateCcw,
  Check,
  ShieldAlert,
  Eye,
  Sliders
} from 'lucide-react';
import { Exam, QuestionScore } from '../../types';
import { api } from '../../services/api';

interface ScanMarksViewProps {
  selectedExam: Exam | null;
  exams: Exam[];
  onSelectExam: (exam: Exam) => void;
  onOpenCreateExam: () => void;
}

type ScannerState = 'idle' | 'streaming' | 'captured' | 'processing' | 'verified';

export const ScanMarksView: React.FC<ScanMarksViewProps> = ({
  selectedExam,
  exams,
  onSelectExam,
  onOpenCreateExam,
}) => {
  const [scannerState, setScannerState] = useState<ScannerState>('idle');
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [capturedImageBlob, setCapturedImageBlob] = useState<Blob | null>(null);
  const [capturedImagePreview, setCapturedImagePreview] = useState<string | null>(null);

  // Scan Processing Result State
  const [scanResult, setScanResult] = useState<any | null>(null);
  const [processError, setProcessError] = useState<string | null>(null);
  const [editableScores, setEditableScores] = useState<QuestionScore[]>([]);
  const [editableStudentId, setEditableStudentId] = useState<string>('');
  const [approving, setApproving] = useState(false);
  const [approvalSuccess, setApprovalSuccess] = useState(false);

  // Media Stream & Video Refs
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Stop camera tracks and release resources
  const stopCameraStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        track.stop();
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // Cleanup on unmount or state switch
  useEffect(() => {
    return () => {
      stopCameraStream();
      if (capturedImagePreview && capturedImagePreview.startsWith('blob:')) {
        URL.revokeObjectURL(capturedImagePreview);
      }
    };
  }, [stopCameraStream, capturedImagePreview]);

  // Phase 1: Launch camera stream with environment-facing preference and laptop fallback
  const startCamera = async () => {
    setCameraError(null);
    setProcessError(null);
    setApprovalSuccess(false);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraError('Camera access is not supported on this browser or requires a secure HTTPS/localhost context.');
      return;
    }

    try {
      stopCameraStream();

      let stream: MediaStream;
      try {
        // Attempt environment-facing rear camera (ideal for mobile / tablet document scanning)
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        });
      } catch (envErr) {
        // Fallback for laptops / desktop webcams
        console.warn('Environment-facing camera not available, falling back to default video device:', envErr);
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });
      }

      streamRef.current = stream;
      setScannerState('streaming');

      // Bind to video element
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch((playErr) => {
            console.error('Video playback error:', playErr);
          });
        }
      }, 100);
    } catch (err: any) {
      console.error('getUserMedia error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraError('Camera permission was denied. Please allow camera permissions in your browser address bar.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraError('No camera device detected on this system. Please connect a webcam or use file upload.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCameraError('Camera is already in use by another application or tab. Please close other camera apps.');
      } else {
        setCameraError(err.message || 'Unable to access camera device.');
      }
      setScannerState('idle');
    }
  };

  // Phase 2: Capture still image from video stream using canvas
  const captureStillImage = () => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) {
      setCameraError('Camera stream is not ready for capture yet.');
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Draw full resolution frame
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Stop live camera to conserve battery & release camera device
    stopCameraStream();

    // Export high-quality JPEG blob
    canvas.toBlob(
      (blob) => {
        if (blob) {
          if (capturedImagePreview && capturedImagePreview.startsWith('blob:')) {
            URL.revokeObjectURL(capturedImagePreview);
          }
          const previewUrl = URL.createObjectURL(blob);
          setCapturedImageBlob(blob);
          setCapturedImagePreview(previewUrl);
          setScannerState('captured');
        }
      },
      'image/jpeg',
      0.95
    );
  };

  // Retake captured image
  const handleRetake = () => {
    if (capturedImagePreview && capturedImagePreview.startsWith('blob:')) {
      URL.revokeObjectURL(capturedImagePreview);
    }
    setCapturedImageBlob(null);
    setCapturedImagePreview(null);
    setScanResult(null);
    setProcessError(null);
    startCamera();
  };

  // Stop camera action
  const handleStopCamera = () => {
    stopCameraStream();
    setScannerState('idle');
  };

  // Upload Scanned Image fallback handler
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setProcessError('Please upload a valid image file (JPG, PNG, or WebP).');
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      setProcessError('Uploaded image exceeds the 15MB size limit.');
      return;
    }

    stopCameraStream();
    if (capturedImagePreview && capturedImagePreview.startsWith('blob:')) {
      URL.revokeObjectURL(capturedImagePreview);
    }

    const previewUrl = URL.createObjectURL(file);
    setCapturedImageBlob(file);
    setCapturedImagePreview(previewUrl);
    setScannerState('captured');
    setProcessError(null);
    setScanResult(null);

    // Reset input value so same file can be re-selected if needed
    e.target.value = '';
  };

  // Phase 3: Process scan with FastAPI backend
  const handleProcessScan = async () => {
    if (!capturedImageBlob || !selectedExam) return;

    try {
      setScannerState('processing');
      setProcessError(null);

      const formData = new FormData();
      formData.append('file', capturedImageBlob, 'marksheet_scan.jpg');
      formData.append('exam_id', selectedExam.exam_id);

      // Run extraction against backend
      const result = await api.processScanImage(formData);
      setScanResult(result);
      setEditableScores(result.scores || []);
      setEditableStudentId(result.student_id || '');
      setScannerState('verified');
    } catch (err: any) {
      console.error('OCR processing failure:', err);
      setProcessError(err.message || 'FastAPI image processing pipeline encountered an error.');
      setScannerState('captured');
    }
  };

  // Faculty verification field edit
  const handleScoreChange = (index: number, newScore: number) => {
    const updated = [...editableScores];
    updated[index] = {
      ...updated[index],
      obtained_marks: newScore,
      is_manually_edited: true,
      is_flagged: newScore > updated[index].max_marks || newScore < 0,
      flag_reason:
        newScore > updated[index].max_marks
          ? `Score (${newScore}) exceeds question max (${updated[index].max_marks})`
          : null,
    };
    setEditableScores(updated);
  };

  // Total calculated from edited scores
  const currentTotalObtained = editableScores.reduce(
    (sum, s) => sum + (Number(s.obtained_marks) || 0),
    0
  );

  // Faculty approval action
  const handleApproveRecord = async () => {
    if (!scanResult) return;
    try {
      setApproving(true);
      // Update any modified scores first
      await api.updateMarksRecord(
        scanResult.record_id,
        editableScores,
        editableStudentId,
        'Faculty verified scan and approved record'
      );
      // Finalize approval
      await api.approveMarksRecord(scanResult.record_id, 'Official Faculty Sign-off');
      setApprovalSuccess(true);
    } catch (err: any) {
      setProcessError(err.message || 'Failed to approve marks record.');
    } finally {
      setApproving(false);
    }
  };

  // Reset to scan another marksheet
  const handleScanNext = () => {
    if (capturedImagePreview && capturedImagePreview.startsWith('blob:')) {
      URL.revokeObjectURL(capturedImagePreview);
    }
    setCapturedImageBlob(null);
    setCapturedImagePreview(null);
    setScanResult(null);
    setProcessError(null);
    setApprovalSuccess(false);
    startCamera();
  };

  return (
    <div className="space-y-6">
      {/* Hidden file input for upload fallback */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept="image/jpeg,image/png,image/webp,image/jpg"
        className="hidden"
      />

      {/* Header */}
      <div className="pb-3 border-b border-slate-200">
        <h2 className="text-xl font-bold text-slate-900">Scan & Digitize Marks Strip</h2>
        <p className="text-xs text-slate-500">
          Browser camera scanner with OpenCV document alignment guide and structured OCR extraction
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
                    <span>{exam.questions.length} Questions</span>
                    <span className="font-semibold text-blue-600">{exam.total_marks} Marks</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Main Scanner Section */}
      {selectedExam && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Scanner Header Bar */}
          <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
                <Camera className="h-4 w-4" />
              </div>
              <div>
                <h3 className="font-bold text-sm">
                  {selectedExam.subject_code} — {selectedExam.subject_name}
                </h3>
                <span className="text-[11px] text-blue-300">
                  {selectedExam.exam_type.replace('_', ' ')} • {selectedExam.questions.length} Questions ({selectedExam.total_marks} Marks)
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {scannerState === 'streaming' && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
                  Live Camera Active
                </span>
              )}
              {scannerState === 'captured' && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  Frame Captured
                </span>
              )}
            </div>
          </div>

          {/* Camera Error Alert */}
          {cameraError && (
            <div className="m-5 p-4 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs flex items-start space-x-3">
              <ShieldAlert className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-bold text-sm">Camera Hardware Notice</p>
                <p>{cameraError}</p>
                <button
                  onClick={startCamera}
                  className="mt-2 px-3 py-1 bg-red-600 text-white font-semibold rounded-md hover:bg-red-700 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}

          {/* Process Error Alert */}
          {processError && (
            <div className="m-5 p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs flex items-start space-x-3">
              <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-sm">Processing Notice</p>
                <p>{processError}</p>
              </div>
            </div>
          )}

          {/* Body: State 1 — Idle */}
          {scannerState === 'idle' && (
            <div className="p-8 text-center space-y-4">
              <div className="h-16 w-16 mx-auto rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center">
                <Camera className="h-8 w-8" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-800">
                  Ready to Scan Marksheet for {selectedExam.subject_code}
                </h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                  Position the student marks strip under clear lighting. Align with the camera guide for optimal OpenCV boundary detection.
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                <button
                  onClick={startCamera}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-sm inline-flex items-center space-x-2 transition-all hover:shadow"
                >
                  <Camera className="h-4 w-4" />
                  <span>Launch Live Camera</span>
                </button>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold inline-flex items-center space-x-2 transition-all"
                >
                  <UploadCloud className="h-4 w-4" />
                  <span>Upload Scanned Image</span>
                </button>
              </div>
              <div className="text-[11px] text-slate-400 pt-2 flex items-center justify-center space-x-1.5">
                <Sparkles className="h-3.5 w-3.5 text-blue-500" />
                <span>OpenCV perspective rectification & RapidOCR extraction active.</span>
              </div>
            </div>
          )}

          {/* Body: State 2 — Live Camera Streaming with Alignment Guide */}
          {scannerState === 'streaming' && (
            <div className="p-4 sm:p-6 bg-slate-950 flex flex-col items-center">
              {/* Camera Stream Viewport with Alignment Guide */}
              <div className="relative w-full max-w-2xl bg-black rounded-xl overflow-hidden shadow-2xl aspect-[4/3] sm:aspect-[16/9]">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />

                {/* Marks Strip Alignment Guide Overlay */}
                <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center p-6">
                  {/* Outer darkened vignette */}
                  <div className="absolute inset-0 border-[28px] sm:border-[44px] border-slate-950/60" />

                  {/* Rectangular Marks-Strip Target Frame */}
                  <div className="relative w-full h-full max-w-lg max-h-72 border-2 border-dashed border-emerald-400/80 rounded-xl flex flex-col justify-between p-3 shadow-2xl">
                    {/* Corner Accent Brackets */}
                    <div className="absolute -top-1 -left-1 w-6 h-6 border-t-4 border-l-4 border-emerald-400 rounded-tl-lg" />
                    <div className="absolute -top-1 -right-1 w-6 h-6 border-t-4 border-r-4 border-emerald-400 rounded-tr-lg" />
                    <div className="absolute -bottom-1 -left-1 w-6 h-6 border-b-4 border-l-4 border-emerald-400 rounded-bl-lg" />
                    <div className="absolute -bottom-1 -right-1 w-6 h-6 border-b-4 border-r-4 border-emerald-400 rounded-br-lg" />

                    {/* Guide Text Pill */}
                    <div className="self-center bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full text-[11px] font-medium text-emerald-300 border border-emerald-500/30 flex items-center space-x-1.5 shadow-lg">
                      <Maximize2 className="h-3 w-3" />
                      <span>Align student roll number and marks table here</span>
                    </div>

                    <div className="self-center text-[10px] text-slate-300/80 bg-slate-950/60 px-2 py-0.5 rounded">
                      Ensure adequate lighting • Avoid hand shadows
                    </div>
                  </div>
                </div>
              </div>

              {/* Live Camera Controls */}
              <div className="mt-5 flex items-center justify-center space-x-4">
                <button
                  onClick={handleStopCamera}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition-colors"
                >
                  Stop Camera
                </button>
                <button
                  onClick={captureStillImage}
                  className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold rounded-xl text-xs inline-flex items-center space-x-2 shadow-lg shadow-emerald-500/20 transition-all hover:scale-105 active:scale-95"
                >
                  <Camera className="h-4 w-4" />
                  <span>Capture Image</span>
                </button>
              </div>
            </div>
          )}

          {/* Body: State 3 — Image Captured Preview & Ready to Process */}
          {(scannerState === 'captured' || scannerState === 'processing') && capturedImagePreview && (
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                {/* Captured Still Preview */}
                <div className="relative rounded-xl overflow-hidden border border-slate-300 bg-slate-100 aspect-[4/3] flex items-center justify-center shadow-inner">
                  <img
                    src={capturedImagePreview}
                    alt="Captured Marksheet Preview"
                    className="w-full h-full object-contain"
                  />
                  <div className="absolute top-3 left-3 bg-slate-900/80 text-white text-[10px] font-semibold px-2.5 py-1 rounded-md backdrop-blur-sm">
                    Captured Frame Preview
                  </div>
                </div>

                {/* Pre-Processing Confirmation Card */}
                <div className="space-y-4">
                  <div className="space-y-1">
                    <h4 className="font-bold text-base text-slate-900">
                      Marksheet Ready for Processing
                    </h4>
                    <p className="text-xs text-slate-500 leading-relaxed">
                      OpenCV will automatically detect the table boundary, rectify perspective distortion, and extract handwritten question scores with RapidOCR.
                    </p>
                  </div>

                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
                    <div className="flex justify-between text-slate-600">
                      <span>Target Subject:</span>
                      <span className="font-semibold text-slate-900">{selectedExam.subject_code}</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Question Pattern:</span>
                      <span className="font-semibold text-slate-900">{selectedExam.questions.length} Questions ({selectedExam.total_marks} pts)</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>AI Pipeline:</span>
                      <span className="font-semibold text-emerald-600">OpenCV CLAHE + RapidOCR (ARM64)</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 pt-2">
                    <button
                      onClick={handleRetake}
                      disabled={scannerState === 'processing'}
                      className="px-4 py-2.5 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-semibold inline-flex items-center space-x-1.5 transition-colors"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                      <span>Retake Image</span>
                    </button>
                    <button
                      onClick={handleProcessScan}
                      disabled={scannerState === 'processing'}
                      className="flex-1 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-sm inline-flex items-center justify-center space-x-2 transition-all hover:shadow"
                    >
                      {scannerState === 'processing' ? (
                        <>
                          <RefreshCw className="h-4 w-4 animate-spin text-white" />
                          <span>Processing with OpenCV & OCR...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-4 w-4" />
                          <span>Process Scan with AI</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Body: State 4 — Side-by-Side Review & Verification */}
          {scannerState === 'verified' && scanResult && (
            <div className="p-6 space-y-6">
              {/* Approval Success Banner */}
              {approvalSuccess ? (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-xs space-y-3">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
                    <div>
                      <h4 className="font-bold text-sm">Marksheet Verified & Approved!</h4>
                      <p className="text-emerald-700 text-[11px] mt-0.5">
                        Record for student <strong>{editableStudentId}</strong> has been committed to MongoDB with faculty audit signature.
                      </p>
                    </div>
                  </div>
                  <div className="pt-2 flex items-center space-x-3">
                    <button
                      onClick={handleScanNext}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold inline-flex items-center space-x-1.5 transition-colors shadow-xs"
                    >
                      <Camera className="h-3.5 w-3.5" />
                      <span>Scan Next Marksheet</span>
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {/* Anomaly / Quality Flags Banner */}
                  {scanResult.has_flags && (
                    <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start space-x-2.5">
                      <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">Faculty Review Required:</span>
                        <p className="text-amber-800 text-[11px] mt-0.5">
                          Certain recognized fields require manual verification before final sign-off. Please check the highlighted inputs below against the scan crop.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Side-by-Side Split: Original Scan vs Editable Form */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Left: Scanned & Preprocessed Image */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                        <span className="flex items-center space-x-1.5">
                          <Eye className="h-3.5 w-3.5 text-blue-600" />
                          <span>Rectified Marks Strip Scan</span>
                        </span>
                        {scanResult.perspective_corrected && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 font-bold">
                            OpenCV Deskewed
                          </span>
                        )}
                      </div>

                      <div className="rounded-xl overflow-hidden border border-slate-300 bg-slate-100 aspect-[4/3] flex items-center justify-center shadow-inner">
                        <img
                          src={scanResult.scan_image_url || capturedImagePreview}
                          alt="Rectified Scan Crop"
                          className="w-full h-full object-contain"
                        />
                      </div>
                    </div>

                    {/* Right: Extracted & Editable Fields */}
                    <div className="space-y-4">
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-700 pb-1 border-b border-slate-100">
                        <span className="flex items-center space-x-1.5">
                          <Sliders className="h-3.5 w-3.5 text-blue-600" />
                          <span>Extracted Values & Verification Form</span>
                        </span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            scanResult.status === 'APPROVED'
                              ? 'bg-emerald-100 text-emerald-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}
                        >
                          {scanResult.status}
                        </span>
                      </div>

                      {/* Student Roll No Field */}
                      <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-1">
                        <label className="block text-[11px] font-semibold text-slate-600">
                          Student Roll Number / Enrollment ID
                        </label>
                        <div className="flex items-center space-x-2">
                          <input
                            type="text"
                            value={editableStudentId}
                            onChange={(e) => setEditableStudentId(e.target.value)}
                            className="flex-1 px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-mono font-bold uppercase focus:ring-2 focus:ring-blue-500 outline-none"
                          />
                          <span className="text-xs text-slate-600 font-medium">
                            {scanResult.student_name || 'Enrolled Student'}
                          </span>
                        </div>
                      </div>

                      {/* Question-Wise Scores List */}
                      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                        {editableScores.map((score, idx) => (
                          <div
                            key={score.question_id}
                            className={`p-2.5 rounded-xl border flex items-center justify-between text-xs transition-colors ${
                              score.is_flagged
                                ? 'border-amber-300 bg-amber-50/50'
                                : 'border-slate-200 bg-white'
                            }`}
                          >
                            <div className="space-y-0.5">
                              <div className="flex items-center space-x-1.5">
                                <span className="font-bold text-slate-800">{score.display_name}</span>
                                <span className="text-[10px] text-slate-400 font-mono">({score.question_id})</span>
                                {score.confidence > 0 && (
                                  <span className="text-[10px] text-slate-500 font-medium">
                                    • {Math.round(score.confidence * 100)}% conf
                                  </span>
                                )}
                              </div>
                              {score.flag_reason && (
                                <p className="text-[10px] text-amber-700 font-medium">
                                  {score.flag_reason}
                                </p>
                              )}
                            </div>

                            <div className="flex items-center space-x-1.5">
                              <input
                                type="number"
                                step="0.5"
                                min="0"
                                max={score.max_marks}
                                value={score.obtained_marks}
                                onChange={(e) =>
                                  handleScoreChange(idx, parseFloat(e.target.value) || 0)
                                }
                                className={`w-16 px-2 py-1 text-right font-bold text-xs border rounded-lg outline-none ${
                                  score.is_flagged
                                    ? 'border-amber-400 focus:ring-2 focus:ring-amber-500 bg-white'
                                    : 'border-slate-300 focus:ring-2 focus:ring-blue-500'
                                }`}
                              />
                              <span className="text-slate-400 text-[11px]">/ {score.max_marks}</span>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Total Marks Banner */}
                      <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl flex items-center justify-between text-xs text-blue-900">
                        <span className="font-semibold">Calculated Total Marks:</span>
                        <div className="flex items-baseline space-x-1">
                          <span className="text-base font-bold text-blue-700">
                            {currentTotalObtained}
                          </span>
                          <span className="text-slate-500 font-medium">
                            / {scanResult.total_max} pts ({Math.round((currentTotalObtained / (scanResult.total_max || 1)) * 100)}%)
                          </span>
                        </div>
                      </div>

                      {/* Approval Action Buttons */}
                      <div className="pt-2 flex items-center space-x-3">
                        <button
                          onClick={handleRetake}
                          className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-semibold"
                        >
                          Retake
                        </button>
                        <button
                          onClick={handleApproveRecord}
                          disabled={approving}
                          className="flex-1 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-sm inline-flex items-center justify-center space-x-2 transition-all hover:shadow"
                        >
                          <Check className="h-4 w-4" />
                          <span>{approving ? 'Committing to MongoDB...' : 'Approve & Commit Record'}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
