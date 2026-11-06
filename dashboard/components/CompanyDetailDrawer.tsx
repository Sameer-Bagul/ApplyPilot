'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  ExternalLink,
  Building2,
  Globe,
  MapPin,
  Briefcase,
  Users,
  Sparkles,
  Save,
  Trash2,
  RefreshCw,
  Mail,
  ShieldCheck,
  Star,
  Check,
  Copy,
  Layers,
  ArrowRight,
  Code2,
  GitFork,
  Search,
} from 'lucide-react';
import { AutoApplyButton } from './AutoApplyButton';

interface CompanyDetailDrawerProps {
  companyName: string | null;
  companyId?: string | null;
  onClose: () => void;
  onCompanyUpdated?: () => void;
  onOpenJob?: (jobUrl: string) => void;
  onOpenLead?: (lead: any) => void;
}

export function CompanyDetailDrawer({
  companyName,
  companyId,
  onClose,
  onCompanyUpdated,
  onOpenJob,
  onOpenLead,
}: CompanyDetailDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'projects' | 'roles' | 'leads' | 'edit'>('overview');
  const [looping, setLooping] = useState(false);
  const [investigating, setInvestigating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);

  // Edit fields
  const [editDomain, setEditDomain] = useState('');
  const [editCareersUrl, setEditCareersUrl] = useState('');
  const [editAts, setEditAts] = useState('');
  const [editSector, setEditSector] = useState('');
  const [editStage, setEditStage] = useState('');
  const [editLocation, setEditLocation] = useState('');
  const [editPriorityTier, setEditPriorityTier] = useState<number>(2);
  const [editIsVip, setEditIsVip] = useState(false);

  useEffect(() => {
    if (!companyName && !companyId) {
      setData(null);
      return;
    }

    const fetchDetail = async () => {
      setLoading(true);
      try {
        const queryParam = companyName
          ? `name=${encodeURIComponent(companyName)}`
          : `id=${encodeURIComponent(companyId!)}`;
        const res = await fetch(`/api/companies/drilldown?${queryParam}`);
        const json = await res.json();
        if (json.success) {
          setData(json.data);
          const c = json.data.company;
          setEditDomain(c.official_domain || '');
          setEditCareersUrl(c.careers_page_url || '');
          setEditAts(c.ats_provider || '');
          setEditSector(c.sector || '');
          setEditStage(c.stage || '');
          setEditLocation(c.location || '');
          setEditPriorityTier(c.priority_tier || 2);
          setEditIsVip(c.is_vip === 1);
        }
      } catch (err) {
        console.error('Failed to load company detail', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [companyName, companyId]);

  if (!companyName && !companyId) return null;

  const company = data?.company;
  const jobs = data?.jobs || [];
  const leads = data?.leads || [];

  const handleDeepLoop = async () => {
    if (!company?.company_name) return;
    setLooping(true);
    try {
      const res = await fetch('/api/companies/loop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ companyName: company.company_name }),
      });
      const resJson = await res.json();
      if (resJson.success) {
        // Refresh detail
        const queryParam = `name=${encodeURIComponent(company.company_name)}`;
        const refRes = await fetch(`/api/companies/drilldown?${queryParam}`);
        const refJson = await refRes.json();
        if (refJson.success) {
          setData(refJson.data);
        }
        if (onCompanyUpdated) onCompanyUpdated();
      }
    } catch (err) {
      console.error('Failed to run company loop', err);
    } finally {
      setLooping(false);
    }
  };

  const handleInvestigate = async () => {
    if (!company?.company_name) return;
    setInvestigating(true);
    try {
      const res = await fetch('/api/companies/investigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ companyName: company.company_name }),
      });
      const json = await res.json();
      if (json.success && json.companyData) {
        setData(json.companyData);
        setActiveTab('projects');
        if (onCompanyUpdated) onCompanyUpdated();
      }
    } catch (err) {
      console.error('Failed to investigate company', err);
    } finally {
      setInvestigating(false);
    }
  };

  const handleSave = async () => {
    if (!company?.company_id) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/companies/drilldown?id=${encodeURIComponent(company.company_id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          official_domain: editDomain,
          careers_page_url: editCareersUrl,
          ats_provider: editAts,
          sector: editSector,
          stage: editStage,
          location: editLocation,
          priority_tier: editPriorityTier,
          is_vip: editIsVip ? 1 : 0,
        }),
      });
      const resJson = await res.json();
      if (resJson.success) {
        setData((prev: any) => ({
          ...prev,
          company: {
            ...prev.company,
            official_domain: editDomain,
            careers_page_url: editCareersUrl,
            ats_provider: editAts,
            sector: editSector,
            stage: editStage,
            location: editLocation,
            priority_tier: editPriorityTier,
            is_vip: editIsVip ? 1 : 0,
          },
        }));
        if (onCompanyUpdated) onCompanyUpdated();
      }
    } catch (err) {
      console.error('Failed to update company', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!company?.company_id) return;
    if (!confirm(`Are you sure you want to delete ${company.company_name} from Watchlist?`)) return;
    try {
      const res = await fetch(`/api/companies/drilldown?id=${encodeURIComponent(company.company_id)}`, {
        method: 'DELETE',
      });
      const resJson = await res.json();
      if (resJson.success) {
        if (onCompanyUpdated) onCompanyUpdated();
        onClose();
      }
    } catch (err) {
      console.error('Failed to delete company', err);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedEmail(text);
    setTimeout(() => setCopiedEmail(null), 2000);
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
        {/* Header */}
        <div className="p-6 border-b border-zinc-200/70 bg-white/70 flex items-start justify-between gap-4 relative">
          <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />

          <div className="space-y-2 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              {company?.is_vip === 1 && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1 shadow-2xs">
                  <Star className="w-3 h-3 fill-amber-500 text-amber-600" />
                  VIP Target
                </span>
              )}
              {company?.ats_provider && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-50 text-cyan-800 border border-cyan-200 capitalize">
                  ATS: {company.ats_provider}
                </span>
              )}
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-100 text-zinc-700 border border-zinc-200">
                Tier {company?.priority_tier ?? 2}
              </span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-zinc-900 flex items-center gap-2 truncate">
              <Building2 className="w-5 h-5 text-cyan-600 shrink-0" />
              <span>{company?.company_name || companyName}</span>
            </h2>
            <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-500">
              {company?.official_domain && (
                <span className="flex items-center gap-1 text-zinc-700 font-mono">
                  <Globe className="w-3.5 h-3.5 text-zinc-400" />
                  {company.official_domain}
                </span>
              )}
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                {company?.location || 'Remote'}
              </span>
              <span className="text-zinc-600 font-medium">
                {company?.sector || 'Technology'} • {company?.stage || 'Growth'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {company?.careers_page_url && (
              <a
                href={company.careers_page_url}
                target="_blank"
                rel="noreferrer"
                className="liquid-pill rounded-full p-2 text-zinc-600 hover:text-zinc-950 transition shadow-2xs"
                title="Open Official Careers Board"
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

        {/* Tab Navigation Pill Bar */}
        <div className="flex items-center justify-between px-6 py-2.5 border-b border-zinc-200/60 bg-zinc-50/70 text-xs">
          <div className="flex items-center gap-1 overflow-x-auto">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer ${
                activeTab === 'overview'
                  ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              Intelligence
            </button>
            <button
              onClick={() => setActiveTab('projects')}
              className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'projects'
                  ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              <span>Projects & Tech</span>
              {company?.topProjects && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-blue-100 text-blue-700 font-bold">
                  {company.topProjects.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('roles')}
              className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'roles'
                  ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              <span>Harvested Roles</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-zinc-200/80 text-zinc-700">
                {jobs.length}
              </span>
            </button>
            <button
              onClick={() => setActiveTab('leads')}
              className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
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
              onClick={() => setActiveTab('edit')}
              className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer ${
                activeTab === 'edit'
                  ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              Edit Profile
            </button>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <button
              onClick={handleInvestigate}
              disabled={investigating}
              className="liquid-pill px-3 py-1.5 rounded-xl text-xs font-semibold text-blue-700 hover:text-blue-900 flex items-center gap-1.5 cursor-pointer shadow-2xs border border-blue-200 bg-blue-50/50"
              title="Run deep OSINT investigation on Wikipedia and GitHub open-source repositories"
            >
              <Sparkles className={`w-3.5 h-3.5 text-blue-600 ${investigating ? 'animate-spin' : ''}`} />
              <span>{investigating ? 'Investigating...' : 'Investigate OSINT'}</span>
            </button>

            <button
              onClick={handleDeepLoop}
              disabled={looping}
              className="liquid-pill px-3 py-1.5 rounded-xl text-xs font-semibold text-zinc-800 hover:text-zinc-950 flex items-center gap-1.5 cursor-pointer shadow-2xs"
              title="Harvest new postings & recruiters for this company"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-cyan-600 ${looping ? 'animate-spin' : ''}`} />
              <span>{looping ? 'Looping...' : 'Deep Loop'}</span>
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-20 text-center text-sm text-zinc-400">Loading company dossier...</div>
          ) : (
            <>
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {/* Summary Metric Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="liquid-glass rounded-2xl p-3 border border-white/90 shadow-2xs">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block">Total Open Roles</span>
                      <span className="text-base font-bold text-zinc-900">{jobs.length}</span>
                    </div>
                    <div className="liquid-glass rounded-2xl p-3 border border-white/90 shadow-2xs">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block">Recruiter Leads</span>
                      <span className="text-base font-bold text-emerald-700">{leads.length}</span>
                    </div>
                    <div className="liquid-glass rounded-2xl p-3 border border-white/90 shadow-2xs">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block">ATS Adapter</span>
                      <span className="text-xs font-bold text-zinc-900 capitalize">{company?.ats_provider || 'Direct'}</span>
                    </div>
                    <div className="liquid-glass rounded-2xl p-3 border border-white/90 shadow-2xs">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 block">Last Active</span>
                      <span className="text-xs font-medium text-zinc-700">{company?.last_scraped_at ? new Date(company.last_scraped_at).toLocaleDateString() : 'Active'}</span>
                    </div>
                  </div>

                  {/* Deep Intelligence Dossier */}
                  <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
                      Autonomous Dossier & Ingestion Channels
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-zinc-700 pt-1">
                      <div className="p-3 rounded-xl bg-white/70 border border-zinc-200/60 shadow-2xs">
                        <span className="font-semibold block text-zinc-900 mb-1">ATS Endpoints</span>
                        <p className="text-zinc-600 text-[11.5px] break-all font-mono">
                          {company?.careers_page_url || 'Automatic discovery active'}
                        </p>
                      </div>
                      <div className="p-3 rounded-xl bg-white/70 border border-zinc-200/60 shadow-2xs">
                        <span className="font-semibold block text-zinc-900 mb-1">Corporate Domain & MX</span>
                        <p className="text-zinc-600 text-[11.5px] font-mono">
                          {company?.official_domain ? `Valid MX on @${company.official_domain}` : 'Domain lookup pending'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Wikipedia Corporate Intelligence */}
                  {company?.wikipedia_summary && (
                    <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-2">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-blue-700 flex items-center gap-1.5">
                        <Globe className="w-3.5 h-3.5 text-blue-600" />
                        Verified Corporate Profile (Wikipedia OSINT)
                      </h3>
                      <p className="text-xs text-zinc-700 leading-relaxed">
                        {company.wikipedia_summary}
                      </p>
                    </div>
                  )}

                  {/* Dual-Attack Readiness */}
                  <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-500 block">
                      Autonomous Dual-Attack Status
                    </span>
                    <p className="text-xs text-zinc-600 leading-relaxed">
                      {jobs.length > 0 && leads.length > 0
                        ? `Ready for Dual-Attack. ApplyPilot has mapped official ATS postings alongside verified recruiter contacts. High-fit applications will trigger parallel portal submission and warm email dispatch.`
                        : `Partial readiness. ApplyPilot is monitoring for both official career board openings and verified recruiter leads.`}
                    </p>
                  </div>
                </div>
              )}

              {/* Projects & Tech Radar Tab */}
              {activeTab === 'projects' && (
                <div className="space-y-5">
                  <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-600 flex items-center gap-1.5">
                        <Code2 className="w-4 h-4 text-blue-600" />
                        Engineering Tech Stack & Open-Source Projects
                      </h3>
                      {company?.github_org_url && (
                        <a
                          href={company.github_org_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                        >
                          <span>GitHub Organization</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>

                    {company?.techRadar?.languages && company.techRadar.languages.length > 0 && (
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        <span className="text-xs font-bold text-zinc-700">Primary Languages:</span>
                        {company.techRadar.languages.map((lang: string) => (
                          <span key={lang} className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-800 border border-blue-200">
                            {lang}
                          </span>
                        ))}
                        {company.techRadar.stars_total > 0 && (
                          <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1">
                            ⭐ {company.techRadar.stars_total.toLocaleString()} stars
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {company?.topProjects && company.topProjects.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                      {company.topProjects.map((p: any) => (
                        <div key={p.name} className="liquid-card rounded-2xl p-4 border border-zinc-200/80 bg-white/80 space-y-2">
                          <div className="flex items-start justify-between gap-2">
                            <a
                              href={p.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-bold text-xs text-blue-700 hover:underline flex items-center gap-1"
                            >
                              <Code2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                              <span className="truncate">{p.name}</span>
                            </a>
                            {p.language && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700 border border-zinc-200">
                                {p.language}
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-zinc-600 line-clamp-2 min-h-[30px]">
                            {p.description || 'Core engineering repository and tools.'}
                          </p>
                          <div className="pt-2 border-t border-zinc-100 flex items-center gap-3 text-[10px] text-zinc-500">
                            <span>⭐ {p.stars || 0} stars</span>
                            <span>•</span>
                            <span>🍴 {p.forks || 0} forks</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-8 text-center border border-dashed border-zinc-200 rounded-2xl bg-zinc-50/50 space-y-3">
                      <p className="text-xs text-zinc-500 max-w-md mx-auto">
                        No open-source project intelligence captured yet. Click below to run zero-token OSINT on Wikipedia & GitHub to detect their engineering tools.
                      </p>
                      <button
                        onClick={handleInvestigate}
                        disabled={investigating}
                        className="liquid-pill px-4 py-2 rounded-xl text-xs font-bold text-blue-700 border border-blue-300 bg-white shadow-2xs hover:bg-blue-50 transition cursor-pointer"
                      >
                        {investigating ? 'Investigating...' : 'Investigate Projects & Tech Stack'}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'roles' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                      Open Career Postings ({jobs.length})
                    </span>
                  </div>

                  {jobs.length === 0 ? (
                    <div className="py-12 text-center text-xs text-zinc-500 liquid-glass rounded-2xl p-6">
                      No active listings found for this company yet. Click &quot;Deep Loop&quot; to sweep their careers board.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {jobs.map((j: any) => (
                        <div
                          key={j.url}
                          onClick={() => onOpenJob && onOpenJob(j.url)}
                          className="liquid-row rounded-2xl p-3.5 flex items-center justify-between gap-3 cursor-pointer group"
                        >
                          <div className="space-y-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-xs text-zinc-900 group-hover:text-cyan-700 transition">
                                {j.title}
                              </span>
                              {j.fit_score != null && (
                                <span className={`px-2 py-0.2 rounded-full text-[10px] font-bold border ${
                                  j.fit_score >= 8 ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                                  j.fit_score >= 5 ? 'bg-amber-50 text-amber-800 border-amber-200' :
                                  'bg-rose-50 text-rose-800 border-rose-200'
                                }`}>
                                  Fit: {j.fit_score}/10
                                </span>
                              )}
                              <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-zinc-100 text-zinc-600 border border-zinc-200">
                                {j.execution_route || 'PORTAL_ONLY'}
                              </span>
                            </div>
                            <div className="text-xs text-zinc-500 flex items-center gap-3">
                              <span>{j.location || 'Remote'}</span>
                              {j.salary_raw && <span>• {j.salary_raw}</span>}
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            <AutoApplyButton
                              jobUrl={j.url}
                              initialState={j.state}
                              onApplied={() => {
                                if (onCompanyUpdated) onCompanyUpdated();
                              }}
                            />
                            <ArrowRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 group-hover:text-zinc-900 transition" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'leads' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                      Discovered Recruiter Contacts ({leads.length})
                    </span>
                  </div>

                  {leads.length === 0 ? (
                    <div className="py-12 text-center text-xs text-zinc-500 liquid-glass rounded-2xl p-6">
                      No recruiter contacts discovered yet. Run the email harvester to detect hiring leads.
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
                                {l.contact_name || 'Hiring Lead'}
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

                          <div className="flex items-center gap-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                copyToClipboard(l.contact_email);
                              }}
                              className="p-1 rounded text-zinc-400 hover:text-zinc-800 transition"
                              title="Copy Email"
                            >
                              {copiedEmail === l.contact_email ? (
                                <Check className="w-3.5 h-3.5 text-emerald-600" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                            <ArrowRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 group-hover:text-zinc-900 transition" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'edit' && (
                <div className="space-y-4">
                  <div className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-700">
                      Edit Watchlist Record
                    </h3>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-zinc-600 block mb-1">Official Domain</label>
                        <input
                          type="text"
                          value={editDomain}
                          onChange={(e) => setEditDomain(e.target.value)}
                          placeholder="company.com"
                          className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs font-mono"
                        />
                      </div>

                      <div>
                        <label className="text-xs font-semibold text-zinc-600 block mb-1">ATS Provider</label>
                        <input
                          type="text"
                          value={editAts}
                          onChange={(e) => setEditAts(e.target.value)}
                          placeholder="greenhouse / lever / ashby"
                          className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-600 block mb-1">Careers Board URL</label>
                      <input
                        type="url"
                        value={editCareersUrl}
                        onChange={(e) => setEditCareersUrl(e.target.value)}
                        placeholder="https://company.com/careers"
                        className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs font-mono"
                      />
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-zinc-600 block mb-1">Sector</label>
                        <input
                          type="text"
                          value={editSector}
                          onChange={(e) => setEditSector(e.target.value)}
                          placeholder="Fintech"
                          className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                        />
                      </div>

                      <div>
                        <label className="text-xs font-semibold text-zinc-600 block mb-1">Location</label>
                        <input
                          type="text"
                          value={editLocation}
                          onChange={(e) => setEditLocation(e.target.value)}
                          placeholder="Bengaluru / Remote"
                          className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                        />
                      </div>

                      <div>
                        <label className="text-xs font-semibold text-zinc-600 block mb-1">Priority Tier</label>
                        <select
                          value={editPriorityTier}
                          onChange={(e) => setEditPriorityTier(Number(e.target.value))}
                          className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                        >
                          <option value="1">Tier 1 (Priority)</option>
                          <option value="2">Tier 2 (Standard)</option>
                          <option value="3">Tier 3 (Backlog)</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <input
                        type="checkbox"
                        id="vip-checkbox"
                        checked={editIsVip}
                        onChange={(e) => setEditIsVip(e.target.checked)}
                        className="rounded border-zinc-300 text-purple-600 focus:ring-purple-500"
                      />
                      <label htmlFor="vip-checkbox" className="text-xs font-semibold text-zinc-800 cursor-pointer">
                        Mark as VIP Target (High Priority Notification & Recruiter Outreach)
                      </label>
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-zinc-200/70">
                      <button
                        onClick={handleDelete}
                        type="button"
                        className="px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition flex items-center gap-1.5 cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete Company
                      </button>

                      <button
                        onClick={handleSave}
                        disabled={saving}
                        type="button"
                        className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
                      >
                        <Save className="w-3.5 h-3.5" />
                        {saving ? 'Saving...' : 'Save Profile'}
                      </button>
                    </div>
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
