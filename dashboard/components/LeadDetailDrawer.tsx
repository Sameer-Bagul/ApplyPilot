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
} from 'lucide-react';

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
  const [actionLoading, setActionLoading] = useState(false);
  const [dispatchResult, setDispatchResult] = useState<string | null>(null);

  // Editable fields
  const [editName, setEditName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editRole, setEditRole] = useState('');
  const [editType, setEditType] = useState('');
  const [editSubject, setEditSubject] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editLinkedin, setEditLinkedin] = useState('');
  const [editStatus, setEditStatus] = useState('');

  useEffect(() => {
    if (!leadId) {
      setData(null);
      return;
    }

    const fetchLead = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/leads/detail?id=${encodeURIComponent(leadId)}`);
        const json = await res.json();
        if (json.success) {
          setData(json.data);
          const l = json.data.lead;
          setEditName(l.contact_name || '');
          setEditEmail(l.contact_email || '');
          setEditRole(l.role_title || '');
          setEditType(l.contact_type || 'recruiter');
          setEditSubject(l.email_draft_subject || '');
          setEditBody(l.email_draft_body || '');
          setEditLinkedin(l.contact_linkedin_url || '');
          setEditStatus(l.outreach_status || 'pending_review');
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
  const company = data?.company;
  const auditLogs = data?.audit_logs || [];

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
        if (onLeadUpdated) onLeadUpdated();
      }
    } catch (err) {
      console.error('Failed to reject lead', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`/api/leads/detail?id=${encodeURIComponent(leadId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contact_name: editName,
          contact_email: editEmail,
          role_title: editRole,
          contact_type: editType,
          email_draft_subject: editSubject,
          email_draft_body: editBody,
          contact_linkedin_url: editLinkedin,
          outreach_status: editStatus,
        }),
      });
      const json = await res.json();
      if (json.success) {
        setData((prev: any) => ({
          ...prev,
          lead: {
            ...prev.lead,
            contact_name: editName,
            contact_email: editEmail,
            role_title: editRole,
            contact_type: editType,
            email_draft_subject: editSubject,
            email_draft_body: editBody,
            contact_linkedin_url: editLinkedin,
            outreach_status: editStatus,
          },
        }));
        if (onLeadUpdated) onLeadUpdated();
      }
    } catch (err) {
      console.error('Failed to save lead draft', err);
    } finally {
      setSaving(false);
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

  const handleDispatch = async () => {
    setActionLoading(true);
    setDispatchResult(null);
    try {
      if (editStatus !== 'approved') {
        await handleApprove();
      }
      const res = await fetch('/api/leads/dispatch', { method: 'POST' });
      const json = await res.json();
      if (json.success) {
        setDispatchResult(`Dispatched! ${json.message}`);
        setEditStatus('sent');
        if (onLeadUpdated) onLeadUpdated();
      } else {
        setDispatchResult(`Error: ${json.error}`);
      }
    } catch (err: any) {
      setDispatchResult(`Dispatch failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 overflow-hidden bg-slate-900/25 backdrop-blur-md flex justify-end animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl h-full liquid-glass-elevated bg-white/95 backdrop-blur-2xl border-l border-white/80 shadow-2xl flex flex-col relative text-zinc-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-zinc-200/70 bg-white/70 flex items-start justify-between gap-4 relative">
          <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />

          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                editStatus === 'approved' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                editStatus === 'rejected' ? 'bg-rose-50 text-rose-800 border-rose-200' :
                editStatus === 'sent' ? 'bg-cyan-50 text-cyan-800 border-cyan-200' :
                'bg-amber-50 text-amber-800 border-amber-200'
              }`}>
                HITL Gate: {editStatus}
              </span>
              <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-zinc-100 text-zinc-600 border border-zinc-200">
                {lead?.contact_type || 'recruiter'}
              </span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-zinc-900 flex items-center gap-2 truncate">
              <User className="w-5 h-5 text-cyan-600 shrink-0" />
              <span>{editName || 'Hiring Lead'}</span>
            </h2>
            <div className="flex items-center gap-3 text-xs text-zinc-500">
              <span 
                onClick={() => lead?.company_name && onOpenCompany && onOpenCompany(lead.company_name)}
                className="text-cyan-700 hover:underline cursor-pointer flex items-center gap-1 font-semibold"
              >
                <Building2 className="w-3.5 h-3.5" />
                {lead?.company_name}
              </span>
              <span>•</span>
              <span>{editRole || 'Talent Acquisition'}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={onClose}
              className="liquid-pill rounded-full p-2 text-zinc-600 hover:text-zinc-950 transition shadow-2xs"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* HITL Safety Control Bar */}
        <div className="px-6 py-3 border-b border-zinc-200/60 bg-zinc-50/70 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-zinc-600">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span className="font-medium">Human-in-the-Loop Admin Safety</span>
          </div>

          <div className="flex items-center gap-2">
            {editStatus === 'pending_review' && (
              <>
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition cursor-pointer"
                >
                  Reject Lead
                </button>
                <button
                  onClick={handleApprove}
                  disabled={actionLoading}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 transition flex items-center gap-1 cursor-pointer shadow-xs"
                >
                  <Check className="w-3.5 h-3.5" />
                  Approve for Outreach
                </button>
              </>
            )}

            {editStatus === 'approved' && (
              <button
                onClick={handleDispatch}
                disabled={actionLoading}
                className="liquid-pill-dark px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <Send className="w-3.5 h-3.5 text-cyan-400" />
                <span>{actionLoading ? 'Dispatching...' : 'Dispatch Now'}</span>
              </button>
            )}

            {editStatus === 'sent' && (
              <span className="px-3 py-1 rounded-xl text-xs font-semibold bg-cyan-50 text-cyan-800 border border-cyan-200 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Email Dispatched
              </span>
            )}
          </div>
        </div>

        {/* Dispatch result message */}
        {dispatchResult && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-cyan-50 border border-cyan-200 text-xs text-cyan-900 font-medium">
            {dispatchResult}
          </div>
        )}

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {loading ? (
            <div className="py-20 text-center text-sm text-zinc-400">Loading recruiter contact...</div>
          ) : (
            <>
              {/* Profile Inputs */}
              <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-700">
                  Lead Information
                </h3>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-zinc-600 block mb-1">Full Name</label>
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      placeholder="Jane Doe"
                      className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-zinc-600 block mb-1">Direct Email</label>
                    <input
                      type="email"
                      value={editEmail}
                      onChange={(e) => setEditEmail(e.target.value)}
                      placeholder="jane@company.com"
                      className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-zinc-600 block mb-1">Title / Role</label>
                    <input
                      type="text"
                      value={editRole}
                      onChange={(e) => setEditRole(e.target.value)}
                      placeholder="Head of Talent Acquisition"
                      className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-zinc-600 block mb-1">Contact Type</label>
                    <select
                      value={editType}
                      onChange={(e) => setEditType(e.target.value)}
                      className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                    >
                      <option value="recruiter">Recruiter / Talent Partner</option>
                      <option value="engineering_lead">Engineering Lead / VP</option>
                      <option value="founder">Founder / CEO / CTO</option>
                      <option value="sourcer">Sourcer / HR</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-zinc-600 block mb-1">LinkedIn Profile</label>
                  <input
                    type="url"
                    value={editLinkedin}
                    onChange={(e) => setEditLinkedin(e.target.value)}
                    placeholder="https://linkedin.com/in/janedoe"
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs font-mono"
                  />
                </div>
              </div>

              {/* Personalized Email Pitch Draft */}
              <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-700 flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-cyan-600" />
                    Personalized Outreach Draft
                  </h3>
                  <span className="text-[10px] text-zinc-500 font-mono">100% Free Engine</span>
                </div>

                <div>
                  <label className="text-xs font-semibold text-zinc-600 block mb-1">Email Subject</label>
                  <input
                    type="text"
                    value={editSubject}
                    onChange={(e) => setEditSubject(e.target.value)}
                    placeholder="Application & Introduction: Senior AI / Full-Stack Engineer"
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-zinc-600 block mb-1">Email Body</label>
                  <textarea
                    rows={8}
                    value={editBody}
                    onChange={(e) => setEditBody(e.target.value)}
                    placeholder="Hi Jane, I noticed your team is building..."
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs font-sans leading-relaxed"
                  />
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-zinc-200/70">
                  <button
                    onClick={handleDelete}
                    type="button"
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition flex items-center gap-1.5 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Delete Lead
                  </button>

                  <button
                    onClick={handleSave}
                    disabled={saving}
                    type="button"
                    className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <Save className="w-3.5 h-3.5" />
                    {saving ? 'Saving...' : 'Save Draft'}
                  </button>
                </div>
              </div>

              {/* Discovery Audit Log */}
              {auditLogs.length > 0 && (
                <div className="liquid-glass rounded-2xl p-4 border border-white/90 shadow-2xs space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-zinc-500 block">
                    Discovery Audit Log
                  </span>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto text-xs text-zinc-600">
                    {auditLogs.map((log: any, i: number) => (
                      <div key={i} className="flex items-center justify-between py-1 border-b border-zinc-200/50">
                        <span className="font-mono text-[11px] text-zinc-800">{log.action_name}</span>
                        <span className="text-zinc-500 text-[10px]">
                          {log.created_at ? new Date(log.created_at).toLocaleTimeString() : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
