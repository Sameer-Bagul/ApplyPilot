'use client';

import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  Video,
  Camera,
  FileText,
  ExternalLink,
  Download,
  Copy,
  Check,
  Play,
  Search,
  RefreshCw,
  Clock,
  Building2,
  MapPin,
  Sparkles,
  ShieldAlert,
  AlertCircle,
  ArrowRight,
  Terminal,
  Calendar,
  Layers,
} from 'lucide-react';
import { RouteBadge } from './ui/RouteBadge';

interface AppliedViewProps {
  onSelectJob?: (url: string) => void;
}

export function AppliedView({ onSelectJob }: AppliedViewProps) {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedJob, setSelectedJob] = useState<any | null>(null);
  const [activeProofTab, setActiveProofTab] = useState<'video' | 'screenshot' | 'log'>('video');

  // Audit log state
  const [logData, setLogData] = useState<any | null>(null);
  const [loadingLog, setLoadingLog] = useState(false);

  // Copy status
  const [copiedVideo, setCopiedVideo] = useState(false);
  const [copiedScreenshot, setCopiedScreenshot] = useState(false);
  const [copiedLog, setCopiedLog] = useState(false);

  const fetchAppliedJobs = async () => {
    setLoading(true);
    try {
      const q = search ? `?search=${encodeURIComponent(search)}` : '';
      const res = await fetch(`/api/jobs/applied${q}`);
      const data = await res.json();
      if (data.success) {
        setJobs(data.jobs || []);
        if (data.jobs && data.jobs.length > 0) {
          // Select first job if none selected or previous selection no longer in list
          if (!selectedJob || !data.jobs.find((j: any) => j.url === selectedJob.url)) {
            setSelectedJob(data.jobs[0]);
          }
        } else {
          setSelectedJob(null);
        }
      }
    } catch (err) {
      console.error('Failed fetching applied jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppliedJobs();
  }, [search]);

  // Fetch execution log when selected job changes
  useEffect(() => {
    if (!selectedJob) {
      setLogData(null);
      return;
    }

    const fetchLog = async () => {
      setLoadingLog(true);
      try {
        const res = await fetch(`/api/proofs?url=${encodeURIComponent(selectedJob.url)}&type=log`);
        const json = await res.json();
        if (json.success && json.log) {
          setLogData(json.log);
        } else {
          setLogData(null);
        }
      } catch (err) {
        setLogData(null);
      } finally {
        setLoadingLog(false);
      }
    };

    fetchLog();
  }, [selectedJob?.url]);

  const getScoreBadgeClass = (score: number | null) => {
    if (score == null) return 'text-zinc-600 bg-zinc-100 border-zinc-200';
    if (score >= 8) return 'text-emerald-800 bg-emerald-50 border-emerald-200 shadow-2xs';
    if (score >= 5) return 'text-amber-800 bg-amber-50 border-amber-200 shadow-2xs';
    return 'text-rose-800 bg-rose-50 border-rose-200 shadow-2xs';
  };

  const videoCount = jobs.filter(j => Boolean(j.proof_video_path)).length;
  const screenshotCount = jobs.filter(j => Boolean(j.proof_screenshot_path)).length;
  const logCount = jobs.filter(j => Boolean(j.proof_log_path)).length;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Banner & KPI Metrics */}
      <div className="liquid-glass-elevated rounded-3xl p-6 sm:p-7 border border-white/90 shadow-sm relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-2xs">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Autonomous Applications Vault</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-zinc-900">
              Applied Jobs & Proof Recordings
            </h1>
            <p className="text-xs sm:text-sm text-zinc-600 leading-relaxed">
              Every job successfully submitted by ApplyPilot's Playwright engine. Review 720p HD session recordings, high-resolution confirmation receipts, and forensic audit logs saved directly to your local device.
            </p>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 shrink-0">
            <div className="liquid-glass rounded-2xl p-3.5 border border-white/90 shadow-2xs text-center min-w-[100px]">
              <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block mb-0.5">Total Applied</span>
              <span className="text-xl font-extrabold text-zinc-900">{jobs.length}</span>
            </div>
            <div className="liquid-glass rounded-2xl p-3.5 border border-white/90 shadow-2xs text-center min-w-[100px]">
              <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block mb-0.5">720p Videos</span>
              <span className="text-xl font-extrabold text-cyan-700 flex items-center justify-center gap-1">
                <Video className="w-4 h-4 text-cyan-600" />
                {videoCount}
              </span>
            </div>
            <div className="liquid-glass rounded-2xl p-3.5 border border-white/90 shadow-2xs text-center min-w-[100px]">
              <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block mb-0.5">Receipts</span>
              <span className="text-xl font-extrabold text-emerald-700 flex items-center justify-center gap-1">
                <Camera className="w-4 h-4 text-emerald-600" />
                {screenshotCount}
              </span>
            </div>
            <div className="liquid-glass rounded-2xl p-3.5 border border-white/90 shadow-2xs text-center min-w-[100px]">
              <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block mb-0.5">Audit Logs</span>
              <span className="text-xl font-extrabold text-indigo-700 flex items-center justify-center gap-1">
                <FileText className="w-4 h-4 text-indigo-600" />
                {logCount || jobs.length}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Search & Actions Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search applied roles, companies, or locations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white/80 border border-zinc-200/90 rounded-2xl pl-10 pr-4 py-2.5 text-xs text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:border-cyan-400 shadow-2xs transition"
          />
        </div>

        <button
          onClick={fetchAppliedJobs}
          className="liquid-pill px-4 py-2 rounded-2xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center justify-center gap-2 transition cursor-pointer shadow-2xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-zinc-500 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Applications</span>
        </button>
      </div>

      {/* Main Dual-Pane Section */}
      {loading && jobs.length === 0 ? (
        <div className="py-24 text-center text-sm text-zinc-400">Loading applied applications vault...</div>
      ) : jobs.length === 0 ? (
        <div className="liquid-glass rounded-3xl p-12 text-center border border-white/90 shadow-sm space-y-4 max-w-xl mx-auto">
          <div className="w-14 h-14 rounded-2xl bg-zinc-100 flex items-center justify-center mx-auto text-zinc-400 shadow-inner">
            <CheckCircle2 className="w-7 h-7 text-zinc-400" />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-zinc-900">No Applications Submitted Yet</h3>
            <p className="text-xs text-zinc-500 max-w-sm mx-auto leading-relaxed">
              When ApplyPilot runs and submits applications, your 720p HD screen recordings, submission receipts, and execution logs will automatically appear here.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Applied Jobs List (5 Cols) */}
          <div className="lg:col-span-5 space-y-3 max-h-[calc(100vh-14rem)] overflow-y-auto pr-1">
            {jobs.map((j) => {
              const isSelected = selectedJob?.url === j.url;
              const hasVideo = Boolean(j.proof_video_path);
              const hasScreenshot = Boolean(j.proof_screenshot_path);

              return (
                <div
                  key={j.url}
                  onClick={() => setSelectedJob(j)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer relative ${
                    isSelected
                      ? 'liquid-glass-elevated bg-white/95 border-cyan-400 shadow-md ring-1 ring-cyan-300'
                      : 'liquid-glass bg-white/70 hover:bg-white/90 border-white/90 shadow-2xs hover:shadow-xs'
                  }`}
                >
                  <div className="space-y-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getScoreBadgeClass(j.fit_score)}`}>
                            {j.fit_score ?? 'Unscored'}/10
                          </span>
                          <RouteBadge route={j.execution_route || 'PORTAL_ONLY'} />
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                            Applied
                          </span>
                        </div>
                        <h3 className="text-sm font-bold text-zinc-900 truncate">
                          {j.title}
                        </h3>
                        <div className="text-xs text-zinc-500 flex items-center gap-2 mt-0.5">
                          <span className="font-semibold text-zinc-800 flex items-center gap-1">
                            <Building2 className="w-3.5 h-3.5 text-cyan-600" />
                            {j.company}
                          </span>
                          <span>•</span>
                          <span className="truncate flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-zinc-400" />
                            {j.location || 'Remote'}
                          </span>
                        </div>
                      </div>

                      {hasVideo && (
                        <div className="p-2 rounded-xl bg-cyan-50 border border-cyan-200 text-cyan-700 shrink-0" title="720p HD Video Available">
                          <Video className="w-4 h-4" />
                        </div>
                      )}
                    </div>

                    {/* Proof Status Pills & Date */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-zinc-200/60 text-[11px] text-zinc-500">
                      <div className="flex items-center gap-1.5 font-medium">
                        <Calendar className="w-3 h-3 text-zinc-400" />
                        <span>
                          {j.applied_at ? new Date(j.applied_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recently'}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {hasVideo && (
                          <span className="px-1.5 py-0.5 rounded-md text-[10px] font-semibold bg-cyan-50 text-cyan-700 border border-cyan-200/60">
                            720p WebM
                          </span>
                        )}
                        {hasScreenshot && (
                          <span className="px-1.5 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                            PNG Receipt
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Column: Verification & Audit Inspection Center (7 Cols) */}
          <div className="lg:col-span-7">
            {selectedJob ? (
              <div className="liquid-glass-elevated rounded-3xl border border-white/90 shadow-md p-6 space-y-6">
                {/* Header for Selected Role */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200/70">
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-cyan-700">Proof Verification</span>
                      <span className="text-xs text-zinc-400">•</span>
                      <span className="text-xs text-zinc-500 font-mono">
                        {selectedJob.applied_at ? new Date(selectedJob.applied_at).toLocaleString() : 'Recent Submission'}
                      </span>
                    </div>
                    <h2 className="text-lg font-bold text-zinc-900 truncate">
                      {selectedJob.title}
                    </h2>
                    <div className="text-xs text-zinc-600 flex items-center gap-2">
                      <Building2 className="w-3.5 h-3.5 text-cyan-600" />
                      <span className="font-semibold text-zinc-800">{selectedJob.company}</span>
                      {selectedJob.salary && (
                        <>
                          <span>•</span>
                          <span className="text-emerald-700 font-medium">{selectedJob.salary}</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {onSelectJob && (
                      <button
                        onClick={() => onSelectJob(selectedJob.url)}
                        className="liquid-pill px-3 py-1.5 rounded-xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center gap-1.5 shadow-2xs transition cursor-pointer"
                        title="Open full job details drawer"
                      >
                        <span>Full Job Details</span>
                        <ArrowRight className="w-3.5 h-3.5 text-zinc-500" />
                      </button>
                    )}
                    {selectedJob.url && (
                      <a
                        href={selectedJob.url}
                        target="_blank"
                        rel="noreferrer"
                        className="liquid-pill p-2 rounded-xl text-zinc-600 hover:text-zinc-950 transition shadow-2xs"
                        title="Open Job Posting"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Sub-tab Switcher: Video vs Screenshot vs Audit Log */}
                <div className="flex items-center gap-1.5 p-1 bg-zinc-100/80 rounded-2xl border border-zinc-200/70 text-xs">
                  <button
                    type="button"
                    onClick={() => setActiveProofTab('video')}
                    className={`flex-1 py-2 rounded-xl font-semibold transition cursor-pointer flex items-center justify-center gap-1.5 ${
                      activeProofTab === 'video'
                        ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                        : 'text-zinc-500 hover:text-zinc-900'
                    }`}
                  >
                    <Video className="w-3.5 h-3.5 text-cyan-600" />
                    <span>720p HD Video</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveProofTab('screenshot')}
                    className={`flex-1 py-2 rounded-xl font-semibold transition cursor-pointer flex items-center justify-center gap-1.5 ${
                      activeProofTab === 'screenshot'
                        ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                        : 'text-zinc-500 hover:text-zinc-900'
                    }`}
                  >
                    <Camera className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Submission Receipt</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveProofTab('log')}
                    className={`flex-1 py-2 rounded-xl font-semibold transition cursor-pointer flex items-center justify-center gap-1.5 ${
                      activeProofTab === 'log'
                        ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                        : 'text-zinc-500 hover:text-zinc-900'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Investigation Log</span>
                  </button>
                </div>

                {/* Sub-tab 1: 720p Video Player */}
                {activeProofTab === 'video' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-zinc-700">720p Video Recording (1280x720)</span>
                        {selectedJob.proof_video_path && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            Ready
                          </span>
                        )}
                      </div>

                      {selectedJob.proof_video_path && (
                        <a
                          href={`/api/proofs?url=${encodeURIComponent(selectedJob.url)}&type=video&download=1`}
                          className="liquid-pill px-3 py-1 rounded-xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
                          download
                        >
                          <Download className="w-3.5 h-3.5 text-cyan-600" />
                          <span>Download .webm</span>
                        </a>
                      )}
                    </div>

                    {selectedJob.proof_video_path ? (
                      <div className="space-y-3">
                        <div className="relative rounded-2xl overflow-hidden bg-black/95 shadow-inner border border-zinc-300/80 aspect-video flex items-center justify-center">
                          <video
                            controls
                            preload="metadata"
                            className="w-full h-full object-contain"
                            src={`/api/proofs?url=${encodeURIComponent(selectedJob.url)}&type=video`}
                          >
                            Your browser does not support HTML5 video streaming.
                          </video>
                        </div>
                        <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 text-[11px] text-zinc-600 flex items-center justify-between gap-2">
                          <span className="font-mono truncate">{selectedJob.proof_video_path}</span>
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(selectedJob.proof_video_path);
                              setCopiedVideo(true);
                              setTimeout(() => setCopiedVideo(false), 2000);
                            }}
                            className="liquid-pill p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 shrink-0 cursor-pointer"
                            title="Copy local path"
                          >
                            {copiedVideo ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="p-12 text-center rounded-2xl bg-zinc-50 border border-dashed border-zinc-200 space-y-2">
                        <Video className="w-8 h-8 text-zinc-300 mx-auto" />
                        <p className="text-xs text-zinc-500 font-medium">
                          No 720p video file recorded for this previous submission.
                        </p>
                        <p className="text-[11px] text-zinc-400">
                          All new applications submitted from the dashboard automatically record 720p video proof.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Sub-tab 2: Confirmation Screenshot */}
                {activeProofTab === 'screenshot' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-zinc-700">DOM Confirmation Receipt</span>
                      {selectedJob.proof_screenshot_path && (
                        <a
                          href={`/api/proofs?url=${encodeURIComponent(selectedJob.url)}&type=screenshot&download=1`}
                          className="liquid-pill px-3 py-1 rounded-xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
                          download
                        >
                          <Download className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Download .png</span>
                        </a>
                      )}
                    </div>

                    {selectedJob.proof_screenshot_path ? (
                      <div className="space-y-3">
                        <div className="rounded-2xl overflow-hidden bg-white border border-zinc-200 shadow-sm max-h-[480px] overflow-y-auto">
                          <img
                            src={`/api/proofs?url=${encodeURIComponent(selectedJob.url)}&type=screenshot`}
                            alt="Application submission receipt"
                            className="w-full h-auto object-cover"
                          />
                        </div>
                        <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 text-[11px] text-zinc-600 flex items-center justify-between gap-2">
                          <span className="font-mono truncate">{selectedJob.proof_screenshot_path}</span>
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(selectedJob.proof_screenshot_path);
                              setCopiedScreenshot(true);
                              setTimeout(() => setCopiedScreenshot(false), 2000);
                            }}
                            className="liquid-pill p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 shrink-0 cursor-pointer"
                            title="Copy local path"
                          >
                            {copiedScreenshot ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="p-12 text-center rounded-2xl bg-zinc-50 border border-dashed border-zinc-200 space-y-2">
                        <Camera className="w-8 h-8 text-zinc-300 mx-auto" />
                        <p className="text-xs text-zinc-500 font-medium">
                          No screenshot receipt captured for this previous run.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Sub-tab 3: Step-by-Step Investigation Log */}
                {activeProofTab === 'log' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-indigo-600" />
                        <span className="text-xs font-bold text-zinc-700">Forensic Execution Audit Log</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <a
                          href={`/api/proofs?url=${encodeURIComponent(selectedJob.url)}&type=raw_log&download=1`}
                          className="liquid-pill px-3 py-1 rounded-xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
                          download
                        >
                          <Download className="w-3.5 h-3.5 text-indigo-600" />
                          <span>Download .log</span>
                        </a>
                      </div>
                    </div>

                    {loadingLog ? (
                      <div className="py-12 text-center text-xs text-zinc-400">Loading execution audit log...</div>
                    ) : logData ? (
                      <div className="space-y-4 text-xs">
                        {/* Summary Card */}
                        <div className="grid grid-cols-3 gap-2.5">
                          <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 text-center">
                            <span className="text-[10px] uppercase font-bold text-zinc-400 block">Total Duration</span>
                            <span className="font-mono font-bold text-zinc-800">{logData.total_duration_ms}ms</span>
                          </div>
                          <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 text-center">
                            <span className="text-[10px] uppercase font-bold text-zinc-400 block">Fields Autofilled</span>
                            <span className="font-mono font-bold text-zinc-800">{logData.fields_filled_count || logData.fields_filled?.length || 0}</span>
                          </div>
                          <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 text-center">
                            <span className="text-[10px] uppercase font-bold text-zinc-400 block">Q&A Resolved</span>
                            <span className="font-mono font-bold text-zinc-800">{logData.qa_count || logData.qa_resolutions?.length || 0}</span>
                          </div>
                        </div>

                        {/* Events Timeline */}
                        <div className="space-y-2">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 block">
                            Execution Events Timeline ({logData.events?.length || 0})
                          </span>
                          <div className="rounded-2xl bg-zinc-950 text-zinc-200 p-4 font-mono text-[11px] space-y-1.5 max-h-60 overflow-y-auto">
                            {logData.events && logData.events.length > 0 ? (
                              logData.events.map((ev: any, idx: number) => (
                                <div key={idx} className="flex items-start gap-2 leading-relaxed">
                                  <span className="text-zinc-500 shrink-0">+{ev.elapsed_ms}ms</span>
                                  <span className="text-cyan-400 shrink-0">[{ev.stage}]</span>
                                  <span className="text-zinc-300 break-all">{ev.message}</span>
                                </div>
                              ))
                            ) : (
                              <div className="text-zinc-500 italic">No timeline events recorded.</div>
                            )}
                          </div>
                        </div>

                        {/* Screening Q&A Breakdown */}
                        {logData.qa_resolutions && logData.qa_resolutions.length > 0 && (
                          <div className="space-y-2">
                            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 block">
                              Tier 1 Screening Q&A Resolutions
                            </span>
                            <div className="space-y-1.5 max-h-40 overflow-y-auto">
                              {logData.qa_resolutions.map((qa: any, idx: number) => (
                                <div key={idx} className="p-2.5 rounded-xl bg-white border border-zinc-200 text-[11px] space-y-1">
                                  <div className="font-semibold text-zinc-800">{qa.question}</div>
                                  <div className="flex items-center justify-between text-zinc-600">
                                    <span className="text-emerald-700 font-medium font-mono">Answer: {String(qa.answer)}</span>
                                    <span className="text-zinc-400 font-mono text-[10px]">Conf: {(qa.confidence * 100).toFixed(0)}%</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Browser Console Logs */}
                        {logData.browser_console && logData.browser_console.length > 0 && (
                          <div className="space-y-2">
                            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 block">
                              Browser Console Output
                            </span>
                            <div className="rounded-xl bg-zinc-900 text-zinc-400 p-3 font-mono text-[10px] space-y-1 max-h-36 overflow-y-auto">
                              {logData.browser_console.map((line: string, i: number) => (
                                <div key={i} className="truncate">{line}</div>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedJob.proof_log_path && (
                          <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 text-[11px] text-zinc-600 flex items-center justify-between gap-2">
                            <span className="font-mono truncate">{selectedJob.proof_log_path}</span>
                            <button
                              type="button"
                              onClick={() => {
                                navigator.clipboard.writeText(selectedJob.proof_log_path);
                                setCopiedLog(true);
                                setTimeout(() => setCopiedLog(false), 2000);
                              }}
                              className="liquid-pill p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 shrink-0 cursor-pointer"
                              title="Copy log path"
                            >
                              {copiedLog ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="p-12 text-center rounded-2xl bg-zinc-50 border border-dashed border-zinc-200 space-y-2">
                        <Terminal className="w-8 h-8 text-zinc-300 mx-auto" />
                        <p className="text-xs text-zinc-500 font-medium">
                          No audit log recorded for this previous submission.
                        </p>
                        <p className="text-[11px] text-zinc-400">
                          ApplyPilot captures full event timelines, field autofill receipts, and browser logs for every new run.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="liquid-glass rounded-3xl p-12 text-center border border-white/90 shadow-sm space-y-3">
                <Video className="w-10 h-10 text-zinc-300 mx-auto" />
                <h3 className="text-sm font-bold text-zinc-800">Select an Application</h3>
                <p className="text-xs text-zinc-500 max-w-sm mx-auto">
                  Click any application in the list on the left to watch its 720p HD video proof, inspect the confirmation screenshot, and examine the execution audit log.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
