'use client';

import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Briefcase,
  Building2,
  Users,
  Search,
  Bell,
  ArrowUpRight,
  ExternalLink,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  Filter,
  Sparkles,
  Radio,
  Mail,
  Zap,
  ShieldCheck,
  MapPin,
  RefreshCw,
  SlidersHorizontal,
  Compass,
  X,
  Send,
  Layers,
  Activity,
  GitBranch,
} from 'lucide-react';
import { AgentRadarView } from '@/components/agent-radar/AgentRadarView';
import { SourceBadge } from '@/components/ui/SourceBadge';
import { RouteBadge } from '@/components/ui/RouteBadge';

interface StatsData {
  totalJobs: number;
  totalCompanies: number;
  totalLeads: number;
  vipCompanies: number;
  routes: {
    dualAttack: number;
    portalOnly: number;
    emailOnly: number;
  };
  topAts: Array<{ provider: string; count: number }>;
  topSectors: Array<{ sector: string; count: number }>;
  recentJobs: any[];
  recentLeads: any[];
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'jobs' | 'companies' | 'leads' | 'radar'>('overview');
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Jobs state
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobSearch, setJobSearch] = useState('');
  const [jobRoute, setJobRoute] = useState('ALL');
  const [jobPage, setJobPage] = useState(1);
  const [jobPagination, setJobPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [jobsLoading, setJobsLoading] = useState(false);

  // Companies state
  const [companies, setCompanies] = useState<any[]>([]);
  const [companySearch, setCompanySearch] = useState('');
  const [companyVipOnly, setCompanyVipOnly] = useState(false);
  const [companyPage, setCompanyPage] = useState(1);
  const [companyPagination, setCompanyPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [companiesLoading, setCompaniesLoading] = useState(false);

  // Leads state
  const [leads, setLeads] = useState<any[]>([]);
  const [leadSearch, setLeadSearch] = useState('');
  const [leadType, setLeadType] = useState('ALL');
  const [leadPage, setLeadPage] = useState(1);
  const [leadPagination, setLeadPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [leadsLoading, setLeadsLoading] = useState(false);

  // Company Drill-Down Modal State
  const [selectedCompany, setSelectedCompany] = useState<any | null>(null);
  const [drilldownData, setDrilldownData] = useState<any | null>(null);
  const [drilldownLoading, setDrilldownLoading] = useState(false);
  const [drawerTab, setDrawerTab] = useState<'leads' | 'jobs'>('leads');
  const [copiedAllEmails, setCopiedAllEmails] = useState(false);

  const openCompanyDrilldown = async (company: any) => {
    setSelectedCompany(company);
    setDrilldownLoading(true);
    setDrawerTab('leads');
    try {
      const res = await fetch(`/api/companies/drilldown?name=${encodeURIComponent(company.company_name)}`);
      const data = await res.json();
      if (data.success) {
        setDrilldownData(data.data);
      }
    } catch (err) {
      console.error('Failed to load company drilldown', err);
    } finally {
      setDrilldownLoading(false);
    }
  };

  const copyAllEmails = (emails: string[]) => {
    if (!emails || emails.length === 0) return;
    navigator.clipboard.writeText(emails.join(', '));
    setCopiedAllEmails(true);
    setTimeout(() => setCopiedAllEmails(false), 2500);
  };

  // Load overview stats
  const fetchStats = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/stats');
      const data = await res.json();
      if (data.success) {
        setStats(data.data);
      }
    } catch (err) {
      console.error('Failed to load stats', err);
    } finally {
      setLoading(false);
    }
  };

  // Load jobs
  const fetchJobs = async (page = 1, search = jobSearch, route = jobRoute) => {
    try {
      setJobsLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        limit: '20',
      });
      if (search) params.set('search', search);
      if (route && route !== 'ALL') params.set('route', route);

      const res = await fetch(`/api/jobs?${params.toString()}`);
      const data = await res.json();
      if (data.success) {
        setJobs(data.jobs);
        setJobPagination(data.pagination);
        setJobPage(data.pagination.page);
      }
    } catch (err) {
      console.error('Failed to load jobs', err);
    } finally {
      setJobsLoading(false);
    }
  };

  // Load companies
  const fetchCompanies = async (page = 1, search = companySearch, vip = companyVipOnly) => {
    try {
      setCompaniesLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        limit: '20',
      });
      if (search) params.set('search', search);
      if (vip) params.set('vip', 'true');

      const res = await fetch(`/api/companies?${params.toString()}`);
      const data = await res.json();
      if (data.success) {
        setCompanies(data.companies);
        setCompanyPagination(data.pagination);
        setCompanyPage(data.pagination.page);
      }
    } catch (err) {
      console.error('Failed to load companies', err);
    } finally {
      setCompaniesLoading(false);
    }
  };

  // Load leads
  const fetchLeads = async (page = 1, search = leadSearch, type = leadType) => {
    try {
      setLeadsLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        limit: '20',
      });
      if (search) params.set('search', search);
      if (type && type !== 'ALL') params.set('type', type);

      const res = await fetch(`/api/leads?${params.toString()}`);
      const data = await res.json();
      if (data.success) {
        setLeads(data.leads);
        setLeadPagination(data.pagination);
        setLeadPage(data.pagination.page);
      }
    } catch (err) {
      console.error('Failed to load leads', err);
    } finally {
      setLeadsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    if (activeTab === 'jobs') fetchJobs(1);
    if (activeTab === 'companies') fetchCompanies(1);
    if (activeTab === 'leads') fetchLeads(1);
  }, [activeTab]);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex min-h-screen p-4 md:p-6 lg:p-8 gap-6 max-w-[1600px] mx-auto">
      {/* ----------------- SIDEBAR ----------------- */}
      <aside className="w-64 shrink-0 flex flex-col gap-6">
        {/* Brand Liquid Glass Card */}
        <div className="liquid-glass rounded-3xl p-6 flex flex-col gap-8">
          {/* Logo & Orb */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full orb-peach shrink-0 flex items-center justify-center" />
            <div className="flex flex-col">
              <span className="font-semibold text-lg tracking-tight text-zinc-900">ApplyPilot</span>
              <span className="text-xs text-zinc-400 font-medium tracking-wide">AUTONOMOUS AGENT</span>
            </div>
          </div>

          {/* Navigation Items */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 px-3 mb-2">
              Navigation
            </span>

            <button
              onClick={() => setActiveTab('overview')}
              className={`flex items-center justify-between px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                activeTab === 'overview'
                  ? 'liquid-glass shadow-[0_4px_16px_rgba(0,0,0,0.04)] text-zinc-950 font-semibold border-white/95 scale-[1.01]'
                  : 'text-zinc-600 hover:text-zinc-950 hover:bg-white/50 hover:shadow-xs'
              }`}
            >
              <div className="flex items-center gap-3">
                <LayoutDashboard className="w-4 h-4 text-purple-600" />
                <span>Dashboard</span>
              </div>
            </button>

            <button
              onClick={() => setActiveTab('jobs')}
              className={`flex items-center justify-between px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                activeTab === 'jobs'
                  ? 'liquid-glass shadow-[0_4px_16px_rgba(0,0,0,0.04)] text-zinc-950 font-semibold border-white/95 scale-[1.01]'
                  : 'text-zinc-600 hover:text-zinc-950 hover:bg-white/50 hover:shadow-xs'
              }`}
            >
              <div className="flex items-center gap-3">
                <Briefcase className="w-4 h-4 text-blue-600" />
                <span>All Jobs</span>
              </div>
              {stats?.totalJobs ? (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200/50">
                  {stats.totalJobs.toLocaleString()}
                </span>
              ) : null}
            </button>

            <button
              onClick={() => setActiveTab('companies')}
              className={`flex items-center justify-between px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                activeTab === 'companies'
                  ? 'liquid-glass shadow-[0_4px_16px_rgba(0,0,0,0.04)] text-zinc-950 font-semibold border-white/95 scale-[1.01]'
                  : 'text-zinc-600 hover:text-zinc-950 hover:bg-white/50 hover:shadow-xs'
              }`}
            >
              <div className="flex items-center gap-3">
                <Building2 className="w-4 h-4 text-amber-600" />
                <span>Companies</span>
              </div>
              {stats?.totalCompanies ? (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/50">
                  {stats.totalCompanies.toLocaleString()}
                </span>
              ) : null}
            </button>

            <button
              onClick={() => setActiveTab('leads')}
              className={`flex items-center justify-between px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                activeTab === 'leads'
                  ? 'liquid-glass shadow-[0_4px_16px_rgba(0,0,0,0.04)] text-zinc-950 font-semibold border-white/95 scale-[1.01]'
                  : 'text-zinc-600 hover:text-zinc-950 hover:bg-white/50 hover:shadow-xs'
              }`}
            >
              <div className="flex items-center gap-3">
                <Users className="w-4 h-4 text-emerald-600" />
                <span>Contacts & Leads</span>
              </div>
              {stats?.totalLeads ? (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/50">
                  {stats.totalLeads.toLocaleString()}
                </span>
              ) : null}
            </button>

            <button
              onClick={() => setActiveTab('radar')}
              className={`flex items-center justify-between px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                activeTab === 'radar'
                  ? 'liquid-glass shadow-[0_4px_16px_rgba(0,0,0,0.04)] text-zinc-950 font-semibold border-white/95 scale-[1.01]'
                  : 'text-zinc-600 hover:text-zinc-950 hover:bg-white/50 hover:shadow-xs'
              }`}
            >
              <div className="flex items-center gap-3">
                <GitBranch className="w-4 h-4 text-purple-600" />
                <span>Agent Radar</span>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200/60 shadow-xs">
                LIVE DAG
              </span>
            </button>
          </div>
        </div>

        {/* System Looper Status Card */}
        <div className="liquid-glass rounded-3xl p-5 flex flex-col gap-4 text-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 px-1">
            Looper Engine
          </span>

          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="text-zinc-500">Tier 1 Sweep</span>
              <span className="font-medium text-emerald-600 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Every 6h
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-zinc-500">ATS Feeds</span>
              <span className="font-medium text-zinc-800">11 Platforms</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-zinc-500">Email Synthesis</span>
              <span className="font-medium text-zinc-800">DoH MX Active</span>
            </div>
          </div>

          <div className="pt-2 border-t border-zinc-200/60 flex items-center justify-between text-zinc-400">
            <span>DB: SQLite WAL</span>
            <span className="font-mono text-[10px]">100% Local</span>
          </div>
        </div>
      </aside>

      {/* ----------------- MAIN CONTENT AREA ----------------- */}
      <main className="flex-1 flex flex-col gap-6 min-w-0">
        {/* Top Header / Search & Profile Bar */}
        <header className="flex items-center justify-between gap-4">
          {/* Frosted Pill Search */}
          <div className="liquid-glass rounded-full px-5 py-2.5 flex items-center gap-3 max-w-md w-full shadow-sm hover:shadow-md transition-all relative overflow-hidden group">
            <div className="absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />
            <Search className="w-4 h-4 text-zinc-400 shrink-0 group-hover:text-purple-600 transition-colors" />
            <input
              type="text"
              placeholder="Search jobs, startups, or recruiter emails..."
              className="bg-transparent border-none outline-none text-sm text-zinc-800 placeholder:text-zinc-400 w-full"
              value={activeTab === 'jobs' ? jobSearch : activeTab === 'companies' ? companySearch : leadSearch}
              onChange={(e) => {
                const val = e.target.value;
                if (activeTab === 'jobs') {
                  setJobSearch(val);
                  fetchJobs(1, val);
                } else if (activeTab === 'companies') {
                  setCompanySearch(val);
                  fetchCompanies(1, val);
                } else {
                  setLeadSearch(val);
                  fetchLeads(1, val);
                }
              }}
            />
          </div>

          {/* Header Right Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                fetchStats();
                if (activeTab === 'jobs') fetchJobs(jobPage);
                if (activeTab === 'companies') fetchCompanies(companyPage);
                if (activeTab === 'leads') fetchLeads(leadPage);
              }}
              title="Refresh Data"
              className="liquid-pill rounded-full w-10 h-10 flex items-center justify-center text-zinc-600 hover:text-zinc-950 transition-all shadow-sm cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {/* User Avatar */}
            <div className="liquid-pill rounded-full pl-2 pr-4 py-1.5 flex items-center gap-2.5 shadow-sm cursor-pointer">
              <div className="w-7 h-7 rounded-full orb-peach flex items-center justify-center text-white text-xs font-semibold shadow-inner">
                SB
              </div>
              <span className="text-sm font-semibold text-zinc-800">Sameer Bagul</span>
            </div>
          </div>
        </header>

        {/* ----------------- TAB: OVERVIEW ----------------- */}
        {activeTab === 'overview' && (
          <div className="flex flex-col gap-6">
            {/* Hero Greeting Card (Reference Image Style) */}
            <div className="liquid-glass rounded-3xl p-8 flex flex-col items-center justify-center text-center gap-4 relative overflow-hidden shadow-sm">
              <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />
              <div className="w-14 h-14 rounded-full orb-peach shrink-0 shadow-lg mb-1" />
              <div className="flex flex-col gap-1 max-w-xl">
                <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-zinc-900">
                  Good Morning <span className="font-bold text-zinc-950">Sameer</span>, {stats?.totalJobs ? `${stats.totalJobs.toLocaleString()} live openings` : 'ready for discovery'}.
                </h1>
                <p className="text-sm text-zinc-500">
                  {stats?.totalLeads ? stats.totalLeads.toLocaleString() : 0} verified recruiter and founder contacts synthesized across {stats?.totalCompanies || 0} watchlist startups.
                </p>
              </div>

              {/* Minimalist Filter Pills */}
              <div className="flex items-center flex-wrap justify-center gap-2 mt-2">
                <button
                  onClick={() => setActiveTab('jobs')}
                  className="liquid-pill rounded-full px-4 py-1.5 text-xs font-semibold bg-zinc-950 text-white shadow-md hover:bg-zinc-800 transition-all cursor-pointer"
                >
                  All Openings ({stats?.totalJobs || 0})
                </button>
                <button
                  onClick={() => {
                    setActiveTab('companies');
                    setCompanyVipOnly(true);
                  }}
                  className="liquid-pill rounded-full px-4 py-1.5 text-xs font-medium text-zinc-700 hover:text-zinc-950 transition-all cursor-pointer shadow-xs"
                >
                  VIP Watchlist ({stats?.vipCompanies || 0})
                </button>
                <button
                  onClick={() => {
                    setActiveTab('jobs');
                    setJobRoute('DUAL_ATTACK');
                  }}
                  className="liquid-pill rounded-full px-4 py-1.5 text-xs font-medium text-zinc-700 hover:text-zinc-950 transition-all cursor-pointer shadow-xs"
                >
                  Dual-Attack Ready ({stats?.routes.dualAttack || 0})
                </button>
                <button
                  onClick={() => setActiveTab('leads')}
                  className="liquid-pill rounded-full px-4 py-1.5 text-xs font-medium text-zinc-700 hover:text-zinc-950 transition-all cursor-pointer shadow-xs"
                >
                  Founder & HR Leads ({stats?.totalLeads || 0})
                </button>
              </div>
            </div>

            {/* Visual Glass Cards (Reference Image Meditate / Music / Move Style) */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
              {/* Card 1: VIP Watchlist */}
              <div
                onClick={() => setActiveTab('companies')}
                className="liquid-glass rounded-3xl p-5 flex flex-col justify-between h-48 cursor-pointer group hover:shadow-md hover:scale-[1.01] transition-all relative overflow-hidden"
              >
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
                <div className="absolute inset-x-0 top-0 h-20 mesh-gradient-1 opacity-70 group-hover:opacity-90 transition-opacity" />
                <div className="relative z-10 flex justify-between items-start">
                  <div className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center shadow-sm">
                    <Building2 className="w-4 h-4 text-zinc-800" />
                  </div>
                  <div className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                    <ArrowUpRight className="w-4 h-4 text-zinc-800" />
                  </div>
                </div>
                <div className="relative z-10 flex flex-col">
                  <span className="text-2xl font-bold tracking-tight text-zinc-900">
                    {stats?.totalCompanies || 0}
                  </span>
                  <span className="text-sm font-medium text-zinc-600">Watchlist Startups</span>
                  <span className="text-[11px] text-zinc-400 mt-0.5">{stats?.vipCompanies || 0} Tier-1 VIP Top 500</span>
                </div>
              </div>

              {/* Card 2: Verified Leads */}
              <div
                onClick={() => setActiveTab('leads')}
                className="liquid-glass rounded-3xl p-5 flex flex-col justify-between h-48 cursor-pointer group hover:shadow-md hover:scale-[1.01] transition-all relative overflow-hidden"
              >
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
                <div className="absolute inset-x-0 top-0 h-20 mesh-gradient-2 opacity-70 group-hover:opacity-90 transition-opacity" />
                <div className="relative z-10 flex justify-between items-start">
                  <div className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center shadow-sm">
                    <Mail className="w-4 h-4 text-zinc-800" />
                  </div>
                  <div className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                    <ArrowUpRight className="w-4 h-4 text-zinc-800" />
                  </div>
                </div>
                <div className="relative z-10 flex flex-col">
                  <span className="text-2xl font-bold tracking-tight text-zinc-900">
                    {stats?.totalLeads || 0}
                  </span>
                  <span className="text-sm font-medium text-zinc-600">Verified Contacts</span>
                  <span className="text-[11px] text-zinc-400 mt-0.5">5-15 emails per company</span>
                </div>
              </div>

              {/* Card 3: Dual-Attack Routing */}
              <div
                onClick={() => {
                  setActiveTab('jobs');
                  setJobRoute('DUAL_ATTACK');
                }}
                className="liquid-glass rounded-3xl p-5 flex flex-col justify-between h-48 cursor-pointer group hover:shadow-md hover:scale-[1.01] transition-all relative overflow-hidden"
              >
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
                <div className="absolute inset-x-0 top-0 h-20 mesh-gradient-3 opacity-70 group-hover:opacity-90 transition-opacity" />
                <div className="relative z-10 flex justify-between items-start">
                  <div className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center shadow-sm">
                    <Zap className="w-4 h-4 text-zinc-800" />
                  </div>
                  <div className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                    <ArrowUpRight className="w-4 h-4 text-zinc-800" />
                  </div>
                </div>
                <div className="relative z-10 flex flex-col">
                  <span className="text-2xl font-bold tracking-tight text-zinc-900">
                    {stats?.routes.dualAttack || 0}
                  </span>
                  <span className="text-sm font-medium text-zinc-600">Dual-Attack Queue</span>
                  <span className="text-[11px] text-zinc-400 mt-0.5">Portal Form + Founder Email</span>
                </div>
              </div>

              {/* Card 4: Autonomous Agent Radar */}
              <div
                onClick={() => setActiveTab('radar')}
                className="liquid-glass rounded-3xl p-5 flex flex-col justify-between h-48 cursor-pointer group hover:shadow-md hover:scale-[1.01] transition-all relative overflow-hidden"
              >
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
                <div className="absolute inset-x-0 top-0 h-20 mesh-gradient-4 opacity-70 group-hover:opacity-90 transition-opacity" />
                <div className="relative z-10 flex justify-between items-start">
                  <div className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center shadow-sm">
                    <GitBranch className="w-4 h-4 text-purple-600" />
                  </div>
                  <div className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                    <ArrowUpRight className="w-4 h-4 text-zinc-800" />
                  </div>
                </div>
                <div className="relative z-10 flex flex-col">
                  <span className="text-2xl font-bold tracking-tight text-zinc-900">6 Lanes</span>
                  <span className="text-sm font-medium text-zinc-600">Autonomous Agent DAG</span>
                  <span className="text-[11px] text-purple-600 font-medium mt-0.5">Live Real-Time Radar</span>
                </div>
              </div>
            </div>

            {/* Two-Column Deep Feed: Recent High-Fit Jobs + Discovered Leads */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Column: Recent Jobs Stream */}
              <div className="liquid-glass rounded-3xl p-6 flex flex-col gap-4 relative overflow-hidden shadow-sm">
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
                <div className="flex items-center justify-between pb-3 border-b border-zinc-200/50">
                  <div className="flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-purple-600" />
                    <h2 className="font-semibold text-zinc-900 text-sm">Recently Discovered Roles</h2>
                  </div>
                  <button
                    onClick={() => setActiveTab('jobs')}
                    className="liquid-pill rounded-full px-3 py-1 text-xs font-semibold text-zinc-600 hover:text-zinc-950 flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                  >
                    <span>View all ({stats?.totalJobs || 0})</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex flex-col gap-2.5">
                  {stats?.recentJobs?.map((job, idx) => (
                    <div
                      key={idx}
                      className="liquid-row rounded-2xl p-3.5 flex items-center justify-between gap-4 group cursor-default"
                    >
                      <div className="flex flex-col min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-sm text-zinc-900 truncate group-hover:text-purple-950 transition-colors">
                            {job.title || 'Software Role'}
                          </span>
                          <RouteBadge route={job.execution_route} compact={true} />
                        </div>
                        <div className="flex items-center gap-2 text-xs text-zinc-500 mt-1 flex-wrap">
                          <span className="font-medium text-zinc-700">{job.company || 'Startup'}</span>
                          <span>•</span>
                          <span className="truncate">{job.location || 'Bengaluru / Remote'}</span>
                          <span>•</span>
                          <SourceBadge site={job.site} compact={false} />
                        </div>
                      </div>

                      <a
                        href={job.url}
                        target="_blank"
                        rel="noreferrer"
                        className="liquid-pill rounded-full px-3.5 py-1.5 text-xs font-semibold text-zinc-800 hover:text-zinc-950 flex items-center gap-1 shrink-0 shadow-xs transition-all cursor-pointer"
                      >
                        <span>Apply</span>
                        <ArrowUpRight className="w-3 h-3 text-zinc-500 group-hover:text-zinc-900" />
                      </a>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Column: Recent Discovered Leads */}
              <div className="liquid-glass rounded-3xl p-6 flex flex-col gap-4 relative overflow-hidden shadow-sm">
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
                <div className="flex items-center justify-between pb-3 border-b border-zinc-200/50">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-emerald-600" />
                    <h2 className="font-semibold text-zinc-900 text-sm">Discovered Recruiters & Founders</h2>
                  </div>
                  <button
                    onClick={() => setActiveTab('leads')}
                    className="liquid-pill rounded-full px-3 py-1 text-xs font-semibold text-zinc-600 hover:text-zinc-950 flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                  >
                    <span>View all ({stats?.totalLeads || 0})</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex flex-col gap-2.5">
                  {stats?.recentLeads?.map((lead, idx) => (
                    <div
                      key={idx}
                      className="liquid-row rounded-2xl p-3.5 flex items-center justify-between gap-4 group cursor-default"
                    >
                      <div className="flex flex-col min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm text-zinc-900 truncate">
                            {lead.contact_name || lead.role_title}
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-zinc-100/90 text-zinc-600 border border-zinc-200/60 shrink-0">
                            {lead.contact_type || 'lead'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-zinc-500 mt-1">
                          <span className="font-mono text-zinc-700 truncate">{lead.contact_email}</span>
                          <span>•</span>
                          <span className="text-zinc-800 font-medium">{lead.company_name}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <button
                          onClick={() => copyToClipboard(lead.contact_email, `email-${idx}`)}
                          title="Copy Email"
                          className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center text-zinc-600 hover:text-zinc-950 transition-all shadow-xs cursor-pointer"
                        >
                          {copiedId === `email-${idx}` ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                        {lead.contact_linkedin_url && (
                          <a
                            href={lead.contact_linkedin_url}
                            target="_blank"
                            rel="noreferrer"
                            title="LinkedIn Profile"
                            className="liquid-pill rounded-full w-8 h-8 flex items-center justify-center text-zinc-600 hover:text-zinc-950 transition-all shadow-xs cursor-pointer"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ----------------- TAB: ALL JOBS ----------------- */}
        {activeTab === 'jobs' && (
          <div className="liquid-glass rounded-3xl p-6 flex flex-col gap-6 relative overflow-hidden shadow-sm">
            <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
            {/* Header & Filter Controls */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-zinc-200/60">
              <div className="flex flex-col">
                <h2 className="text-lg font-semibold text-zinc-900 tracking-tight">Active Job Openings</h2>
                <p className="text-xs text-zinc-500 mt-0.5">
                  Showing {jobs.length} of {jobPagination.total.toLocaleString()} opportunities indexed
                </p>
              </div>

              {/* Execution Route Filter Pills */}
              <div className="flex items-center gap-2 flex-wrap">
                {['ALL', 'DUAL_ATTACK', 'PORTAL_ONLY', 'EMAIL_ONLY'].map((route) => (
                  <button
                    key={route}
                    onClick={() => {
                      setJobRoute(route);
                      fetchJobs(1, jobSearch, route);
                    }}
                    className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                      jobRoute === route
                        ? 'liquid-pill-dark shadow-md'
                        : 'liquid-pill text-zinc-600 hover:text-zinc-950 shadow-xs'
                    }`}
                  >
                    {route === 'ALL' ? 'All Routes' : route}
                  </button>
                ))}
              </div>
            </div>

            {/* Jobs Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-separate border-spacing-y-2.5">
                <thead>
                  <tr className="text-xs font-medium text-zinc-400">
                    <th className="pb-2 px-4">Role Title</th>
                    <th className="pb-2 px-4">Company</th>
                    <th className="pb-2 px-4">Location</th>
                    <th className="pb-2 px-4">Source / ATS</th>
                    <th className="pb-2 px-4">Route</th>
                    <th className="pb-2 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {jobsLoading ? (
                    <tr>
                      <td colSpan={6} className="text-center py-16 text-zinc-400 text-xs">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <div className="w-5 h-5 rounded-full border-2 border-zinc-300 border-t-zinc-800 animate-spin" />
                          <span>Loading openings from local database...</span>
                        </div>
                      </td>
                    </tr>
                  ) : jobs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-16 text-zinc-400 text-xs">
                        No jobs found matching your criteria.
                      </td>
                    </tr>
                  ) : (
                    jobs.map((job, idx) => (
                      <tr key={idx} className="liquid-row rounded-2xl group cursor-default">
                        <td className="py-3.5 px-4 font-semibold text-zinc-900 rounded-l-2xl">
                          <span className="truncate block max-w-xs md:max-w-md group-hover:text-purple-950 transition-colors">
                            {job.title}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-zinc-700 font-medium">{job.company || 'Company'}</td>
                        <td className="py-3.5 px-4 text-zinc-500 text-xs">
                          <div className="flex items-center gap-1.5 truncate max-w-xs">
                            <MapPin className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                            <span>{job.location || 'Remote'}</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <SourceBadge site={job.site} />
                        </td>
                        <td className="py-3.5 px-4">
                          <RouteBadge route={job.execution_route} />
                        </td>
                        <td className="py-3.5 px-4 text-right rounded-r-2xl">
                          <a
                            href={job.url}
                            target="_blank"
                            rel="noreferrer"
                            className="liquid-pill-dark inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold cursor-pointer"
                          >
                            <span>Apply</span>
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </a>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between pt-4 border-t border-zinc-200/60 text-xs text-zinc-500">
              <span>
                Page <span className="font-semibold text-zinc-800">{jobPagination.page}</span> of {jobPagination.totalPages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={jobPagination.page <= 1 || jobsLoading}
                  onClick={() => fetchJobs(jobPage - 1)}
                  className="liquid-pill rounded-full px-3.5 py-1.5 font-medium disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>
                <button
                  disabled={jobPagination.page >= jobPagination.totalPages || jobsLoading}
                  onClick={() => fetchJobs(jobPage + 1)}
                  className="liquid-pill rounded-full px-3.5 py-1.5 font-medium disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ----------------- TAB: COMPANIES (WATCHLIST) ----------------- */}
        {activeTab === 'companies' && (
          <div className="liquid-glass rounded-3xl p-6 flex flex-col gap-6 relative overflow-hidden shadow-sm">
            <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-zinc-200/60">
              <div className="flex flex-col">
                <h2 className="text-lg font-semibold text-zinc-900 tracking-tight">Career Watchlist & VIP Startups</h2>
                <p className="text-xs text-zinc-500 mt-0.5">
                  Showing {companies.length} of {companyPagination.total.toLocaleString()} monitored companies
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    const nextVip = !companyVipOnly;
                    setCompanyVipOnly(nextVip);
                    fetchCompanies(1, companySearch, nextVip);
                  }}
                  className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                    companyVipOnly
                      ? 'liquid-pill-dark shadow-md'
                      : 'liquid-pill text-zinc-600 hover:text-zinc-950 shadow-xs'
                  }`}
                >
                  VIP Top-500 Only
                </button>
              </div>
            </div>

            {/* Companies Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-separate border-spacing-y-2.5">
                <thead>
                  <tr className="text-xs font-medium text-zinc-400">
                    <th className="pb-2 px-4">Company Name</th>
                    <th className="pb-2 px-4">Stage & Funding</th>
                    <th className="pb-2 px-4">Sector</th>
                    <th className="pb-2 px-4">Hub / Area</th>
                    <th className="pb-2 px-4">ATS Provider</th>
                    <th className="pb-2 px-4 text-center">Open Roles</th>
                    <th className="pb-2 px-4 text-center">Verified Outreach</th>
                    <th className="pb-2 px-4 text-right">Drill Down</th>
                  </tr>
                </thead>
                <tbody>
                  {companiesLoading ? (
                    <tr>
                      <td colSpan={8} className="text-center py-16 text-zinc-400 text-xs">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <div className="w-5 h-5 rounded-full border-2 border-zinc-300 border-t-zinc-800 animate-spin" />
                          <span>Loading companies from watchlist...</span>
                        </div>
                      </td>
                    </tr>
                  ) : companies.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="text-center py-16 text-zinc-400 text-xs">
                        No companies found.
                      </td>
                    </tr>
                  ) : (
                    companies.map((c, idx) => (
                      <tr key={idx} className="liquid-row rounded-2xl group cursor-default">
                        <td className="py-3.5 px-4 font-semibold text-zinc-900 rounded-l-2xl">
                          <div className="flex items-center gap-2">
                            <span className="group-hover:text-amber-950 transition-colors">{c.company_name}</span>
                            {c.is_vip === 1 && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60 shrink-0">
                                VIP
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-xs text-zinc-600 font-medium">
                          {c.stage || 'Funded'}
                        </td>
                        <td className="py-3.5 px-4 text-xs text-zinc-600">{c.sector || 'Technology'}</td>
                        <td className="py-3.5 px-4 text-xs text-zinc-500">{c.area || c.location || 'Bengaluru'}</td>
                        <td className="py-3.5 px-4 text-xs font-mono text-zinc-600">
                          {c.ats_provider || 'Direct'}
                        </td>
                        <td className="py-3.5 px-4 text-center font-bold text-zinc-800">
                          {c.open_roles_count || 0}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <button
                            onClick={() => openCompanyDrilldown(c)}
                            className="liquid-pill inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-50/80 text-rose-700 hover:bg-rose-100 border border-rose-200/60 transition-all cursor-pointer shadow-xs"
                          >
                            <Mail className="w-3.5 h-3.5 text-rose-500" />
                            <span>{c.emails?.length ? `${c.emails.length} Inboxes` : '8+ Inboxes'}</span>
                          </button>
                        </td>
                        <td className="py-3.5 px-4 text-right rounded-r-2xl">
                          <button
                            onClick={() => openCompanyDrilldown(c)}
                            className="liquid-pill inline-flex items-center gap-1 text-xs font-semibold text-zinc-800 hover:text-zinc-950 px-3.5 py-1.5 rounded-full shadow-xs cursor-pointer"
                          >
                            <span>Explore</span>
                            <ArrowUpRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-950" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between pt-4 border-t border-zinc-200/60 text-xs text-zinc-500">
              <span>
                Page <span className="font-semibold text-zinc-800">{companyPagination.page}</span> of {companyPagination.totalPages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={companyPagination.page <= 1 || companiesLoading}
                  onClick={() => fetchCompanies(companyPage - 1)}
                  className="liquid-pill rounded-full px-3.5 py-1.5 font-medium disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>
                <button
                  disabled={companyPagination.page >= companyPagination.totalPages || companiesLoading}
                  onClick={() => fetchCompanies(companyPage + 1)}
                  className="liquid-pill rounded-full px-3.5 py-1.5 font-medium disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ----------------- TAB: CONTACTS & EMAILS ----------------- */}
        {activeTab === 'leads' && (
          <div className="liquid-glass rounded-3xl p-6 flex flex-col gap-6 relative overflow-hidden shadow-sm">
            <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-zinc-200/60">
              <div className="flex flex-col">
                <h2 className="text-lg font-semibold text-zinc-900 tracking-tight">Verified Recruiter & Founder Leads</h2>
                <p className="text-xs text-zinc-500 mt-0.5">
                  Showing {leads.length} of {leadPagination.total.toLocaleString()} synthesized contacts
                </p>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {['ALL', 'founder', 'recruiter', 'inbox'].map((type) => (
                  <button
                    key={type}
                    onClick={() => {
                      setLeadType(type);
                      fetchLeads(1, leadSearch, type);
                    }}
                    className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                      leadType === type
                        ? 'liquid-pill-dark shadow-md'
                        : 'liquid-pill text-zinc-600 hover:text-zinc-950 shadow-xs'
                    }`}
                  >
                    {type === 'ALL' ? 'All Contacts' : type.charAt(0).toUpperCase() + type.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Leads Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-separate border-spacing-y-2.5">
                <thead>
                  <tr className="text-xs font-medium text-zinc-400">
                    <th className="pb-2 px-4">Contact & Title</th>
                    <th className="pb-2 px-4">Company</th>
                    <th className="pb-2 px-4">Verified Email</th>
                    <th className="pb-2 px-4">Type</th>
                    <th className="pb-2 px-4">LinkedIn Note (≤280 chars)</th>
                    <th className="pb-2 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {leadsLoading ? (
                    <tr>
                      <td colSpan={6} className="text-center py-16 text-zinc-400 text-xs">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <div className="w-5 h-5 rounded-full border-2 border-zinc-300 border-t-zinc-800 animate-spin" />
                          <span>Loading leads from database...</span>
                        </div>
                      </td>
                    </tr>
                  ) : leads.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-16 text-zinc-400 text-xs">
                        No contacts found.
                      </td>
                    </tr>
                  ) : (
                    leads.map((l, idx) => (
                      <tr key={idx} className="liquid-row rounded-2xl group cursor-default">
                        <td className="py-3.5 px-4 font-semibold text-zinc-900 rounded-l-2xl">
                          <div className="flex flex-col">
                            <span className="group-hover:text-emerald-950 transition-colors">
                              {l.contact_name || l.role_title}
                            </span>
                            {l.contact_name && (
                              <span className="text-xs text-zinc-500 font-normal">{l.role_title}</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-zinc-700">{l.company_name}</td>
                        <td className="py-3.5 px-4 text-xs font-mono text-zinc-800">
                          <div className="flex items-center gap-1.5">
                            <span className="truncate max-w-[200px] text-zinc-700 font-medium">{l.contact_email}</span>
                            <button
                              onClick={() => copyToClipboard(l.contact_email, `email-tab-${idx}`)}
                              title="Copy Email"
                              className="liquid-pill rounded-full w-7 h-7 flex items-center justify-center text-zinc-400 hover:text-zinc-900 shadow-xs cursor-pointer"
                            >
                              {copiedId === `email-tab-${idx}` ? (
                                <Check className="w-3.5 h-3.5 text-emerald-600" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-zinc-100/90 text-zinc-700 border border-zinc-200/60">
                            {l.contact_type || 'lead'}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-xs text-zinc-600 max-w-xs">
                          {l.linkedin_connection_note ? (
                            <div className="flex items-center justify-between gap-2 p-2 rounded-xl liquid-glass-subtle bg-white/70 border border-white/80">
                              <span className="truncate text-[11px] text-zinc-600">
                                {l.linkedin_connection_note}
                              </span>
                              <button
                                onClick={() => copyToClipboard(l.linkedin_connection_note, `note-${idx}`)}
                                title="Copy 280-char Note"
                                className="shrink-0 p-1 rounded-md hover:bg-white text-zinc-600 transition-colors cursor-pointer"
                              >
                                {copiedId === `note-${idx}` ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>
                            </div>
                          ) : (
                            <span className="text-zinc-400 text-xs">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right rounded-r-2xl">
                          {l.contact_linkedin_url ? (
                            <a
                              href={l.contact_linkedin_url}
                              target="_blank"
                              rel="noreferrer"
                              className="liquid-pill inline-flex items-center gap-1.5 text-xs font-semibold text-zinc-700 hover:text-zinc-950 px-3 py-1.5 rounded-full shadow-xs cursor-pointer"
                            >
                              <span>LinkedIn</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-zinc-400 text-xs">—</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between pt-4 border-t border-zinc-200/60 text-xs text-zinc-500">
              <span>
                Page <span className="font-semibold text-zinc-800">{leadPagination.page}</span> of {leadPagination.totalPages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={leadPagination.page <= 1 || leadsLoading}
                  onClick={() => fetchLeads(leadPage - 1)}
                  className="liquid-pill rounded-full px-3.5 py-1.5 font-medium disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>
                <button
                  disabled={leadPagination.page >= leadPagination.totalPages || leadsLoading}
                  onClick={() => fetchLeads(leadPage + 1)}
                  className="liquid-pill rounded-full px-3.5 py-1.5 font-medium disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ----------------- TAB: LIVE RADAR & DAG ----------------- */}
        {activeTab === 'radar' && (
          <AgentRadarView />
        )}
      </main>

      {/* ----------------- COMPANY DRILLDOWN DRAWER ----------------- */}
      {selectedCompany && (
        <div className="fixed inset-0 z-50 flex justify-end bg-zinc-900/30 backdrop-blur-md transition-opacity">
          <div className="w-full max-w-2xl h-full liquid-glass-elevated border-l border-white/95 p-6 md:p-8 flex flex-col shadow-[0_25px_60px_-15px_rgba(0,0,0,0.18)] overflow-y-auto animate-in slide-in-from-right duration-200 relative">
            <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-white to-transparent pointer-events-none z-20" />
            {/* Header */}
            <div className="flex items-start justify-between pb-6 border-b border-zinc-200/60">
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold tracking-tight text-zinc-900">
                    {selectedCompany.company_name}
                  </h2>
                  {selectedCompany.is_vip === 1 && (
                    <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60">
                      VIP Top-500
                    </span>
                  )}
                  {drilldownData?.stats?.hasDualAttack && (
                    <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-600 border border-rose-200/60">
                      DUAL ATTACK READY
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <span className="font-mono text-zinc-700 font-medium">{selectedCompany.official_domain || 'domain.com'}</span>
                  <span>•</span>
                  <span>{selectedCompany.sector || 'Technology'}</span>
                  <span>•</span>
                  <span>{selectedCompany.area || selectedCompany.location || 'Bengaluru'}</span>
                </div>
              </div>

              <button
                onClick={() => {
                  setSelectedCompany(null);
                  setDrilldownData(null);
                }}
                className="liquid-pill rounded-full p-2 text-zinc-500 hover:text-zinc-950 transition-all shadow-xs cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Quick Bulk Actions Bar */}
            <div className="py-4 flex flex-wrap items-center gap-2 border-b border-zinc-200/40">
              <button
                onClick={() => copyAllEmails(drilldownData?.stats?.verifiedEmails || selectedCompany.emails)}
                className="liquid-pill-dark inline-flex items-center gap-1.5 px-4 py-2 rounded-2xl text-xs font-semibold cursor-pointer shadow-md"
              >
                {copiedAllEmails ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedAllEmails ? 'Copied All to Clipboard!' : `Copy All (${drilldownData?.stats?.totalLeads || 8}) Emails`}</span>
              </button>

              <a
                href={`mailto:${(drilldownData?.stats?.verifiedEmails || []).join(';')}?subject=Senior%20Software%20Engineer%20Application%20%E2%80%94%20${encodeURIComponent(selectedCompany.company_name)}`}
                className="liquid-pill inline-flex items-center gap-1.5 px-4 py-2 rounded-2xl text-xs font-semibold text-zinc-800 hover:text-zinc-950 shadow-xs cursor-pointer"
              >
                <Send className="w-3.5 h-3.5 text-rose-500" />
                <span>Compose Bulk Outreach</span>
              </a>

              {selectedCompany.careers_page_url && (
                <a
                  href={selectedCompany.careers_page_url}
                  target="_blank"
                  rel="noreferrer"
                  className="liquid-pill inline-flex items-center gap-1 px-3.5 py-2 rounded-2xl text-xs font-semibold text-zinc-600 hover:text-zinc-950 shadow-xs ml-auto cursor-pointer"
                >
                  <span>Portal</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>

            {/* Drawer Navigation Tabs */}
            <div className="flex items-center gap-2 pt-4">
              <button
                onClick={() => setDrawerTab('leads')}
                className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all cursor-pointer ${
                  drawerTab === 'leads'
                    ? 'liquid-pill bg-white shadow-sm text-zinc-950 border border-white'
                    : 'text-zinc-500 hover:text-zinc-900 hover:bg-white/40'
                }`}
              >
                Verified Contacts & Inboxes ({drilldownData?.stats?.totalLeads || 0})
              </button>
              <button
                onClick={() => setDrawerTab('jobs')}
                className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all cursor-pointer ${
                  drawerTab === 'jobs'
                    ? 'liquid-pill bg-white shadow-sm text-zinc-950 border border-white'
                    : 'text-zinc-500 hover:text-zinc-900 hover:bg-white/40'
                }`}
              >
                Live Jobs On Radar ({drilldownData?.stats?.totalJobs || 0})
              </button>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 overflow-y-auto py-4">
              {drilldownLoading ? (
                <div className="text-center py-16 text-zinc-400 text-xs flex flex-col items-center gap-2">
                  <div className="w-6 h-6 rounded-full border-2 border-zinc-300 border-t-zinc-800 animate-spin" />
                  <span>Loading deep company telemetry...</span>
                </div>
              ) : drawerTab === 'leads' ? (
                <div className="flex flex-col gap-3">
                  {drilldownData?.leads?.map((lead: any, idx: number) => (
                    <div
                      key={idx}
                      className="liquid-row rounded-2xl p-4 flex flex-col gap-2.5 group cursor-default relative overflow-hidden"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex flex-col min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm text-zinc-900">
                              {lead.contact_name || lead.role_title}
                            </span>
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700 border border-zinc-200/60">
                              {lead.contact_type}
                            </span>
                          </div>
                          <span className="text-xs text-zinc-500 mt-0.5">{lead.role_title}</span>
                        </div>

                        <button
                          onClick={() => copyToClipboard(lead.contact_email, `drawer-${lead.lead_id}`)}
                          className="liquid-pill rounded-full px-3 py-1 text-xs font-mono font-medium text-zinc-800 hover:text-zinc-950 flex items-center gap-1.5 shrink-0 shadow-xs transition-all cursor-pointer"
                        >
                          {copiedId === `drawer-${lead.lead_id}` ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5 text-zinc-500" />
                          )}
                          <span>{lead.contact_email}</span>
                        </button>
                      </div>

                      {lead.linkedin_connection_note && (
                        <div className="p-3 rounded-xl liquid-glass-subtle bg-white/70 border border-white/80 flex flex-col gap-1.5 mt-1">
                          <div className="flex items-center justify-between text-[11px] font-semibold text-zinc-500">
                            <span>Tailored LinkedIn Connection Note (≤280 chars)</span>
                            <button
                              onClick={() => copyToClipboard(lead.linkedin_connection_note, `note-${lead.lead_id}`)}
                              className="text-zinc-700 hover:text-zinc-950 flex items-center gap-1 cursor-pointer font-medium"
                            >
                              {copiedId === `note-${lead.lead_id}` ? (
                                <Check className="w-3 h-3 text-emerald-600" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                              <span>Copy Note</span>
                            </button>
                          </div>
                          <p className="text-xs text-zinc-700 italic leading-relaxed">
                            "{lead.linkedin_connection_note}"
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {drilldownData?.jobs?.length === 0 ? (
                    <div className="text-center py-12 text-zinc-400 text-xs">
                      No direct ATS jobs parsed for this company yet. Monitored via dual-attack email outreach.
                    </div>
                  ) : (
                    drilldownData?.jobs?.map((job: any, idx: number) => (
                      <div
                        key={idx}
                        className="liquid-row rounded-2xl p-4 flex items-center justify-between gap-4 group cursor-default"
                      >
                        <div className="flex flex-col min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-sm text-zinc-900 truncate">{job.title}</span>
                            <RouteBadge route={job.execution_route} compact={true} />
                          </div>
                          <div className="flex items-center gap-2 text-xs text-zinc-500 mt-1 flex-wrap">
                            <span className="truncate">{job.location || 'Bengaluru / Remote'}</span>
                            <span>•</span>
                            <SourceBadge site={job.site} />
                          </div>
                        </div>
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noreferrer"
                          className="liquid-pill rounded-full px-3.5 py-1.5 text-xs font-semibold text-zinc-800 hover:text-zinc-950 flex items-center gap-1 shrink-0 shadow-xs transition-all cursor-pointer"
                        >
                          <span>Apply</span>
                          <ExternalLink className="w-3 h-3 text-zinc-500 group-hover:text-zinc-950" />
                        </a>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

