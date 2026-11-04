'use client';

import React, { useState } from 'react';
import { X, Building2, Plus, Star } from 'lucide-react';

interface AddCompanyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCompanyAdded: () => void;
}

export function AddCompanyModal({ isOpen, onClose, onCompanyAdded }: AddCompanyModalProps) {
  const [companyName, setCompanyName] = useState('');
  const [domain, setDomain] = useState('');
  const [careersUrl, setCareersUrl] = useState('');
  const [atsProvider, setAtsProvider] = useState('greenhouse');
  const [sector, setSector] = useState('AI & Machine Learning');
  const [priorityTier, setPriorityTier] = useState<number>(1);
  const [isVip, setIsVip] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName) {
      setError('Company Name is required.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch('/api/companies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: companyName,
          official_domain: domain,
          careers_page_url: careersUrl,
          ats_provider: atsProvider,
          sector,
          priority_tier: priorityTier,
          is_vip: isVip ? 1 : 0,
        }),
      });

      const json = await res.json();
      if (json.success) {
        onCompanyAdded();
        onClose();
      } else {
        setError(json.error || 'Failed to add company');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to add company');
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
            <div className="p-2.5 rounded-2xl bg-amber-500/10 text-amber-700 border border-amber-200 shadow-2xs">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-zinc-900">Add Target Company</h2>
              <p className="text-xs text-zinc-500">Enroll company into continuous ATS monitoring</p>
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

          <div>
            <label className="text-xs font-semibold text-zinc-700 block mb-1">
              Company Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Anthropic"
              className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Official Domain</label>
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="anthropic.com"
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs font-mono"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">ATS Provider</label>
              <select
                value={atsProvider}
                onChange={(e) => setAtsProvider(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="greenhouse">Greenhouse</option>
                <option value="lever">Lever</option>
                <option value="ashby">Ashby</option>
                <option value="workday">Workday</option>
                <option value="custom">Custom Careers Site</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-zinc-700 block mb-1">Careers Board URL</label>
            <input
              type="url"
              value={careersUrl}
              onChange={(e) => setCareersUrl(e.target.value)}
              placeholder="https://jobs.lever.co/anthropic"
              className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 font-mono shadow-2xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Sector</label>
              <input
                type="text"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                placeholder="AI / Foundation Models"
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Priority Tier</label>
              <select
                value={priorityTier}
                onChange={(e) => setPriorityTier(Number(e.target.value))}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="1">Tier 1 (Highest Priority)</option>
                <option value="2">Tier 2 (Standard)</option>
                <option value="3">Tier 3 (Backlog)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="add-company-vip"
              checked={isVip}
              onChange={(e) => setIsVip(e.target.checked)}
              className="rounded border-zinc-300 text-purple-600 focus:ring-purple-500"
            />
            <label htmlFor="add-company-vip" className="text-xs font-semibold text-zinc-800 cursor-pointer flex items-center gap-1.5">
              <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-600" />
              Enroll as VIP Company (Instant High-Priority Alerts)
            </label>
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
              <Plus className="w-3.5 h-3.5 text-amber-400" />
              <span>{submitting ? 'Adding...' : 'Add to Watchlist'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
