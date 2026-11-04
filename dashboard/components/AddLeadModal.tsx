'use client';

import React, { useState } from 'react';
import { X, Users, Plus, Mail } from 'lucide-react';

interface AddLeadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLeadAdded: () => void;
}

export function AddLeadModal({ isOpen, onClose, onLeadAdded }: AddLeadModalProps) {
  const [companyName, setCompanyName] = useState('');
  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [roleTitle, setRoleTitle] = useState('Senior Technical Recruiter');
  const [contactType, setContactType] = useState('recruiter');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName || !contactEmail) {
      setError('Company Name and Direct Email are required.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch('/api/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: companyName,
          contact_name: contactName,
          contact_email: contactEmail,
          role_title: roleTitle,
          contact_type: contactType,
          outreach_status: 'pending_review',
        }),
      });

      const json = await res.json();
      if (json.success) {
        onLeadAdded();
        onClose();
      } else {
        setError(json.error || 'Failed to add contact lead');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to add contact lead');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 overflow-hidden bg-slate-900/25 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-lg liquid-glass-elevated bg-white/95 backdrop-blur-2xl border border-white/95 rounded-3xl shadow-2xl overflow-hidden flex flex-col text-zinc-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-zinc-200/70 bg-white/70 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-700 border border-emerald-200 shadow-2xs">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-zinc-900">Add Recruiter / Lead</h2>
              <p className="text-xs text-zinc-500">Quarantine lead into Human-in-the-Loop review gate</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="liquid-pill rounded-full p-2 text-zinc-600 hover:text-zinc-950 transition shadow-2xs"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">
                Company Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Google / Stripe"
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Contact Name</label>
              <input
                type="text"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                placeholder="Sarah Connor"
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-zinc-700 block mb-1">
              Direct Contact Email <span className="text-rose-500">*</span>
            </label>
            <input
              type="email"
              required
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="sarah.connor@stripe.com"
              className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 font-mono shadow-2xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Role Title</label>
              <input
                type="text"
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
                placeholder="Staff Recruiter"
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Contact Type</label>
              <select
                value={contactType}
                onChange={(e) => setContactType(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="recruiter">Recruiter / Talent</option>
                <option value="engineering_lead">Engineering Manager / VP</option>
                <option value="founder">Founder / CEO / CTO</option>
                <option value="sourcer">Sourcer / HR</option>
              </select>
            </div>
          </div>

          <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200/80 text-xs text-amber-900 shadow-2xs">
            Lead will be added in <strong className="font-semibold text-amber-950 font-mono">pending_review</strong> status. You can review and personalize the outreach draft in the Recruiter Outreach Hub before approving.
          </div>

          <div className="pt-3 border-t border-zinc-200/70 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="liquid-pill px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer shadow-2xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <Plus className="w-3.5 h-3.5 text-emerald-400" />
              <span>{submitting ? 'Adding...' : 'Add Recruiter Lead'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
