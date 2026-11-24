'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  ExternalLink,
  Mail,
  User,
  Building2,
  CheckCircle2,
  XCircle,
  Save,
  Trash2,
  Send,
  Link2,
  ShieldCheck,
  Clock,
  Sparkles,
  Paperclip,
  Check,
  AlertTriangle,
  FileText,
  Briefcase,
  Layers,
  Cpu,
  Flame,
  Info,
  ChevronDown,
  ChevronUp,
  Copy,
  MessageSquare,
} from 'lucide-react';

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.45a1.6 1.6 0 1 0 0 3.2 1.6 1.6 0 0 0 0-3.2Z" />
    </svg>
  );
}

interface LeadDetailDrawerProps {
  leadId: string | null;
  onClose: () => void;
  onLeadUpdated?: () => void;
  onOpenCompany?: (companyName: string) => void;
}

export function LeadDetailDrawer({
  leadId,
  onClose,
  onLeadUpdated,
  onOpenCompany,
}: LeadDetailDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any | null>(null);
  const [saving, setSaving] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [showTransportHelp, setShowTransportHelp] = useState(false);

  // Editable fields
  const [editName, setEditName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editPersonalEmail, setEditPersonalEmail] = useState('');
  const [editPersonalSource, setEditPersonalSource] = useState('');
  const [preferredChannel, setPreferredChannel] = useState<'corporate' | 'personal'>('corporate');
  const [enriching, setEnriching] = useState(false);
  const [editRole, setEditRole] = useState('');
  const [editPersona, setEditPersona] = useState('founder');
  const [editScore, setEditScore] = useState(0);
  const [editSubject, setEditSubject] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editLinkedin, setEditLinkedin] = useState('');
  const [editLinkedinNote, setEditLinkedinNote] = useState('');
  const [copiedNote, setCopiedNote] = useState(false);
  const [insertedQuote, setInsertedQuote] = useState(false);
  const [editStatus, setEditStatus] = useState('drafted');

  useEffect(() => {
    if (!leadId) {
      setData(null);
      setFeedback(null);
      return;
    }

    const fetchLead = async () => {
      setLoading(true);
      setFeedback(null);
      try {
        const res = await fetch(`/api/leads/detail?id=${encodeURIComponent(leadId)}`);
        const json = await res.json();
        if (json.success) {
          setData(json);
          const l = json.lead;
          setEditName(l.contact_name || '');
          setEditEmail(l.contact_email || '');
          setEditPersonalEmail(l.personal_email || '');
          setEditPersonalSource(l.personal_email_source || '');
          setPreferredChannel((l.preferred_channel as any) || 'corporate');
          setEditRole(l.role_title || '');
          setEditPersona(l.persona || l.contact_type || 'founder');
          setEditScore(l.priority_score || 0);
          setEditSubject(l.email_subject || l.email_draft_subject || '');
          setEditBody(l.email_body_text || l.email_draft_body || '');
          const firstKeyPerson = json.companyIntel?.key_people?.[0];
          setEditLinkedin(l.contact_linkedin_url || firstKeyPerson?.linkedin_url || '');
          setEditLinkedinNote(l.linkedin_connection_note || firstKeyPerson?.connection_note || '');
          setEditStatus(l.outreach_status || 'drafted');
        }
      } catch (err) {
        console.error('Failed to load lead detail', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLead();
  }, [leadId]);

  if (!leadId) return null;

  const lead = data?.lead;
  const company = data?.companyInfo;
  const intel = data?.companyIntel;
  const openJobs = data?.openJobs || [];
  const resume = data?.resume;
  const transport = data?.transport;

  // 1-Click Send Email action
  const handleSendEmail = async () => {
    if (!leadId) return;
    const destEmail = preferredChannel === 'personal' && editPersonalEmail ? editPersonalEmail : editEmail;
    if (!destEmail) {
      setFeedback({ type: 'error', message: 'No recipient email configured.' });
      return;
    }

    const confirmed = window.confirm(
      `Send tailored outreach email now to ${editName || 'Lead'} at ${destEmail}?\n\nResume: ${resume?.filename || 'Default resume'}`
    );
    if (!confirmed) return;

    setSendingEmail(true);
    setFeedback(null);
    try {
      // First save any edits
      await fetch(`/api/leads/detail?id=${encodeURIComponent(leadId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contact_name: editName,
          contact_email: editEmail,
          personal_email: editPersonalEmail,
          preferred_channel: preferredChannel,
          role_title: editRole,
          persona: editPersona,
          email_subject: editSubject,
          email_body_text: editBody,
        }),
      });

      const res = await fetch('/api/leads/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_id: leadId,
          contact_name: editName,
          contact_email: editEmail,
          personal_email: editPersonalEmail,
          preferred_channel: preferredChannel,
          role_title: editRole,
          persona: editPersona,
          subject: editSubject,
          body_text: editBody,
        }),
      });
      const json = await res.json();
      if (json.success) {
        setEditStatus('sent');
        setFeedback({
          type: 'success',
          message: `Email successfully sent to ${destEmail}! (Attached: ${resume?.filename || 'Tailored Resume'})`,
        });
        if (onLeadUpdated) onLeadUpdated();
      } else {
        setFeedback({
          type: 'error',
          message: json.error || 'Failed sending email',
        });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Error executing email send' });
    } finally {
      setSendingEmail(false);
    }
  };

  // 1-Click Save as Gmail Draft
  const handleSaveAsDraft = async () => {
    if (!leadId) return;
    setSavingDraft(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/leads/save-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_id: leadId,
          contact_name: editName,
          contact_email: editEmail,
          personal_email: editPersonalEmail,
          personal_email_source: editPersonalSource,
          preferred_channel: preferredChannel,
          role_title: editRole,
          persona: editPersona,
          subject: editSubject,
          body_text: editBody,
        }),
      });
      const json = await res.json();
      if (json.success) {
        setEditStatus('drafted');
        setFeedback({
          type: 'success',
          message: 'Saved to Gmail Drafts & database successfully!',
        });
        if (onLeadUpdated) onLeadUpdated();
      } else {
        setFeedback({
          type: 'error',
          message: json.error || 'Failed saving draft',
        });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Error saving draft' });
    } finally {
      setSavingDraft(false);
    }
  };

  const handleApprove = async () => {
    setActionLoading(true);
    try {
      const res = await fetch('/api/leads/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: [leadId], approved_by: 'admin_dashboard' }),
      });
      const json = await res.json();
      if (json.success) {
        setEditStatus('approved');
        setFeedback({ type: 'success', message: 'Lead approved for outreach batch dispatch.' });
        if (onLeadUpdated) onLeadUpdated();
      }
    } catch (err) {
      console.error('Failed to approve lead', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    setActionLoading(true);
    try {
      const res = await fetch(`/api/leads/detail?id=${encodeURIComponent(leadId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outreach_status: 'rejected' }),
      });
      const json = await res.json();
      if (json.success) {
        setEditStatus('rejected');
        setFeedback({ type: 'success', message: 'Lead rejected.' });
        if (onLeadUpdated) onLeadUpdated();
      }
    } catch (err) {
      console.error('Failed to reject lead', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleEnrich = async () => {
    if (!leadId || !editName) return;
    setEnriching(true);
    try {
      const res = await fetch('/api/leads/enrich', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          leadId,
          contactName: editName,
          companyName: lead?.company_name,
          domain: lead?.company_domain,
        }),
      });
      const json = await res.json();
      if (json.success && json.huntResult) {
        if (json.huntResult.personal_emails?.[0]) {
          setEditPersonalEmail(json.huntResult.personal_emails[0]);
          setEditPersonalSource(json.huntResult.sources_used?.join(', ') || 'OSINT');
          setPreferredChannel('personal');
          setFeedback({ type: 'success', message: `Found personal email: ${json.huntResult.personal_emails[0]}` });
        }
        if (onLeadUpdated) onLeadUpdated();
      }
    } catch (e) {
      console.error('Failed enriching personal email', e);
    } finally {
      setEnriching(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setFeedback(null);
    try {
      const res = await fetch(`/api/leads/detail?id=${encodeURIComponent(leadId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contact_name: editName,
          contact_email: editEmail,
          personal_email: editPersonalEmail,
          personal_email_source: editPersonalSource,
          preferred_channel: preferredChannel,
          role_title: editRole,
          persona: editPersona,
          priority_score: editScore,
          email_subject: editSubject,
          email_body_text: editBody,
          contact_linkedin_url: editLinkedin,
          linkedin_connection_note: editLinkedinNote,
          outreach_status: editStatus,
        }),
      });
      const json = await res.json();
      if (json.success) {
        setFeedback({ type: 'success', message: 'Lead & email content saved successfully.' });
        if (onLeadUpdated) onLeadUpdated();
      }
    } catch (err) {
      console.error('Failed to save lead draft', err);
      setFeedback({ type: 'error', message: 'Failed to save changes' });
    } finally {
      setSaving(false);
    }
  };

  const copyNoteToClipboard = (text: string) => {
    if (!text) return;
    try {
      navigator.clipboard.writeText(text);
      setCopiedNote(true);
      setTimeout(() => setCopiedNote(false), 2000);
    } catch (err) {
      console.error('Failed copying to clipboard', err);
    }
  };

  const handleDelete = async () => {
    if (!leadId) return;
    if (!confirm('Are you sure you want to delete this recruiter lead?')) return;
    try {
      const res = await fetch(`/api/leads/detail?id=${encodeURIComponent(leadId)}`, {
        method: 'DELETE',
      });
      const json = await res.json();
      if (json.success) {
        if (onLeadUpdated) onLeadUpdated();
        onClose();
      }
    } catch (err) {
      console.error('Failed to delete lead', err);
    }
  };

  const personaColor =
    editPersona === 'founder'
      ? 'bg-purple-50 text-purple-800 border-purple-200'
      : editPersona === 'hr'
      ? 'bg-blue-50 text-blue-800 border-blue-200'
      : 'bg-emerald-50 text-emerald-800 border-emerald-200';

  const scoreBadgeColor =
    editScore >= 80
      ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
      : editScore >= 60
      ? 'bg-cyan-50 text-cyan-700 border-cyan-300'
      : 'bg-zinc-100 text-zinc-700 border-zinc-200';

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden bg-slate-900/30 backdrop-blur-md flex justify-end animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl h-full liquid-glass-elevated bg-white/95 backdrop-blur-2xl border-l border-white/80 shadow-2xl flex flex-col relative text-zinc-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-zinc-200/70 bg-white/80 flex items-start justify-between gap-4 relative">
          <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent pointer-events-none" />

          <div className="space-y-2 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${scoreBadgeColor} flex items-center gap-1`}>
                <Flame className="w-3 h-3 text-amber-500" />
                Score: {editScore}/100
              </span>

              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider border ${personaColor}`}>
                {editPersona === 'founder' ? '🚀 Founder Angle' : editPersona === 'hr' ? '💼 Recruiter Angle' : '⚡ Engineer Angle'}
              </span>

              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                  editStatus === 'approved'
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : editStatus === 'sent'
                    ? 'bg-cyan-50 text-cyan-800 border-cyan-200'
                    : editStatus === 'rejected'
                    ? 'bg-rose-50 text-rose-800 border-rose-200'
                    : 'bg-amber-50 text-amber-800 border-amber-200'
                }`}
              >
                Status: {editStatus}
              </span>
            </div>

            <h2 className="text-xl font-bold tracking-tight text-zinc-900 flex items-center gap-2 truncate">
              <User className="w-5 h-5 text-cyan-600 shrink-0" />
              <span>{editName || 'Hiring Lead'}</span>
            </h2>

            <div className="flex items-center gap-3 text-xs text-zinc-500 flex-wrap">
              <span
                onClick={() => lead?.company_name && onOpenCompany && onOpenCompany(lead.company_name)}
                className="text-cyan-700 hover:underline cursor-pointer flex items-center gap-1 font-semibold"
              >
                <Building2 className="w-3.5 h-3.5" />
                {lead?.company_name}
              </span>
              <span>•</span>
              <span>{editRole || 'Engineering Lead'}</span>
              {lead?.company_domain && (
                <>
                  <span>•</span>
                  <a
                    href={`https://${lead.company_domain}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-zinc-500 hover:text-zinc-800 flex items-center gap-1"
                  >
                    {lead.company_domain}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={onClose}
              className="liquid-pill rounded-full p-2 text-zinc-600 hover:text-zinc-950 transition shadow-2xs cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Transport & Sending Channel Status Banner */}
        <div className="px-6 py-2.5 border-b border-zinc-200/60 bg-zinc-50/90 text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-semibold text-zinc-700">Outreach Channel:</span>
              <span className="font-mono font-medium text-emerald-800 bg-emerald-100/70 px-2 py-0.5 rounded-md border border-emerald-200">
                {transport?.label || 'SMTP / Gmail'}
              </span>
            </div>

            <button
              onClick={() => setShowTransportHelp(!showTransportHelp)}
              className="text-zinc-500 hover:text-zinc-800 flex items-center gap-1 cursor-pointer font-medium"
            >
              <Info className="w-3.5 h-3.5" />
              <span>How sending works</span>
              {showTransportHelp ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>

          {showTransportHelp && (
            <div className="mt-2.5 p-3 rounded-xl bg-white border border-zinc-200 shadow-2xs space-y-1.5 text-zinc-600 animate-in fade-in">
              <div className="font-bold text-zinc-800 text-[11px] uppercase tracking-wider">
                Flexible Sending: SMTP vs Gmail API
              </div>
              <p className="text-[11px] leading-relaxed">
                ApplyPilot gives you the choice between standard <strong>SMTP</strong> (e.g. Gmail App Passwords) or <strong>Gmail OAuth API</strong>:
              </p>
              <ul className="list-disc pl-4 text-[11px] space-y-0.5 text-zinc-700">
                <li>
                  <strong>Option A (Easiest - 1 minute):</strong> Use a standard <strong>Gmail App Password</strong>. In your Google Account &gt; Security &gt; App Passwords, generate a 16-character code. Set <code className="bg-zinc-100 px-1 py-0.5 rounded font-mono">SMTP_USER=you@gmail.com</code> and <code className="bg-zinc-100 px-1 py-0.5 rounded font-mono">SMTP_PASS=xxxx xxxx xxxx xxxx</code> in your <code className="bg-zinc-100 px-1 py-0.5 rounded font-mono">.env</code>.
                </li>
                <li>
                  <strong>Option B:</strong> Gmail OAuth via <code className="bg-zinc-100 px-1 py-0.5 rounded font-mono">~/.gmail-mcp/credentials.json</code> directly creates drafts in your Gmail folder and sends via REST API.
                </li>
                <li>
                  <strong>Option C (Local / Mock):</strong> Without credentials, ApplyPilot cleanly simulates drafts and sends locally so you can preview everything risk-free!
                </li>
              </ul>
            </div>
          )}
        </div>

        {/* Action / Confirmation Feedback Banner */}
        {feedback && (
          <div
            className={`mx-6 mt-4 p-3.5 rounded-2xl text-xs font-semibold flex items-center justify-between gap-2 shadow-2xs ${
              feedback.type === 'success'
                ? 'bg-emerald-50 border border-emerald-200 text-emerald-900'
                : 'bg-rose-50 border border-rose-200 text-rose-900'
            }`}
          >
            <div className="flex items-center gap-2">
              {feedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <span>{feedback.message}</span>
            </div>
            <button onClick={() => setFeedback(null)} className="text-zinc-400 hover:text-zinc-600">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {loading ? (
            <div className="py-20 text-center text-sm text-zinc-400">Loading cold email draft & intel...</div>
          ) : (
            <>
              {/* Company Intelligence Summary Card */}
              {intel && (
                <div className="liquid-glass rounded-2xl p-4.5 border border-white/90 shadow-2xs space-y-3 bg-gradient-to-br from-white/90 to-cyan-50/30">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-cyan-900 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
                      Company Intelligence (30-day Cache)
                    </span>
                    {intel.funding_stage && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-100/70 text-cyan-800 border border-cyan-200">
                        {intel.funding_stage}
                      </span>
                    )}
                  </div>

                  {intel.wikipedia_summary && (
                    <p className="text-xs text-zinc-600 leading-relaxed italic bg-white/70 p-2.5 rounded-xl border border-zinc-200/60">
                      "{intel.wikipedia_summary}"
                    </p>
                  )}

                  {/* Tech stack badges */}
                  {intel.tech_stack && intel.tech_stack.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[11px] font-semibold text-zinc-500 block">Verified Tech Stack:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {intel.tech_stack.map((t: string, idx: number) => (
                          <span
                            key={idx}
                            className="text-[11px] px-2 py-0.5 rounded-md font-mono bg-zinc-100 text-zinc-700 border border-zinc-200"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* AI focus tags */}
                  {intel.ai_focus_tags && intel.ai_focus_tags.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[11px] font-semibold text-zinc-500 block">AI Focus Vectors:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {intel.ai_focus_tags.map((tag: string, idx: number) => (
                          <span
                            key={idx}
                            className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-purple-50 text-purple-700 border border-purple-200 flex items-center gap-1"
                          >
                            <Cpu className="w-2.5 h-2.5" />
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Open roles match */}
                  {openJobs && openJobs.length > 0 && (
                    <div className="pt-2 border-t border-zinc-200/60 flex items-center justify-between text-xs">
                      <span className="text-zinc-600 flex items-center gap-1 font-medium">
                        <Briefcase className="w-3.5 h-3.5 text-zinc-500" />
                        {openJobs.length} active matching jobs at {lead?.company_name}
                      </span>
                      <span className="text-cyan-700 font-semibold">{openJobs[0]?.title}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Recipient Details & Channel */}
              <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-700 flex items-center justify-between">
                  <span>Recipient & Target Channel</span>
                  <span className="text-[10px] font-mono font-normal text-zinc-500">ID: {lead?.lead_id}</span>
                </h3>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-zinc-600 block mb-1">Full Name</label>
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      placeholder="Jane Doe"
                      className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:border-cyan-400 shadow-2xs"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-zinc-600 block mb-1">Role / Persona Angle</label>
                    <select
                      value={editPersona}
                      onChange={(e) => setEditPersona(e.target.value)}
                      className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:border-cyan-400 shadow-2xs font-semibold"
                    >
                      <option value="founder">Founder / CEO / CTO (Impact & Architecture)</option>
                      <option value="hr">Recruiter / HR (Skills & Notice Period)</option>
                      <option value="engineer">Engineering Lead (Peer Stack & Code)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-zinc-600 block mb-1">Corporate Work Email</label>
                    <input
                      type="email"
                      value={editEmail}
                      onChange={(e) => setEditEmail(e.target.value)}
                      placeholder="jane@company.com"
                      className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:border-cyan-400 shadow-2xs font-mono"
                    />
                    {intel?.detected_email_pattern && (
                      <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-emerald-800 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg font-mono">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                        <span className="font-semibold">Pattern Confirmed:</span>
                        <span>{intel.detected_email_pattern}</span>
                        {intel.email_pattern_confidence ? (
                          <span className="text-emerald-600 font-bold">({Math.round(intel.email_pattern_confidence * 100)}% conf)</span>
                        ) : null}
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs font-semibold text-zinc-600">Personal Email (OSINT)</label>
                      <button
                        type="button"
                        onClick={handleEnrich}
                        disabled={enriching}
                        className="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer"
                      >
                        <Sparkles className={`w-3 h-3 ${enriching ? 'animate-spin' : ''}`} />
                        {enriching ? 'Hunting...' : 'Find'}
                      </button>
                    </div>
                    <input
                      type="email"
                      value={editPersonalEmail}
                      onChange={(e) => setEditPersonalEmail(e.target.value)}
                      placeholder="jane.personal@gmail.com"
                      className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 shadow-2xs font-mono"
                    />
                  </div>
                </div>

                {/* Target Channel Switcher */}
                <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/70 flex items-center justify-between text-xs">
                  <span className="text-zinc-600 font-medium">Send Destination:</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setPreferredChannel('corporate')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold cursor-pointer transition ${
                        preferredChannel === 'corporate'
                          ? 'bg-cyan-600 text-white shadow-2xs'
                          : 'bg-zinc-200/70 text-zinc-600 hover:text-zinc-900'
                      }`}
                    >
                      Corporate Email ({editEmail ? editEmail.split('@')[1] : 'Company'})
                    </button>
                    <button
                      type="button"
                      onClick={() => setPreferredChannel('personal')}
                      disabled={!editPersonalEmail}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                        !editPersonalEmail
                          ? 'opacity-40 cursor-not-allowed bg-zinc-100 text-zinc-400'
                          : preferredChannel === 'personal'
                          ? 'bg-indigo-600 text-white shadow-2xs cursor-pointer'
                          : 'bg-zinc-200/70 text-zinc-600 hover:text-zinc-900 cursor-pointer'
                      }`}
                    >
                      Personal Inbox {editPersonalEmail ? '(@gmail)' : ''}
                    </button>
                  </div>
                </div>
              </div>

              {/* Dual-Attack Channel: LinkedIn Decision Maker & Connection Note */}
              <div className="liquid-glass rounded-2xl p-5 border border-sky-200/80 shadow-2xs space-y-4 bg-gradient-to-br from-white/95 to-sky-50/40">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-lg bg-sky-600 text-white flex items-center justify-center shadow-2xs shrink-0">
                      <LinkedInIcon className="w-4 h-4" />
                    </span>
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-sky-950 flex items-center gap-1.5">
                        Dual-Attack: LinkedIn Decision Maker
                      </h3>
                      <p className="text-[10px] text-sky-700">Non-login public OSINT • Tailored connection note &lt; 300 chars</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-300">
                    Dual Channel
                  </span>
                </div>

                {/* Multiple Discovered People Selector (if available) */}
                {intel?.key_people && intel.key_people.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-semibold text-zinc-600 block">
                      Discovered Company Leadership ({intel.key_people.length}):
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {intel.key_people.map((person: any, idx: number) => {
                        const isSelected = editLinkedin === person.linkedin_url;
                        return (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => {
                              if (person.name) setEditName(person.name);
                              if (person.role) setEditRole(person.role);
                              if (person.persona) setEditPersona(person.persona);
                              if (person.linkedin_url) setEditLinkedin(person.linkedin_url);
                              if (person.connection_note) setEditLinkedinNote(person.connection_note);
                            }}
                            className={`px-2.5 py-1.5 rounded-xl text-xs font-medium border text-left transition flex items-center gap-2 cursor-pointer ${
                              isSelected
                                ? 'bg-sky-600 text-white border-sky-700 shadow-2xs'
                                : 'bg-white/90 text-zinc-700 border-zinc-200 hover:border-sky-300 hover:bg-sky-50/60'
                            }`}
                          >
                            <span className="font-semibold">{person.name}</span>
                            <span className={`text-[10px] opacity-80 ${isSelected ? 'text-sky-100' : 'text-zinc-500'}`}>
                              ({person.role})
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* LinkedIn Profile Link Input & External Open */}
                <div>
                  <label className="text-xs font-semibold text-zinc-600 block mb-1">LinkedIn Profile Link</label>
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1 min-w-0">
                      <input
                        type="url"
                        value={editLinkedin}
                        onChange={(e) => setEditLinkedin(e.target.value)}
                        placeholder="https://www.linkedin.com/in/username"
                        className="w-full bg-white border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-sky-200 focus:border-sky-400 shadow-2xs font-mono"
                      />
                    </div>
                    {editLinkedin ? (
                      <a
                        href={editLinkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-2 rounded-xl text-xs font-bold text-sky-700 bg-sky-100/80 hover:bg-sky-200/80 border border-sky-300 transition flex items-center gap-1.5 shrink-0 shadow-2xs cursor-pointer"
                        title="Open LinkedIn Profile in new tab"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>Open Profile</span>
                      </a>
                    ) : null}
                  </div>
                </div>

                {/* Personalized Connection Note */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <label className="font-semibold text-zinc-600">Tailored Connection Note (&lt; 300 chars)</label>
                    <span
                      className={`text-[11px] font-mono font-bold ${
                        editLinkedinNote.length > 300
                          ? 'text-rose-600'
                          : editLinkedinNote.length >= 250
                          ? 'text-amber-600'
                          : 'text-emerald-700'
                      }`}
                    >
                      {editLinkedinNote.length}/300 chars
                    </span>
                  </div>

                  <textarea
                    rows={3}
                    value={editLinkedinNote}
                    onChange={(e) => setEditLinkedinNote(e.target.value)}
                    placeholder="Hi there, really impressed by what you're building..."
                    className="w-full bg-white border border-zinc-200/90 rounded-xl p-3 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-sky-200 focus:border-sky-400 shadow-2xs font-sans leading-relaxed"
                  />

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[10px] text-zinc-500">
                      Copy note and paste directly into LinkedIn "Add a note" modal
                    </span>
                    <button
                      type="button"
                      onClick={() => copyNoteToClipboard(editLinkedinNote)}
                      disabled={!editLinkedinNote}
                      className="px-3 py-1.5 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-700 transition flex items-center gap-1.5 cursor-pointer shadow-2xs active:scale-95 disabled:opacity-40"
                    >
                      {copiedNote ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-300" />
                          <span>Copied to Clipboard!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 text-sky-200" />
                          <span>Copy Note</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Active Social Hiring Announcements (LinkedIn / X Posts) */}
              {intel?.hiring_posts && intel.hiring_posts.length > 0 && (
                <div className="liquid-glass rounded-2xl p-4.5 border border-amber-200/80 shadow-2xs space-y-3 bg-gradient-to-br from-amber-50/50 to-orange-50/30 text-zinc-900">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-950 flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5 text-amber-600" />
                      Public Hiring Post &amp; Quote Hook
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300">
                      Smoking Gun Signal
                    </span>
                  </div>

                  {intel.hiring_posts.slice(0, 2).map((post: any, idx: number) => (
                    <div key={idx} className="p-3 bg-white/90 rounded-xl border border-amber-200/60 shadow-2xs space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-zinc-800 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-amber-500" />
                          {post.author_name || 'Hiring Lead'}
                          <span className="text-[10px] text-zinc-500 font-normal">
                            ({post.platform === 'linkedin_post' ? 'LinkedIn' : 'X'})
                          </span>
                        </span>
                        {post.post_url && (
                          <a
                            href={post.post_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] text-amber-700 hover:text-amber-900 flex items-center gap-1 font-semibold"
                          >
                            <span>View Post</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>

                      <p className="text-xs text-zinc-600 leading-relaxed italic bg-amber-50/60 p-2 rounded-lg border border-amber-100">
                        "{post.post_quote}"
                      </p>

                      <div className="flex items-center justify-end">
                        <button
                          type="button"
                          onClick={() => {
                            const quoteRef = `\n\nP.S. Saw your post mentioning: "${post.post_quote.slice(0, 100)}...". As an engineer passionate about this problem, I'd love to contribute directly.`;
                            if (!editBody.includes(post.post_quote.slice(0, 40))) {
                              setEditBody(editBody + quoteRef);
                              setInsertedQuote(true);
                              setTimeout(() => setInsertedQuote(false), 2500);
                            }
                          }}
                          className="text-[11px] font-bold text-amber-800 bg-amber-100/80 hover:bg-amber-200/80 px-2.5 py-1 rounded-lg border border-amber-300 transition flex items-center gap-1 cursor-pointer"
                        >
                          <Sparkles className="w-3 h-3 text-amber-600" />
                          <span>{insertedQuote ? 'Inserted into Draft!' : 'Insert Post Hook into Email'}</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Email Content Editor */}
              <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-700 flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-cyan-600" />
                    Personalized Outreach Email
                  </h3>
                  <span className="text-[10px] text-zinc-400 font-mono">Tailored for {editPersona}</span>
                </div>

                <div>
                  <label className="text-xs font-semibold text-zinc-600 block mb-1">Subject Line</label>
                  <input
                    type="text"
                    value={editSubject}
                    onChange={(e) => setEditSubject(e.target.value)}
                    placeholder="Application: Software Engineer — Sameer Bagul"
                    className="w-full bg-white border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:border-cyan-400 shadow-2xs font-semibold"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-zinc-600 block mb-1">Email Body (Plaintext / HTML)</label>
                  <textarea
                    rows={10}
                    value={editBody}
                    onChange={(e) => setEditBody(e.target.value)}
                    placeholder="Hi there, I noticed your recent work at..."
                    className="w-full bg-white border border-zinc-200/90 rounded-xl p-3 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:border-cyan-400 shadow-2xs font-sans leading-relaxed"
                  />
                </div>

                {/* Resume Attachment Card */}
                <div className="p-3.5 rounded-xl bg-gradient-to-r from-zinc-50 to-emerald-50/40 border border-zinc-200/80 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-zinc-800 truncate">
                        {resume?.filename || 'Sameer_Bagul_Resume.pdf'}
                      </div>
                      <div className="text-[10px] text-zinc-500 truncate font-mono">
                        {resume?.path || '~/.applypilot/resume.pdf'}
                      </div>
                    </div>
                  </div>

                  <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 shrink-0 flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    Attached &amp; Ready
                  </span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-5 border-t border-zinc-200/70 bg-white/90 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={handleDelete}
              type="button"
              className="px-3 py-2 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition flex items-center gap-1.5 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete</span>
            </button>

            {editStatus === 'pending_review' && (
              <button
                onClick={handleReject}
                disabled={actionLoading}
                className="px-3 py-2 rounded-xl text-xs font-semibold text-zinc-700 bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 transition cursor-pointer"
              >
                Reject
              </button>
            )}
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={handleSave}
              disabled={saving}
              type="button"
              className="liquid-pill px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-2xs"
            >
              <Save className="w-3.5 h-3.5 text-zinc-600" />
              <span>{saving ? 'Saving...' : 'Save Draft'}</span>
            </button>

            <button
              onClick={handleSaveAsDraft}
              disabled={savingDraft}
              type="button"
              className="liquid-pill px-3.5 py-2 rounded-xl text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 flex items-center gap-1.5 cursor-pointer shadow-2xs"
              title="Create/Update draft directly in your real Gmail Drafts folder"
            >
              <FileText className="w-3.5 h-3.5 text-indigo-600" />
              <span>{savingDraft ? 'Syncing...' : 'Save as Gmail Draft'}</span>
            </button>

            {editStatus !== 'sent' ? (
              <button
                onClick={handleSendEmail}
                disabled={sendingEmail}
                type="button"
                className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 flex items-center gap-2 cursor-pointer shadow-md hover:scale-[1.02] transition"
              >
                <Send className={`w-3.5 h-3.5 text-cyan-300 ${sendingEmail ? 'animate-bounce' : ''}`} />
                <span>{sendingEmail ? 'Sending...' : 'Send Email Now'}</span>
              </button>
            ) : (
              <span className="px-3 py-2 rounded-xl text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Email Sent
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
