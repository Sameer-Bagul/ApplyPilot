'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  ExternalLink,
  Briefcase,
  Building2,
  MapPin,
  DollarSign,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Save,
  Trash2,
  Sparkles,
  Users,
  Shield,
  Layers,
  ArrowRight,
  Clock,
  Send,
  Play,
  Monitor,
  ShieldAlert,
  Video,
  Camera,
  Download,
  Copy,
  Check,
  FileText,
  Terminal,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Target,
  Globe,
  Award,
  Zap,
} from 'lucide-react';
import { RouteBadge } from './ui/RouteBadge';

interface JobDetailDrawerProps {
  jobUrl: string | null;
  onClose: () => void;
  onJobUpdated?: () => void;
  onOpenLead?: (lead: any) => void;
  onOpenTicket?: (ticketId: number) => void;
}

export function JobDetailDrawer({
  jobUrl,
  onClose,
  onJobUpdated,
  onOpenLead,
  onOpenTicket,
}: JobDetailDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'description' | 'scoring' | 'leads' | 'proof' | 'edit'>('description');
  const [copiedVideo, setCopiedVideo] = useState(false);
  const [copiedScreenshot, setCopiedScreenshot] = useState(false);
  const [copiedLog, setCopiedLog] = useState(false);
  const [proofLog, setProofLog] = useState<any | null>(null);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  
  // Application runner state (Phase 2)
  const [applyingMode, setApplyingMode] = useState<'assist' | 'auto_verify' | 'headed' | 'headless' | null>(null);
  const [applyResult, setApplyResult] = useState<{ status: string; message: string; ticket_id?: number } | null>(null);
  const [reverting, setReverting] = useState(false);
  
  // Editable form fields
  const [editState, setEditState] = useState('');
  const [editFitScore, setEditFitScore] = useState<number>(0);
  const [editRoute, setEditRoute] = useState('');
  const [editSalary, setEditSalary] = useState('');
  const [editLocation, setEditLocation] = useState('');
  const [editReasoning, setEditReasoning] = useState('');

  const handleApply = async (mode: 'assist' | 'auto_verify' | 'headed' | 'headless') => {
    if (!jobUrl) return;
    setApplyingMode(mode);
    setApplyResult(null);
    try {
      const isAssist = mode === 'assist' || mode === 'headed';
      const executionMode = mode === 'assist' ? 'assist' : (mode === 'auto_verify' ? 'auto_verify' : undefined);
      const res = await fetch('/api/apply/job', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jobUrl,
          headless: !isAssist,
          mode: executionMode,
          auto_submit: !isAssist,
        }),
      });
      const resJson = await res.json();
      if (resJson.success) {
        const statusVal = resJson.status || resJson.data?.status || 'applied';
        const messageVal = resJson.message || resJson.data?.message || (statusVal === 'applied' ? 'Application submitted successfully!' : 'Application requires human review or verification.');
        const ticketIdVal = resJson.ticket_id || resJson.data?.ticket_id;
        setApplyResult({
          status: statusVal,
          message: messageVal,
          ticket_id: ticketIdVal,
        });
        if (onJobUpdated) onJobUpdated();
      } else {
        setApplyResult({
          status: 'error',
          message: resJson.error || 'Failed to trigger application run.',
        });
      }
    } catch (err: any) {
      setApplyResult({
        status: 'error',
        message: err.message || 'Network error triggering application run.',
      });
    } finally {
      setApplyingMode(null);
    }
  };

  const handleRevert = async () => {
    if (!jobUrl) return;
    if (!confirm('Mark this job as Not Applied? This will restore it to Ready to Apply for re-submission.')) return;
    setReverting(true);
    try {
      const res = await fetch('/api/jobs/revert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jobUrl }),
      });
      const resJson = await res.json();
      if (resJson.success) {
        setData((prev: any) => prev ? ({
          ...prev,
          job: {
            ...prev.job,
            state: 'ready_to_apply',
            apply_status: 'ready_to_apply',
            needs_human_reason: 'reverted_by_user_proof_inspected',
          },
        }) : prev);
        setEditState('ready_to_apply');
        if (onJobUpdated) onJobUpdated();
      } else {
        alert(resJson.error || 'Failed to revert job.');
      }
    } catch (err: any) {
      alert(err.message || 'Error reverting job.');
    } finally {
      setReverting(false);
    }
  };

  useEffect(() => {
    if (!jobUrl) {
      setData(null);
      return;
    }

    const fetchDetail = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/jobs/detail?url=${encodeURIComponent(jobUrl)}`);
        const json = await res.json();
        if (json.success) {
          setData(json.data);
          const j = json.data.job;
          setEditState(j.state || 'discovered');
          setEditFitScore(j.fit_score ?? 0);
          setEditRoute(j.execution_route || 'PORTAL_ONLY');
          setEditSalary(j.salary_raw || '');
          setEditLocation(j.location || '');
          setEditReasoning(j.match_reasoning || '');
        }
      } catch (err) {
        console.error('Failed to load job detail', err);
      } finally {
        setLoading(false);
      }
    };

    const fetchProofLog = async () => {
      try {
        const res = await fetch(`/api/proofs?url=${encodeURIComponent(jobUrl)}&type=log`);
        const json = await res.json();
        if (json.success && json.log) {
          setProofLog(json.log);
        } else {
          setProofLog(null);
        }
      } catch {
        setProofLog(null);
      }
    };

    fetchDetail();
    fetchProofLog();
  }, [jobUrl]);

  if (!jobUrl) return null;

  const job = data?.job;
  const company = data?.company;
  const leads = data?.leads || [];

  const metadata = React.useMemo(() => {
    if (!job?.metadata_json) return null;
    try {
      return typeof job.metadata_json === 'string' ? JSON.parse(job.metadata_json) : job.metadata_json;
    } catch {
      return null;
    }
  }, [job?.metadata_json]);

  const resumeMatch = metadata?.resume_match;
  const matchPct = resumeMatch?.match_percentage ?? (job?.fit_score != null ? Math.round(job.fit_score * 10) : null);
  const matchedSkills: string[] = resumeMatch?.matched_skills || metadata?.tech_stack || [];
  const missingSkills: string[] = resumeMatch?.missing_skills || [];
  const workplaceType: string = metadata?.workplace_type || (job?.location?.toLowerCase().includes('remote') ? 'Remote' : (job?.location?.toLowerCase().includes('hybrid') ? 'Hybrid' : 'Onsite'));
  const roleCategory: string = metadata?.role_category || 'SOFTWARE_ENGINEERING';
  const minExp = metadata?.min_experience_years;
  const maxExp = metadata?.max_experience_years;

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`/api/jobs/detail?url=${encodeURIComponent(jobUrl)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state: editState,
          fit_score: editFitScore,
          execution_route: editRoute,
          salary_raw: editSalary,
          location: editLocation,
          match_reasoning: editReasoning,
        }),
      });
      const resJson = await res.json();
      if (resJson.success) {
        setData((prev: any) => ({
          ...prev,
          job: {
            ...prev.job,
            state: editState,
            fit_score: editFitScore,
            execution_route: editRoute,
            salary_raw: editSalary,
            location: editLocation,
            match_reasoning: editReasoning,
          },
        }));
        if (onJobUpdated) onJobUpdated();
      }
    } catch (err) {
      console.error('Failed to update job', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!jobUrl) return;
    if (!confirm('Are you sure you want to delete this job record?')) return;
    try {
      const res = await fetch(`/api/jobs/detail?url=${encodeURIComponent(jobUrl)}`, {
        method: 'DELETE',
      });
      const resJson = await res.json();
      if (resJson.success) {
        if (onJobUpdated) onJobUpdated();
        onClose();
      }
    } catch (err) {
      console.error('Failed to delete job', err);
    }
  };

  const getScoreBadgeClass = (score: number | null | undefined) => {
    if (score == null) return 'text-zinc-600 bg-zinc-100 border-zinc-200';
    if (score >= 8) return 'text-emerald-800 bg-emerald-50 border-emerald-200 shadow-xs';
    if (score >= 5) return 'text-amber-800 bg-amber-50 border-amber-200 shadow-xs';
    return 'text-rose-800 bg-rose-50 border-rose-200 shadow-xs';
  };

  return (
    <div 
      className="fixed inset-0 z-50 overflow-hidden bg-slate-900/25 backdrop-blur-md flex justify-end animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-3xl h-full liquid-glass-elevated bg-white/95 backdrop-blur-2xl border-l border-white/80 shadow-2xl flex flex-col relative text-zinc-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="p-6 border-b border-zinc-200/70 bg-white/70 flex items-start justify-between gap-4 relative">
          <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />
          
          <div className="space-y-2 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              {job && <RouteBadge route={job.execution_route || 'PORTAL_ONLY'} />}
              {job && (
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getScoreBadgeClass(job.fit_score)}`}>
                  Fit Score: {job.fit_score ?? 'Unscored'}/10
                </span>
              )}
              {job?.state && (
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                  job.state === 'submission_unconfirmed'
                    ? 'bg-amber-100 text-amber-900 border-amber-300 font-bold'
                    : job.state === 'applied'
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200 font-semibold'
                    : 'bg-zinc-100 text-zinc-700 border-zinc-200'
                }`}>
                  {job.state === 'submission_unconfirmed' ? '⚠️ Unconfirmed Submission' : job.state}
                </span>
              )}
              {(job?.state === 'applied' || job?.apply_status === 'applied' || job?.state === 'submission_unconfirmed') && (
                <button
                  type="button"
                  disabled={reverting}
                  onClick={handleRevert}
                  className="px-2.5 py-0.5 rounded-full text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition flex items-center gap-1 shadow-2xs cursor-pointer disabled:opacity-50"
                  title="Mark as Not Applied: restores state to Ready to Apply if review of proof shows incomplete submission"
                >
                  <RotateCcw className={`w-3 h-3 ${reverting ? 'animate-spin' : ''}`} />
                  <span>{reverting ? 'Reverting...' : 'Mark as Not Applied'}</span>
                </button>
              )}
            </div>
            <h2 className="text-xl font-bold tracking-tight text-zinc-900 truncate">
              {job?.title || 'Job Detail'}
            </h2>
            <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-500">
              <span className="flex items-center gap-1.5 font-medium text-zinc-800">
                <Building2 className="w-3.5 h-3.5 text-cyan-600" />
                {job?.company || 'Company'}
              </span>
              <span className="flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                {job?.location || 'Remote'}
              </span>
              {job?.salary_raw && (
                <span className="flex items-center gap-1.5 text-emerald-700 font-medium">
                  <DollarSign className="w-3.5 h-3.5" />
                  {job.salary_raw}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {job?.url && (
              <a
                href={job.url}
                target="_blank"
                rel="noreferrer"
                className="liquid-pill rounded-full p-2 text-zinc-600 hover:text-zinc-950 transition shadow-2xs"
                title="Open Official Job Board Posting"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
            <button
              onClick={onClose}
              className="liquid-pill rounded-full p-2 text-zinc-600 hover:text-zinc-950 transition shadow-2xs"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Resume Match Intelligence Banner */}
        {matchPct != null && (
          <div className="mx-6 mt-4 p-4 rounded-2xl border border-emerald-200/80 bg-gradient-to-r from-emerald-500/10 via-teal-500/5 to-cyan-500/10 flex items-center justify-between gap-4 shadow-2xs">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-12 h-12 rounded-2xl bg-emerald-600 text-white flex flex-col items-center justify-center font-bold shrink-0 shadow-sm">
                <span className="text-base leading-none">{matchPct}%</span>
                <span className="text-[9px] uppercase tracking-wider font-semibold opacity-90">Match</span>
              </div>
              <div className="space-y-0.5 min-w-0">
                <div className="text-xs font-bold text-zinc-900 flex items-center gap-1.5 flex-wrap">
                  <span>Candidate: Sameer Bagul (2.5y AI / Fullstack)</span>
                  {resumeMatch?.experience_match && (
                    <span className="text-[10px] px-2 py-0.2 rounded-full font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                      {resumeMatch.experience_match === 'MATCH' ? '✓ Ideal Experience Fit (2.5y)' : resumeMatch.experience_match}
                    </span>
                  )}
                  {workplaceType && (
                    <span className="text-[10px] px-2 py-0.2 rounded-full font-semibold bg-cyan-100 text-cyan-800 border border-cyan-200">
                      {workplaceType === 'Remote' ? '🌐 Remote' : workplaceType}
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-zinc-600 line-clamp-1">
                  {resumeMatch?.reasoning || `Algorithmic fit score ${job?.fit_score}/10 based on role relevance, tech stack, and experience.`}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setActiveTab('scoring')}
                className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-white/90 text-emerald-900 border border-emerald-200 hover:bg-white hover:border-emerald-300 transition shadow-2xs flex items-center gap-1 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                <span>Score Breakdown</span>
              </button>
            </div>
          </div>
        )}

        {/* Tab Navigation Pill Bar */}
        <div className="flex items-center gap-1 px-6 py-2.5 border-b border-zinc-200/60 bg-zinc-50/70 text-xs">
          <button
            onClick={() => setActiveTab('description')}
            className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all cursor-pointer ${
              activeTab === 'description'
                ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900'
            }`}
          >
            Description & Overview
          </button>
          <button
            onClick={() => setActiveTab('scoring')}
            className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all cursor-pointer ${
              activeTab === 'scoring'
                ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900'
            }`}
          >
            Match Reasoning
          </button>
          <button
            onClick={() => setActiveTab('leads')}
            className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'leads'
                ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900'
            }`}
          >
            <span>Recruiter Contacts</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-zinc-200/80 text-zinc-700">
              {leads.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('proof')}
            className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'proof'
                ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900'
            }`}
          >
            <Video className="w-3.5 h-3.5 text-cyan-600" />
            <span>Submission Proof</span>
            {(job?.proof_video_path || job?.proof_screenshot_path) && (
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
            )}
          </button>
          <button
            onClick={() => setActiveTab('edit')}
            className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all cursor-pointer ${
              activeTab === 'edit'
                ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900'
            }`}
          >
            Edit Record
          </button>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-20 text-center text-sm text-zinc-400">Loading job details...</div>
          ) : (
            <>
              {activeTab === 'description' && (
                <div className="space-y-6">
                  {/* Metadata Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="liquid-glass rounded-2xl p-3 border border-white/90 shadow-2xs">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block">State</span>
                      <span className="text-sm font-bold text-zinc-900 capitalize">{job?.state || 'discovered'}</span>
                    </div>
                    <div className="liquid-glass rounded-2xl p-3 border border-white/90 shadow-2xs">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block">Route</span>
                      <span className="text-sm font-bold text-cyan-700">{job?.execution_route || 'PORTAL_ONLY'}</span>
                    </div>
                    <div className="liquid-glass rounded-2xl p-3 border border-white/90 shadow-2xs">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block">ATS Origin</span>
                      <span className="text-sm font-bold text-zinc-900 capitalize">{job?.ats_provider || 'Direct'}</span>
                    </div>
                    <div className="liquid-glass rounded-2xl p-3 border border-white/90 shadow-2xs">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block">Discovered</span>
                      <span className="text-xs font-medium text-zinc-700">{job?.discovered_at ? new Date(job.discovered_at).toLocaleDateString() : 'Recent'}</span>
                    </div>
                  </div>

                  {/* Job Specification Chips */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="px-3 py-1 rounded-xl bg-purple-50 text-purple-800 border border-purple-200/80 font-semibold flex items-center gap-1.5 shadow-2xs">
                      <Briefcase className="w-3.5 h-3.5 text-purple-600" />
                      <span>Role: {roleCategory.replace('_', ' ')}</span>
                    </span>
                    <span className="px-3 py-1 rounded-xl bg-cyan-50 text-cyan-800 border border-cyan-200/80 font-semibold flex items-center gap-1.5 shadow-2xs">
                      <Globe className="w-3.5 h-3.5 text-cyan-600" />
                      <span>Workplace: {workplaceType}</span>
                    </span>
                    {(minExp != null || maxExp != null) && (
                      <span className="px-3 py-1 rounded-xl bg-blue-50 text-blue-800 border border-blue-200/80 font-semibold flex items-center gap-1.5 shadow-2xs">
                        <Award className="w-3.5 h-3.5 text-blue-600" />
                        <span>Experience: {minExp ? `${minExp}${maxExp ? `-${maxExp}` : '+'} yrs` : `<${maxExp} yrs`}</span>
                      </span>
                    )}
                  </div>

                  {/* Matched & Required Tech Stack */}
                  {matchedSkills.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-zinc-500 block">
                        Matched Technologies ({matchedSkills.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {matchedSkills.map((tech) => (
                          <span
                            key={tech}
                            className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-white text-zinc-800 border border-zinc-200/90 shadow-2xs flex items-center gap-1"
                          >
                            <Check className="w-3 h-3 text-emerald-600 stroke-[3]" />
                            <span>{tech}</span>
                          </span>
                        ))}
                        {missingSkills.map((tech) => (
                          <span
                            key={tech}
                            className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-zinc-50 text-zinc-500 border border-dashed border-zinc-300 flex items-center gap-1"
                            title="Bonus or missing requirement"
                          >
                            <span>{tech}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Company Snapshot */}
                  {company && (
                    <div className="liquid-glass rounded-2xl p-4 border border-white/90 shadow-2xs space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                          <Building2 className="w-3.5 h-3.5 text-cyan-600" />
                          Company Intelligence
                        </span>
                        {company.is_vip === 1 && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                            VIP Target
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-zinc-600 grid grid-cols-2 gap-2 pt-1">
                        <div>Domain: <span className="font-mono text-zinc-900 font-semibold">{company.official_domain || 'N/A'}</span></div>
                        <div>Sector: <span className="text-zinc-900 font-semibold">{company.sector || 'Technology'}</span></div>
                        <div>Priority Tier: <span className="text-zinc-900 font-semibold">Tier {company.priority_tier || 2}</span></div>
                        <div>ATS Provider: <span className="text-zinc-900 font-semibold">{company.ats_provider || 'Custom'}</span></div>
                      </div>
                    </div>
                  )}

                  {/* Raw or Clean Description */}
                  <div className="space-y-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-500 block">
                      Role Description & Requirements
                    </span>
                    <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs text-xs text-zinc-700 leading-relaxed max-h-96 overflow-y-auto whitespace-pre-line bg-white/70">
                      {job?.description || 'No detailed description ingested yet. The job was harvested directly via ATS API.'}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'scoring' && (
                <div className="space-y-4">
                  <div className="liquid-glass-elevated rounded-2xl p-5 border border-white/90 shadow-xs space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Target className="w-5 h-5 text-emerald-600" />
                        <span className="text-sm font-bold text-zinc-900">
                          Candidate Resume Match Analysis
                        </span>
                      </div>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${getScoreBadgeClass(job?.fit_score)}`}>
                        {matchPct != null ? `${matchPct}% Match (${job?.fit_score ?? 0}/10)` : `${job?.fit_score ?? 0} / 10`}
                      </span>
                    </div>

                    {/* Candidate Comparison Banner */}
                    <div className="p-3.5 rounded-xl bg-white/90 border border-zinc-200/80 shadow-2xs space-y-2">
                      <div className="text-xs font-bold text-zinc-900 flex items-center justify-between">
                        <span>Evaluated Candidate Profile</span>
                        <span className="text-emerald-700 font-mono text-[11px] font-semibold">Sameer Bagul (2.5y Exp)</span>
                      </div>
                      <p className="text-xs text-zinc-600 leading-relaxed">
                        {resumeMatch?.reasoning || job?.match_reasoning || 'Algorithmic 4-factor scoring pass evaluating role alignment, tech matrix, experience, and remote/location authorization.'}
                      </p>
                    </div>

                    {/* Matched vs Missing Skills Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                      <div className="p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-200/70 space-y-2">
                        <span className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-700 stroke-[3]" />
                          Matched Skills ({matchedSkills.length})
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {matchedSkills.length > 0 ? (
                            matchedSkills.map((s) => (
                              <span key={s} className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-white text-emerald-800 border border-emerald-200 shadow-2xs">
                                {s}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-zinc-400 italic">No specific tech tokens parsed.</span>
                          )}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-xl bg-zinc-50 border border-zinc-200 space-y-2">
                        <span className="text-xs font-bold text-zinc-700 flex items-center gap-1.5">
                          <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                          Missing / Bonus Reqs ({missingSkills.length})
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {missingSkills.length > 0 ? (
                            missingSkills.map((s) => (
                              <span key={s} className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-white text-zinc-600 border border-zinc-200">
                                {s}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-emerald-700 font-medium">None! All detected skills matched.</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* 4-Factor Breakdown */}
                    <div className="space-y-2 pt-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-zinc-500 block">
                        4-Factor Deterministic Breakdown
                      </span>
                      <div className="grid grid-cols-2 gap-2.5 text-[11px] text-zinc-600">
                        <div className="p-2.5 rounded-xl bg-white/80 border border-zinc-200/60">
                          <span className="font-semibold block text-zinc-800">Factor 1: Role Relevance</span>
                          <span>Software/AI title matching & non-tech rejection (0-4 pts)</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-white/80 border border-zinc-200/60">
                          <span className="font-semibold block text-zinc-800">Factor 2: Tech Matrix</span>
                          <span>Python, TypeScript, React, Next.js, AI Agents (0-3 pts)</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-white/80 border border-zinc-200/60">
                          <span className="font-semibold block text-zinc-800">Factor 3: Seniority Fit</span>
                          <span>Targeting 2.5y sweet spot (Mid-level 1-4y) (0-2 pts)</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-white/80 border border-zinc-200/60">
                          <span className="font-semibold block text-zinc-800">Factor 4: Location & Remote</span>
                          <span>Remote first, hybrid, or India tech hubs (0-1 pt)</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'leads' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                      Discovered Recruiter Contacts for {job?.company}
                    </span>
                    <span className="text-xs text-zinc-500">{leads.length} found</span>
                  </div>

                  {leads.length === 0 ? (
                    <div className="py-12 text-center text-xs text-zinc-500 liquid-glass rounded-2xl p-6">
                      No recruiter contacts associated with this job yet. 
                      Run the free email harvester to discover verified leads.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {leads.map((l: any) => (
                        <div
                          key={l.lead_id}
                          onClick={() => onOpenLead && onOpenLead(l)}
                          className="liquid-row rounded-2xl p-3.5 flex items-center justify-between gap-3 cursor-pointer group"
                        >
                          <div className="space-y-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-xs text-zinc-900 group-hover:text-cyan-700 transition">
                                {l.contact_name || 'Hiring Manager'}
                              </span>
                              <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-zinc-100 text-zinc-600 border border-zinc-200">
                                {l.contact_type}
                              </span>
                              <span className={`text-[10px] px-2 py-0.2 rounded-full font-semibold border ${
                                l.outreach_status === 'approved' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                                l.outreach_status === 'sent' ? 'bg-cyan-50 text-cyan-800 border-cyan-200' :
                                'bg-amber-50 text-amber-800 border-amber-200'
                              }`}>
                                {l.outreach_status}
                              </span>
                            </div>
                            <div className="text-xs text-zinc-500 font-mono truncate">{l.contact_email}</div>
                          </div>

                          <ArrowRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 group-hover:text-zinc-900 transition" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'proof' && (
                <div className="space-y-6">
                  {/* Proof Overview Card */}
                  <div className="liquid-glass-elevated rounded-2xl p-5 border border-white/90 shadow-xs space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Video className="w-5 h-5 text-cyan-600" />
                        <span className="text-sm font-bold text-zinc-900">
                          Application Verification Proof
                        </span>
                      </div>
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                        job?.proof_video_path || job?.proof_screenshot_path
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : 'bg-zinc-100 text-zinc-600 border-zinc-200'
                      }`}>
                        {job?.proof_video_path && job?.proof_screenshot_path
                          ? '720p HD Video & Screenshot Saved'
                          : job?.proof_video_path
                          ? '720p HD Video Saved'
                          : job?.proof_screenshot_path
                          ? 'Screenshot Saved'
                          : 'No Proof Recorded Yet'}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-600 leading-relaxed">
                      ApplyPilot records a 720p (1280x720) video of the browser filling and submitting the application form, alongside a full-page confirmation screenshot saved directly to local storage on your device.
                    </p>
                  </div>

                  {/* 720p Video Recording Section */}
                  <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Monitor className="w-4 h-4 text-indigo-600" />
                        <span className="text-xs font-bold uppercase tracking-wider text-zinc-700">
                          720p Video Recording (.webm)
                        </span>
                      </div>
                      {job?.proof_video_path && (
                        <a
                          href={`/api/proofs/video?url=${encodeURIComponent(jobUrl)}&download=1`}
                          className="liquid-pill px-3 py-1 rounded-xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
                          download
                        >
                          <Download className="w-3.5 h-3.5 text-cyan-600" />
                          <span>Download .webm</span>
                        </a>
                      )}
                    </div>

                    {job?.proof_video_path ? (
                      <div className="space-y-3">
                        <div className="relative rounded-2xl overflow-hidden bg-black/95 shadow-inner border border-zinc-300/80 aspect-video flex items-center justify-center">
                          <video
                            controls
                            preload="metadata"
                            className="w-full h-full object-contain"
                            src={`/api/proofs/video?url=${encodeURIComponent(jobUrl)}`}
                          >
                            Your browser does not support HTML5 video streaming.
                          </video>
                        </div>
                        <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 text-[11px] text-zinc-600 flex items-center justify-between gap-2">
                          <span className="font-mono truncate">{job.proof_video_path}</span>
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(job.proof_video_path);
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
                      <div className="p-8 text-center rounded-2xl bg-zinc-50/80 border border-dashed border-zinc-200 space-y-2">
                        <Video className="w-8 h-8 text-zinc-300 mx-auto" />
                        <p className="text-xs text-zinc-500 font-medium">
                          No 720p video recorded yet for this role.
                        </p>
                        <p className="text-[11px] text-zinc-400">
                          Click "Apply Headed" or "Apply Headless" below to execute an autonomous application with 720p video recording.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Screenshot Confirmation Receipt Section */}
                  <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-4">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <Camera className="w-4 h-4 text-emerald-600" />
                        <span className="text-xs font-bold uppercase tracking-wider text-zinc-700">
                          Confirmation Screenshot Receipt (.png)
                        </span>
                      </div>
                      {job?.proof_screenshot_path && (
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setZoomLevel(1);
                              setLightboxOpen(true);
                            }}
                            className="liquid-pill px-3 py-1 rounded-xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
                          >
                            <Maximize2 className="w-3.5 h-3.5 text-purple-600" />
                            <span>Zoom & Inspect</span>
                          </button>
                          <a
                            href={`/api/proofs?url=${encodeURIComponent(jobUrl)}&type=screenshot`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="liquid-pill px-3 py-1 rounded-xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
                          >
                            <ExternalLink className="w-3.5 h-3.5 text-cyan-600" />
                            <span>Open in New Tab</span>
                          </a>
                          <a
                            href={`/api/proofs?url=${encodeURIComponent(jobUrl)}&type=screenshot&download=1`}
                            className="liquid-pill px-3 py-1 rounded-xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
                            download
                          >
                            <Download className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Download .png</span>
                          </a>
                        </div>
                      )}
                    </div>

                    {job?.proof_screenshot_path ? (
                      <div className="space-y-3">
                        <div 
                          onClick={() => {
                            setZoomLevel(1);
                            setLightboxOpen(true);
                          }}
                          className="rounded-2xl overflow-hidden bg-zinc-900/5 border border-zinc-200 shadow-sm max-h-[480px] overflow-y-auto cursor-zoom-in group relative"
                        >
                          <img
                            src={`/api/proofs?url=${encodeURIComponent(jobUrl)}&type=screenshot`}
                            alt="Application submission confirmation receipt"
                            className="w-full h-auto object-contain block transition group-hover:opacity-95"
                          />
                          <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition bg-zinc-900/80 text-white px-2.5 py-1 rounded-lg text-[11px] font-medium flex items-center gap-1.5 shadow-md pointer-events-none backdrop-blur-xs">
                            <Maximize2 className="w-3 h-3 text-cyan-300" />
                            <span>Click to Zoom (Crystal Clear)</span>
                          </div>
                        </div>
                        <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 text-[11px] text-zinc-600 flex items-center justify-between gap-2">
                          <span className="font-mono truncate">{job.proof_screenshot_path}</span>
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(job.proof_screenshot_path);
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
                      <div className="p-8 text-center rounded-2xl bg-zinc-50/80 border border-dashed border-zinc-200 space-y-2">
                        <Camera className="w-8 h-8 text-zinc-300 mx-auto" />
                        <p className="text-xs text-zinc-500 font-medium">
                          No screenshot receipt captured yet.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Forensic Execution Audit Log Section */}
                  <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-indigo-600" />
                        <span className="text-xs font-bold uppercase tracking-wider text-zinc-700">
                          Forensic Execution Audit Log
                        </span>
                      </div>
                      <a
                        href={`/api/proofs?url=${encodeURIComponent(jobUrl)}&type=raw_log&download=1`}
                        className="liquid-pill px-3 py-1 rounded-xl text-xs font-semibold text-zinc-700 hover:text-zinc-950 flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
                        download
                      >
                        <Download className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Download .log</span>
                      </a>
                    </div>

                    {proofLog ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-3 gap-2 text-center text-xs">
                          <div className="p-2.5 rounded-xl bg-zinc-50 border border-zinc-200/60">
                            <span className="text-[10px] uppercase font-bold text-zinc-400 block">Duration</span>
                            <span className="font-mono font-bold text-zinc-800">{proofLog.total_duration_ms}ms</span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-zinc-50 border border-zinc-200/60">
                            <span className="text-[10px] uppercase font-bold text-zinc-400 block">Fields Filled</span>
                            <span className="font-mono font-bold text-zinc-800">{proofLog.fields_filled_count || proofLog.fields_filled?.length || 0}</span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-zinc-50 border border-zinc-200/60">
                            <span className="text-[10px] uppercase font-bold text-zinc-400 block">Q&A Resolved</span>
                            <span className="font-mono font-bold text-zinc-800">{proofLog.qa_count || proofLog.qa_resolutions?.length || 0}</span>
                          </div>
                        </div>

                        <div className="rounded-2xl bg-zinc-950 text-zinc-200 p-4 font-mono text-[11px] space-y-1.5 max-h-48 overflow-y-auto">
                          {proofLog.events?.map((ev: any, idx: number) => (
                            <div key={idx} className="flex items-start gap-2 leading-relaxed">
                              <span className="text-zinc-500 shrink-0">+{ev.elapsed_ms}ms</span>
                              <span className="text-cyan-400 shrink-0">[{ev.stage}]</span>
                              <span className="text-zinc-300 break-all">{ev.message}</span>
                            </div>
                          ))}
                        </div>

                        {job?.proof_log_path && (
                          <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 text-[11px] text-zinc-600 flex items-center justify-between gap-2">
                            <span className="font-mono truncate">{job.proof_log_path}</span>
                            <button
                              type="button"
                              onClick={() => {
                                navigator.clipboard.writeText(job.proof_log_path);
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
                      <div className="p-8 text-center rounded-2xl bg-zinc-50/80 border border-dashed border-zinc-200 space-y-2">
                        <Terminal className="w-8 h-8 text-zinc-300 mx-auto" />
                        <p className="text-xs text-zinc-500 font-medium">
                          No audit log recorded yet for this role.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'edit' && (
                <div className="space-y-4">
                  <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-700">
                      Edit Listing Details
                    </h3>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-zinc-600 block mb-1">State</label>
                        <select
                          value={editState}
                          onChange={(e) => setEditState(e.target.value)}
                          className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                        >
                          <option value="discovered">Discovered</option>
                          <option value="enriching">Enriching</option>
                          <option value="scored">Scored</option>
                          <option value="ready_to_apply">Ready to Apply</option>
                          <option value="applied">Applied</option>
                          <option value="submission_unconfirmed">Submission Unconfirmed</option>
                          <option value="rejected">Rejected</option>
                          <option value="dead">Dead (Closed)</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-xs font-semibold text-zinc-600 block mb-1">Execution Route</label>
                        <select
                          value={editRoute}
                          onChange={(e) => setEditRoute(e.target.value)}
                          className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                        >
                          <option value="DUAL_ATTACK">DUAL_ATTACK (Portal + Email)</option>
                          <option value="PORTAL_ONLY">PORTAL_ONLY</option>
                          <option value="EMAIL_ONLY">EMAIL_ONLY</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-zinc-600 block mb-1">Fit Score (0 - 10)</label>
                        <input
                          type="number"
                          min="0"
                          max="10"
                          value={editFitScore}
                          onChange={(e) => setEditFitScore(Number(e.target.value))}
                          className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs font-mono"
                        />
                      </div>

                      <div>
                        <label className="text-xs font-semibold text-zinc-600 block mb-1">Salary Raw</label>
                        <input
                          type="text"
                          value={editSalary}
                          onChange={(e) => setEditSalary(e.target.value)}
                          placeholder="$160,000 - $210,000"
                          className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-600 block mb-1">Location</label>
                      <input
                        type="text"
                        value={editLocation}
                        onChange={(e) => setEditLocation(e.target.value)}
                        placeholder="Remote / Bengaluru"
                        className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-600 block mb-1">Match Reasoning</label>
                      <textarea
                        rows={3}
                        value={editReasoning}
                        onChange={(e) => setEditReasoning(e.target.value)}
                        className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                      />
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-zinc-200/70">
                      <button
                        onClick={handleDelete}
                        type="button"
                        className="px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition flex items-center gap-1.5 cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete Job
                      </button>

                      <button
                        onClick={handleSave}
                        disabled={saving}
                        type="button"
                        className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
                      >
                        <Save className="w-3.5 h-3.5" />
                        {saving ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Phase 2: Action Bar for Autonomous Application */}
        <div className="p-4 border-t border-zinc-200/80 bg-white/80 backdrop-blur-md space-y-3">
          {applyResult && (
            <div className={`p-3 rounded-2xl text-xs flex items-center justify-between gap-3 border shadow-2xs ${
              applyResult.status === 'applied'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : applyResult.status === 'needs_human' || applyResult.ticket_id
                ? 'bg-amber-50 border-amber-200 text-amber-900'
                : 'bg-rose-50 border-rose-200 text-rose-900'
            }`}>
              <div className="flex items-center gap-2 min-w-0">
                {applyResult.status === 'applied' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                ) : applyResult.status === 'needs_human' || applyResult.ticket_id ? (
                  <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                )}
                <span className="truncate">{applyResult.message}</span>
              </div>

              {applyResult.ticket_id && onOpenTicket && (
                <button
                  type="button"
                  onClick={() => onOpenTicket(applyResult.ticket_id!)}
                  className="px-3 py-1 rounded-xl text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white shadow-xs shrink-0 cursor-pointer transition flex items-center gap-1.5"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Open HITL Ticket #{applyResult.ticket_id}
                </button>
              )}
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            <div className="text-xs text-zinc-500">
              <span className="font-semibold text-zinc-800 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-zinc-600" />
                Direct Application
              </span>
              <span className="text-[11px] text-zinc-400">Autofill with candidate profile and tailored resume</span>
            </div>

            <div className="flex items-center gap-2 flex-wrap justify-end">
              {(job?.state === 'applied' || job?.apply_status === 'applied' || job?.state === 'submission_unconfirmed') && (
                <button
                  type="button"
                  disabled={reverting}
                  onClick={handleRevert}
                  className="px-3 py-2 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition flex items-center gap-1.5 shadow-2xs cursor-pointer disabled:opacity-50 mr-1"
                  title="Mark as Not Applied: restores state to Ready to Apply for re-submission"
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${reverting ? 'animate-spin' : ''}`} />
                  <span>{reverting ? 'Reverting...' : 'Mark as Not Applied'}</span>
                </button>
              )}

              <button
                type="button"
                disabled={applyingMode !== null}
                onClick={() => handleApply('assist')}
                className="liquid-pill px-3.5 py-2 rounded-xl text-xs font-semibold text-indigo-700 bg-indigo-50/60 hover:bg-indigo-100/80 border border-indigo-200/80 flex items-center gap-1.5 cursor-pointer shadow-2xs transition disabled:opacity-50"
                title="Assist Mode: Natural human typing, fills details, attaches resume, chimes & pauses on Hyprland Workspace 11 for you to solve CAPTCHA & submit"
              >
                <Monitor className="w-3.5 h-3.5 text-indigo-600" />
                {applyingMode === 'assist' ? 'Running Assist...' : 'Assist Mode (Fill & Review)'}
              </button>

              <button
                type="button"
                disabled={applyingMode !== null}
                onClick={() => handleApply('auto_verify')}
                className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs transition disabled:opacity-50"
                title="Auto-Verify Mode: Autonomous stealth fill & submit with multi-layer OCR + HTTP 200 proof verification"
              >
                <Play className="w-3.5 h-3.5 text-cyan-300 fill-cyan-300" />
                {applyingMode === 'auto_verify' ? 'Auto-Verifying...' : 'Auto-Verify Mode'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* High-Resolution Screenshot Lightbox Modal */}
      {lightboxOpen && jobUrl && (
        <div 
          className="fixed inset-0 z-50 bg-zinc-950/80 backdrop-blur-md flex flex-col p-4 md:p-6 animate-in fade-in duration-200"
          onClick={() => setLightboxOpen(false)}
        >
          {/* Modal Header */}
          <div 
            className="flex items-center justify-between p-3.5 px-5 bg-zinc-900/95 border border-zinc-800 rounded-2xl text-white mb-3 shadow-xl backdrop-blur-md"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 min-w-0">
              <Camera className="w-4 h-4 text-emerald-400 shrink-0" />
              <div className="truncate">
                <span className="text-xs font-bold text-zinc-100 mr-2">{job?.company || 'Company'}</span>
                <span className="text-xs text-zinc-400 truncate">({job?.title || 'Application Proof'})</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-emerald-950 text-emerald-400 border border-emerald-800 hidden sm:inline-block">
                Retina 2x Lossless
              </span>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center bg-zinc-800/80 rounded-xl p-1 border border-zinc-700/80">
                <button
                  type="button"
                  onClick={() => setZoomLevel((z) => Math.max(0.5, z - 0.25))}
                  className="p-1 text-zinc-300 hover:text-white hover:bg-zinc-700/80 rounded-lg transition cursor-pointer"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <span className="text-[11px] font-mono px-2 text-zinc-300 min-w-[48px] text-center font-semibold">
                  {Math.round(zoomLevel * 100)}%
                </span>
                <button
                  type="button"
                  onClick={() => setZoomLevel((z) => Math.min(3.0, z + 0.25))}
                  className="p-1 text-zinc-300 hover:text-white hover:bg-zinc-700/80 rounded-lg transition cursor-pointer"
                  title="Zoom In"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setZoomLevel(1)}
                  className="text-[10px] font-semibold px-2 py-0.5 text-zinc-400 hover:text-zinc-100 transition rounded-md ml-1"
                >
                  Reset
                </button>
              </div>

              <a
                href={`/api/proofs?url=${encodeURIComponent(jobUrl)}&type=screenshot`}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/80 rounded-xl transition cursor-pointer"
                title="Open original raw image in new tab"
              >
                <ExternalLink className="w-4 h-4 text-cyan-400" />
              </a>

              <a
                href={`/api/proofs?url=${encodeURIComponent(jobUrl)}&type=screenshot&download=1`}
                className="p-2 text-zinc-400 hover:text-emerald-400 hover:bg-zinc-800/80 rounded-xl transition cursor-pointer"
                download
                title="Download original PNG"
              >
                <Download className="w-4 h-4 text-emerald-400" />
              </a>

              <button
                type="button"
                onClick={() => setLightboxOpen(false)}
                className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/80 rounded-xl transition cursor-pointer ml-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Modal Image Body with Panning & High-DPI Rendering */}
          <div 
            className="flex-1 overflow-auto rounded-3xl border border-zinc-800/80 bg-zinc-950/90 shadow-2xl p-4 flex items-start justify-center cursor-default"
            onClick={(e) => e.stopPropagation()}
          >
            <div 
              style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center', transition: 'transform 0.15s ease-out' }}
              className="max-w-none transition"
            >
              <img
                src={`/api/proofs?url=${encodeURIComponent(jobUrl)}&type=screenshot`}
                alt="High-resolution confirmation receipt"
                className="rounded-xl shadow-2xl block mx-auto"
                style={{ maxWidth: zoomLevel === 1 ? '100%' : 'none' }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
