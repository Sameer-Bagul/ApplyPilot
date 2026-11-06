'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSession, signOut } from 'next-auth/react';
import { LandingPage } from '@/components/LandingPage';
import { PaginationControls } from '@/components/ui/PaginationControls';
import {
  LogOut,
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
  Globe,
  X,
  Send,
  Layers,
  Activity,
  GitBranch,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Trash2,
  Save,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Flame,
  Cpu,
  Star,
  Paperclip,
  User,
  HelpCircle,
  Clock,
  Terminal,
} from 'lucide-react';

import { AgentRadarView } from '@/components/agent-radar/AgentRadarView';
import { SourceBadge } from '@/components/ui/SourceBadge';
import { RouteBadge } from '@/components/ui/RouteBadge';
import { WallpaperSwitcher } from '@/components/ui/LiquidBackground';

import { JobDetailDrawer } from '@/components/JobDetailDrawer';
import { CompanyDetailDrawer } from '@/components/CompanyDetailDrawer';
import { LeadDetailDrawer } from '@/components/LeadDetailDrawer';
import { HitlTicketModal } from '@/components/HitlTicketModal';
import { ArchitectureView } from '@/components/ArchitectureView';
import { SourcesView } from '@/components/SourcesView';
import { ProfileView } from '@/components/ProfileView';
import { AddJobModal } from '@/components/AddJobModal';
import { AddCompanyModal } from '@/components/AddCompanyModal';
import { AddLeadModal } from '@/components/AddLeadModal';
import { AutoApplyButton } from '@/components/AutoApplyButton';

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
  hitlCount?: number;
  pendingReviewsCount?: number;
}

interface DashboardPageProps {
  initialTab?: 'overview' | 'architecture' | 'sources' | 'jobs' | 'companies' | 'leads' | 'hitl' | 'radar' | 'profile';
}

function DashboardContent({ initialTab = 'overview' }: DashboardPageProps) {
  const { data: session, status } = useSession();
  const [activeTab, setActiveTab] = useState<
    'overview' | 'architecture' | 'sources' | 'jobs' | 'companies' | 'leads' | 'hitl' | 'radar' | 'profile'
  >(initialTab);
  const [jobLimit, setJobLimit] = useState(25);
  const [companyLimit, setCompanyLimit] = useState(25);
  const [leadLimit, setLeadLimit] = useState(25);
  const [ticketLimit, setTicketLimit] = useState(25);
  const [greeting, setGreeting] = useState('Good Day');
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);

  // Nested Drawer / Modal Selection State
  const [selectedJobUrl, setSelectedJobUrl] = useState<string | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null);

  // Add Modals State
  const [addJobOpen, setAddJobOpen] = useState(false);
  const [addCompanyOpen, setAddCompanyOpen] = useState(false);
  const [addLeadOpen, setAddLeadOpen] = useState(false);

  // Responsive Navigation State
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Jobs State
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobSearch, setJobSearch] = useState('');
  const [jobRoute, setJobRoute] = useState('ALL');
  const [jobState, setJobState] = useState('ALL');
  const [jobMinScore, setJobMinScore] = useState<number>(0);
  const [jobPage, setJobPage] = useState(1);
  const [jobPagination, setJobPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [jobsLoading, setJobsLoading] = useState(false);

  // Companies State
  const [companies, setCompanies] = useState<any[]>([]);
  const [companySearch, setCompanySearch] = useState('');
  const [companyVipOnly, setCompanyVipOnly] = useState(false);
  const [companySector, setCompanySector] = useState('ALL');
  const [companyPage, setCompanyPage] = useState(1);
  const [companyPagination, setCompanyPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [companiesLoading, setCompaniesLoading] = useState(false);

  // Leads State
  const [leads, setLeads] = useState<any[]>([]);
  const [leadSearch, setLeadSearch] = useState('');
  const [leadStatus, setLeadStatus] = useState('ALL');
  const [leadType, setLeadType] = useState('ALL');
  const [leadPage, setLeadPage] = useState(1);
  const [leadPagination, setLeadPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [leadsLoading, setLeadsLoading] = useState(false);
  const [dispatchingLeads, setDispatchingLeads] = useState(false);
  const [dispatchMessage, setDispatchMessage] = useState<string | null>(null);

  // HITL State
  const [tickets, setTickets] = useState<any[]>([]);
  const [ticketStatus, setTicketStatus] = useState('pending');
  const [ticketPage, setTicketPage] = useState(1);
  const [ticketPagination, setTicketPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [ticketsLoading, setTicketsLoading] = useState(false);

  // Dynamic greeting based on user's local time
  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('Good Morning');
    else if (hour < 18) setGreeting('Good Afternoon');
    else setGreeting('Good Evening');
  }, []);

  const switchTab = (tab: typeof activeTab) => {
    setActiveTab(tab);
    if (typeof window !== 'undefined') {
      const nextPath = tab === 'overview' ? '/' : `/${tab}`;
      window.history.pushState({ tab }, '', nextPath);
    }
  };

  const openJob = (url: string) => {
    setSelectedJobUrl(url);
    if (typeof window !== 'undefined') {
      const u = new URL(window.location.href);
      u.searchParams.set('job', url);
      window.history.pushState(null, '', u.toString());
    }
  };

  const closeJob = () => {
    setSelectedJobUrl(null);
    if (typeof window !== 'undefined') {
      const u = new URL(window.location.href);
      u.searchParams.delete('job');
      window.history.pushState(null, '', u.toString());
    }
  };

  const openCompany = (companyName: string) => {
    setSelectedCompany(companyName);
    if (typeof window !== 'undefined') {
      const u = new URL(window.location.href);
      u.searchParams.set('company', companyName);
      window.history.pushState(null, '', u.toString());
    }
  };

  const closeCompany = () => {
    setSelectedCompany(null);
    if (typeof window !== 'undefined') {
      const u = new URL(window.location.href);
      u.searchParams.delete('company');
      window.history.pushState(null, '', u.toString());
    }
  };

  const openLead = (leadId: string) => {
    setSelectedLeadId(leadId);
    if (typeof window !== 'undefined') {
      const u = new URL(window.location.href);
      u.searchParams.set('lead', leadId);
      window.history.pushState(null, '', u.toString());
    }
  };

  const closeLead = () => {
    setSelectedLeadId(null);
    if (typeof window !== 'undefined') {
      const u = new URL(window.location.href);
      u.searchParams.delete('lead');
      window.history.pushState(null, '', u.toString());
    }
  };

  const openTicket = (ticketId: number) => {
    setSelectedTicketId(ticketId);
    if (typeof window !== 'undefined') {
      const u = new URL(window.location.href);
      u.searchParams.set('ticket', ticketId.toString());
      window.history.pushState(null, '', u.toString());
    }
  };

  const closeTicket = () => {
    setSelectedTicketId(null);
    if (typeof window !== 'undefined') {
      const u = new URL(window.location.href);
      u.searchParams.delete('ticket');
      window.history.pushState(null, '', u.toString());
    }
  };

  // Sync with browser URL slugs & deep link query parameters
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const validTabs: Array<typeof activeTab> = [
      'overview',
      'architecture',
      'sources',
      'jobs',
      'companies',
      'leads',
      'hitl',
      'radar',
      'profile',
    ];

    const syncFromUrl = () => {
      const path = window.location.pathname.replace(/^\//, '');
      if (validTabs.includes(path as any)) {
        setActiveTab(path as any);
      } else {
        const urlParams = new URLSearchParams(window.location.search);
        const tabParam = urlParams.get('tab');
        if (tabParam && validTabs.includes(tabParam as any)) {
          setActiveTab(tabParam as any);
        }
      }

      const params = new URLSearchParams(window.location.search);
      const jobParam = params.get('job');
      if (jobParam) setSelectedJobUrl(jobParam);
      const companyParam = params.get('company');
      if (companyParam) setSelectedCompany(companyParam);
      const leadParam = params.get('lead');
      if (leadParam) setSelectedLeadId(leadParam);
      const ticketParam = params.get('ticket');
      if (ticketParam) setSelectedTicketId(parseInt(ticketParam, 10));
    };

    syncFromUrl();
    window.addEventListener('popstate', syncFromUrl);
    return () => window.removeEventListener('popstate', syncFromUrl);
  }, []);

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

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchJobs = async (page = jobPage, limit = jobLimit) => {
    setJobsLoading(true);
    try {
      const res = await fetch(
        `/api/jobs?page=${page}&limit=${limit}&search=${encodeURIComponent(jobSearch)}&route=${jobRoute}&state=${jobState}&minScore=${jobMinScore}`
      );
      const data = await res.json();
      if (data.success) {
        setJobs(data.jobs);
        setJobPagination(data.pagination);
        setJobPage(page);
      }
    } catch (err) {
      console.error('Failed to fetch jobs', err);
    } finally {
      setJobsLoading(false);
    }
  };

  const fetchCompanies = async (page = companyPage, limit = companyLimit) => {
    setCompaniesLoading(true);
    try {
      const res = await fetch(
        `/api/companies?page=${page}&limit=${limit}&search=${encodeURIComponent(companySearch)}&vip=${companyVipOnly}&sector=${companySector}`
      );
      const data = await res.json();
      if (data.success) {
        setCompanies(data.companies);
        setCompanyPagination(data.pagination);
        setCompanyPage(page);
      }
    } catch (err) {
      console.error('Failed to fetch companies', err);
    } finally {
      setCompaniesLoading(false);
    }
  };

  const fetchLeads = async (page = leadPage, limit = leadLimit) => {
    setLeadsLoading(true);
    try {
      const res = await fetch(
        `/api/leads?page=${page}&limit=${limit}&search=${encodeURIComponent(leadSearch)}&status=${leadStatus}&type=${leadType}`
      );
      const data = await res.json();
      if (data.success) {
        setLeads(data.leads);
        setLeadPagination(data.pagination);
        setLeadPage(page);
      }
    } catch (err) {
      console.error('Failed to fetch leads', err);
    } finally {
      setLeadsLoading(false);
    }
  };

  const fetchTickets = async (page = ticketPage, limit = ticketLimit) => {
    setTicketsLoading(true);
    try {
      const res = await fetch(`/api/hitl?page=${page}&limit=${limit}&status=${ticketStatus}`);
      const data = await res.json();
      if (data.success) {
        setTickets(data.tickets);
        setTicketPagination(data.pagination);
        setTicketPage(page);
      }
    } catch (err) {
      console.error('Failed to fetch tickets', err);
    } finally {
      setTicketsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'jobs') fetchJobs(1);
    if (activeTab === 'companies') fetchCompanies(1);
    if (activeTab === 'leads') fetchLeads(1);
    if (activeTab === 'hitl') fetchTickets(1);
  }, [
    activeTab,
    jobSearch,
    jobRoute,
    jobState,
    jobMinScore,
    companySearch,
    companyVipOnly,
    companySector,
    leadSearch,
    leadStatus,
    leadType,
    ticketStatus,
  ]);

  const handleApproveAllPending = async () => {
    const pendingIds = leads.filter((l) => l.outreach_status === 'pending_review').map((l) => l.lead_id);
    if (pendingIds.length === 0) return;
    try {
      const res = await fetch('/api/leads/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: pendingIds, approved_by: 'admin_dashboard' }),
      });
      const data = await res.json();
      if (data.success) {
        fetchLeads(leadPage);
        fetchStats();
      }
    } catch (err) {
      console.error('Failed to approve leads', err);
    }
  };

  const handleDispatchApprovedLeads = async () => {
    setDispatchingLeads(true);
    setDispatchMessage(null);
    try {
      const res = await fetch('/api/leads/dispatch', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setDispatchMessage(`Dispatched ${data.dispatchedCount} approved emails!`);
        fetchLeads(leadPage);
        fetchStats();
      } else {
        setDispatchMessage(`Dispatch failed: ${data.error}`);
      }
    } catch (err: any) {
      setDispatchMessage(`Dispatch error: ${err.message}`);
    } finally {
      setDispatchingLeads(false);
    }
  };

  const getScoreColor = (score: number | null | undefined) => {
    if (score == null) return 'text-zinc-600 bg-zinc-100 border-zinc-200';
    if (score >= 8) return 'text-emerald-800 bg-emerald-50 border-emerald-200 shadow-2xs';
    if (score >= 5) return 'text-amber-800 bg-amber-50 border-amber-200 shadow-2xs';
    return 'text-rose-800 bg-rose-50 border-rose-200 shadow-2xs';
  };

  const navItems = [
    {
      id: 'overview',
      label: 'Mission Control',
      icon: LayoutDashboard,
      color: 'text-purple-600',
      badge: null,
      badgeColor: '',
    },
    {
      id: 'architecture',
      label: 'Architecture',
      icon: Layers,
      color: 'text-cyan-600',
      badge: 'CORE',
      badgeColor: 'bg-cyan-50 text-cyan-800 border-cyan-200/80',
    },
    {
      id: 'sources',
      label: 'Job Sources',
      icon: Globe,
      color: 'text-indigo-600',
      badge: 'MULTI-SRC',
      badgeColor: 'bg-indigo-50 text-indigo-800 border-indigo-200/80',
    },
    {
      id: 'jobs',
      label: 'Jobs Explorer',
      icon: Briefcase,
      color: 'text-blue-600',
      badge: stats?.totalJobs ? stats.totalJobs.toLocaleString() : null,
      badgeColor: 'bg-blue-50 text-blue-800 border-blue-200/80',
    },
    {
      id: 'companies',
      label: 'Watchlist',
      icon: Building2,
      color: 'text-amber-600',
      badge: stats?.totalCompanies ? stats.totalCompanies.toLocaleString() : null,
      badgeColor: 'bg-amber-50 text-amber-800 border-amber-200/80',
    },
    {
      id: 'leads',
      label: 'Outreach Hub',
      icon: Users,
      color: 'text-emerald-600',
      badge: stats?.totalLeads ? stats.totalLeads.toLocaleString() : null,
      badgeColor: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    },
    {
      id: 'hitl',
      label: 'HITL Tickets',
      icon: ShieldAlert,
      color: 'text-rose-600',
      badge: stats?.hitlCount ? `${stats.hitlCount} PENDING` : '0',
      badgeColor: stats?.hitlCount
        ? 'bg-rose-50 text-rose-800 border-rose-200/80 animate-pulse'
        : 'bg-zinc-100 text-zinc-600 border-zinc-200',
    },
    {
      id: 'profile',
      label: 'Candidate Profile',
      icon: User,
      color: 'text-indigo-600',
    },
    {
      id: 'radar',
      label: 'Agent Radar',
      icon: GitBranch,
      color: 'text-purple-600',
      badge: 'LIVE DAG',
      badgeColor: 'bg-purple-50 text-purple-800 border-purple-200/80',
    },
  ];

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-zinc-950/20 border-t-zinc-950 animate-spin" />
        <span className="text-xs font-semibold text-zinc-500">Connecting to Mission Control...</span>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return <LandingPage />;
  }

  return (
    <div className="flex flex-col md:flex-row min-h-screen p-2.5 sm:p-3 md:p-4 lg:p-5 2xl:p-7 gap-3 sm:gap-4 lg:gap-6 w-full max-w-none text-zinc-900">
      {/* ----------------- DESKTOP SIDEBAR (Liquid Glass Card) ----------------- */}
      <aside
        className={`hidden md:flex flex-col gap-4 lg:gap-6 shrink-0 transition-all duration-300 ${
          sidebarCollapsed ? 'w-20' : 'w-56 lg:w-64'
        }`}
      >
        <div
          className={`liquid-glass rounded-3xl flex flex-col justify-between transition-all relative overflow-hidden shadow-sm h-full ${
            sidebarCollapsed ? 'p-3 items-center gap-4' : 'p-5 lg:p-6 gap-6'
          }`}
        >
          {/* Specular top rim highlight */}
          <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />

          <div className="space-y-6 w-full">
            {/* Logo, Title & Sidebar Collapse */}
            <div className={`flex items-center w-full ${sidebarCollapsed ? 'flex-col gap-2' : 'justify-between gap-3'}`}>
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-full orb-peach shrink-0 flex items-center justify-center shadow-md" />
                {!sidebarCollapsed && (
                  <div className="flex flex-col min-w-0">
                    <span className="font-extrabold text-lg tracking-tight text-zinc-900 truncate flex items-center gap-1.5">
                      ApplyPilot
                      <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded-full bg-cyan-50 text-cyan-800 border border-cyan-200">
                        v2.0
                      </span>
                    </span>
                    <span className="text-[10px] text-zinc-500 font-semibold tracking-wider uppercase">
                      AUTONOMOUS ENGINE
                    </span>
                  </div>
                )}
              </div>

              <button
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                title={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
                className="liquid-pill rounded-full p-1.5 text-zinc-600 hover:text-zinc-950 transition cursor-pointer shadow-2xs shrink-0"
              >
                {sidebarCollapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
              </button>
            </div>

            {/* Navigation Items */}
            <nav className="flex flex-col gap-1.5 w-full">
              {navItems.map((item) => {
                const IconComponent = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => switchTab(item.id as any)}
                    className={`liquid-row rounded-2xl flex items-center gap-3 transition-all cursor-pointer ${
                      sidebarCollapsed ? 'p-2.5 justify-center' : 'p-2.5 sm:px-3 justify-between'
                    } ${
                      isActive
                        ? 'border-zinc-300 bg-white shadow-xs font-bold text-zinc-950'
                        : 'hover:bg-white/90 text-zinc-700'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <IconComponent
                        className={`w-4 h-4 shrink-0 transition-transform ${item.color} ${
                          isActive ? 'scale-110' : ''
                        }`}
                      />
                      {!sidebarCollapsed && <span className="text-xs truncate">{item.label}</span>}
                    </div>

                    {!sidebarCollapsed && item.badge && (
                      <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full border ${item.badgeColor}`}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Bottom System Status Widget */}
          {!sidebarCollapsed && (
            <div className="p-3.5 rounded-2xl bg-white/60 border border-white/90 shadow-2xs space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[10.5px] font-bold text-zinc-500 uppercase tracking-wider">Engine Status</span>
                <span className="flex items-center gap-1.5 text-emerald-700 font-semibold text-[11px]">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                  Active
                </span>
              </div>
              <div className="text-[11px] text-zinc-600 flex items-center justify-between">
                <span>Free Ingestion</span>
                <span className="font-mono font-semibold text-zinc-800">4.7M+ ATS</span>
              </div>
              <div className="text-[11px] text-zinc-600 flex items-center justify-between">
                <span>Local Matcher</span>
                <span className="font-semibold text-emerald-700">0 Tokens</span>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* ----------------- MAIN STUDIO DASHBOARD CONTENT ----------------- */}
      <main className="flex-1 flex flex-col gap-4 lg:gap-6 min-w-0">
        {/* Top Liquid Glass Header Bar */}
        <header className="liquid-glass rounded-3xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm relative overflow-hidden">
          <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />

          {/* Left: Greeting & Current Tab Title */}
          <div className="flex items-center gap-3">
            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden liquid-pill rounded-full p-2 text-zinc-700 hover:text-zinc-950 transition cursor-pointer shadow-2xs"
            >
              <Menu className="w-4 h-4" />
            </button>

            <div className="space-y-0.5">
              <h2 className="text-xl sm:text-2xl font-extrabold tracking-tight text-zinc-900 flex items-center gap-2">
                <span>{greeting}, Sameer !</span>
              </h2>
              <p className="text-xs text-zinc-500">
                Autonomous Career Acquisition & Dual-Attack Execution Studio
              </p>
            </div>
          </div>

          {/* Right: Actions, Live Indicator, User Auth & Studio Grid Switcher */}
          <div className="flex items-center gap-2.5 sm:gap-3 flex-wrap">
            {/* Active Continuous Looper Pill */}
            <div className="liquid-pill rounded-full px-3 py-1.5 flex items-center gap-2 text-xs font-semibold text-zinc-800 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="hidden sm:inline">Marathon Looper</span>
            </div>

            {/* Authenticated User Pill & Sign Out */}
            {session?.user && (
              <div className="flex items-center gap-2 liquid-pill rounded-full pl-2 pr-2.5 py-1 text-xs font-semibold text-zinc-800 shadow-2xs">
                {session.user.image ? (
                  <img
                    src={session.user.image}
                    alt={session.user.name || 'User'}
                    className="w-5 h-5 rounded-full object-cover border border-zinc-200"
                  />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-zinc-950 text-white text-[10px] flex items-center justify-center font-bold">
                    {session.user.name ? session.user.name.charAt(0) : 'S'}
                  </div>
                )}
                <span className="hidden sm:inline text-xs font-bold text-zinc-900 truncate max-w-[120px]">
                  {session.user.name || 'Sameer'}
                </span>
                <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 uppercase font-bold tracking-wider">
                  Admin
                </span>
                <button
                  onClick={() => signOut({ callbackUrl: '/login' })}
                  title="Sign Out of Mission Control"
                  className="ml-1 text-zinc-400 hover:text-rose-600 transition cursor-pointer p-0.5 rounded-full hover:bg-rose-50"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Studio Grid & Pearl Spheres Backdrop Switcher */}
            <WallpaperSwitcher />
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden liquid-glass-elevated rounded-3xl p-4 shadow-xl border border-white/95 space-y-2 animate-in fade-in">
            {navItems.map((item) => {
              const IconComponent = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    switchTab(item.id as any);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full liquid-row rounded-2xl p-3 flex items-center justify-between text-xs font-semibold ${
                    isActive ? 'bg-white shadow-xs font-bold text-zinc-950' : 'text-zinc-700'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <IconComponent className={`w-4 h-4 ${item.color}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full border ${item.badgeColor}`}>
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* ----------------- TAB 1: MISSION CONTROL OVERVIEW ----------------- */}
        {activeTab === 'overview' && (
          <div className="space-y-5 lg:space-y-6 animate-in fade-in duration-200">
            {/* Top Metric Tiles */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-5">
              <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs hover:shadow-md transition-all relative overflow-hidden group">
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />
                <div className="flex items-center justify-between text-zinc-500 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider">Total Postings</span>
                  <div className="p-2 rounded-xl bg-blue-50 text-blue-700 border border-blue-200/60 shadow-2xs">
                    <Briefcase className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-zinc-900 tracking-tight">
                  {stats?.totalJobs ? stats.totalJobs.toLocaleString() : '2,554+'}
                </div>
                <div className="text-[11px] text-emerald-700 font-semibold mt-1 flex items-center gap-1">
                  <span>+100% Direct ATS</span>
                  <span className="text-zinc-400 font-normal">• Zero Aggregators</span>
                </div>
              </div>

              <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs hover:shadow-md transition-all relative overflow-hidden group">
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />
                <div className="flex items-center justify-between text-zinc-500 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider">Watchlist Targets</span>
                  <div className="p-2 rounded-xl bg-amber-50 text-amber-700 border border-amber-200/60 shadow-2xs">
                    <Building2 className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-zinc-900 tracking-tight">
                  {stats?.totalCompanies ? stats.totalCompanies.toLocaleString() : '136'}
                </div>
                <div className="text-[11px] text-amber-700 font-semibold mt-1 flex items-center gap-1">
                  <Star className="w-3 h-3 fill-amber-500 text-amber-600" />
                  <span>{stats?.vipCompanies || 24} VIP Targets</span>
                </div>
              </div>

              <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs hover:shadow-md transition-all relative overflow-hidden group">
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />
                <div className="flex items-center justify-between text-zinc-500 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider">Recruiter Leads</span>
                  <div className="p-2 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200/60 shadow-2xs">
                    <Users className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-zinc-900 tracking-tight">
                  {stats?.totalLeads ? stats.totalLeads.toLocaleString() : '230'}
                </div>
                <div className="text-[11px] text-emerald-700 font-semibold mt-1">
                  <span>100% Free Harvester</span>
                </div>
              </div>

              <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs hover:shadow-md transition-all relative overflow-hidden group">
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />
                <div className="flex items-center justify-between text-zinc-500 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider">Dual-Attack Queue</span>
                  <div className="p-2 rounded-xl bg-purple-50 text-purple-700 border border-purple-200/60 shadow-2xs">
                    <Zap className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-zinc-900 tracking-tight">
                  {stats?.routes?.dualAttack || 42}
                </div>
                <div className="text-[11px] text-purple-700 font-semibold mt-1">
                  <span>Portal + Recruiter Warm Email</span>
                </div>
              </div>
            </div>

            {/* Quick Actions & Route Breakdown Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              {/* Route Breakdown Card */}
              <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                    Execution Routes Distribution
                  </h3>
                  <Zap className="w-4 h-4 text-purple-600" />
                </div>

                <div className="space-y-3">
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-zinc-800">
                      <span>DUAL_ATTACK (Portal + Warm Outreach)</span>
                      <span>{stats?.routes?.dualAttack || 42}</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-zinc-100 overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full" style={{ width: '45%' }} />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-zinc-800">
                      <span>PORTAL_ONLY (Automated Headless Submission)</span>
                      <span>{stats?.routes?.portalOnly || 1800}</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-zinc-100 overflow-hidden">
                      <div className="h-full bg-cyan-500 rounded-full" style={{ width: '70%' }} />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-zinc-800">
                      <span>EMAIL_ONLY (Founder / Recruiter Pitch)</span>
                      <span>{stats?.routes?.emailOnly || 188}</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-zinc-100 overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: '25%' }} />
                    </div>
                  </div>
                </div>
              </div>

              {/* Free Direct ATS Harvest Providers */}
              <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                    Direct ATS Harvest Source Distribution
                  </h3>
                  <Compass className="w-4 h-4 text-cyan-600" />
                </div>

                <div className="grid grid-cols-2 gap-2.5 text-xs">
                  {(stats?.topAts || [
                    { provider: 'greenhouse', count: 1240 },
                    { provider: 'lever', count: 820 },
                    { provider: 'ashby', count: 340 },
                    { provider: 'workday', count: 154 },
                  ]).map((ats, idx) => (
                    <div key={idx} className="p-3 rounded-2xl bg-white/70 border border-white/90 shadow-2xs">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400 block capitalize">
                        {ats.provider}
                      </span>
                      <span className="text-base font-extrabold text-zinc-900">{ats.count.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Fast Launch Studio Actions */}
              <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4 flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-2">
                    Studio Management Actions
                  </h3>
                  <p className="text-xs text-zinc-500 leading-relaxed">
                    Create new job entries, target companies, or review pending recruiter emails through the strict HITL gate.
                  </p>
                </div>

                <div className="flex flex-col gap-2 pt-2">
                  <button
                    onClick={() => setAddJobOpen(true)}
                    className="liquid-pill w-full py-2.5 px-3.5 rounded-2xl flex items-center justify-between text-xs font-semibold text-zinc-800 hover:text-zinc-950 transition cursor-pointer shadow-2xs"
                  >
                    <div className="flex items-center gap-2">
                      <Briefcase className="w-4 h-4 text-blue-600" />
                      <span>Add Target Job Manually</span>
                    </div>
                    <Plus className="w-3.5 h-3.5 text-zinc-400" />
                  </button>

                  <button
                    onClick={() => setAddCompanyOpen(true)}
                    className="liquid-pill w-full py-2.5 px-3.5 rounded-2xl flex items-center justify-between text-xs font-semibold text-zinc-800 hover:text-zinc-950 transition cursor-pointer shadow-2xs"
                  >
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-amber-600" />
                      <span>Add Target Company</span>
                    </div>
                    <Plus className="w-3.5 h-3.5 text-zinc-400" />
                  </button>

                  <button
                    onClick={() => setAddLeadOpen(true)}
                    className="liquid-pill w-full py-2.5 px-3.5 rounded-2xl flex items-center justify-between text-xs font-semibold text-zinc-800 hover:text-zinc-950 transition cursor-pointer shadow-2xs"
                  >
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4 text-emerald-600" />
                      <span>Add Recruiter Lead</span>
                    </div>
                    <Plus className="w-3.5 h-3.5 text-zinc-400" />
                  </button>
                </div>
              </div>
            </div>

            {/* Recent High-Scoring Opportunities */}
            <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-zinc-900 tracking-tight">
                    Top Scored Career Opportunities
                  </h3>
                  <p className="text-xs text-zinc-500">
                    Harvested directly from company careers pages and evaluated by the 4-factor local matcher
                  </p>
                </div>

                <button
                  onClick={() => switchTab('jobs')}
                  className="liquid-pill px-3 py-1.5 rounded-xl text-xs font-semibold text-zinc-800 hover:text-zinc-950 flex items-center gap-1 cursor-pointer shadow-2xs"
                >
                  <span>Explore All</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="space-y-2">
                {(stats?.recentJobs || []).slice(0, 5).map((j: any) => (
                  <div
                    key={j.url}
                    onClick={() => openJob(j.url)}
                    className="liquid-row rounded-2xl p-3.5 flex items-center justify-between gap-3 cursor-pointer group"
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-zinc-900 group-hover:text-cyan-700 transition">
                          {j.title}
                        </span>
                        {j.fit_score != null && (
                          <span className={`px-2 py-0.2 rounded-full text-[10px] font-bold border ${getScoreColor(j.fit_score)}`}>
                            {j.fit_score}/10 Fit
                          </span>
                        )}
                        <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-zinc-100 text-zinc-600 border border-zinc-200">
                          {j.execution_route || 'PORTAL_ONLY'}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-500 flex items-center gap-3">
                        <span className="font-medium text-zinc-700">{j.company}</span>
                        <span>•</span>
                        <span>{j.location || 'Remote'}</span>
                        {j.salary_raw && <span>• {j.salary_raw}</span>}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <AutoApplyButton
                        jobUrl={j.url}
                        initialState={j.state}
                        onApplied={() => fetchStats()}
                        onOpenTicket={(ticketId) => {
                          setSelectedJobUrl(null);
                          setSelectedTicketId(ticketId);
                        }}
                      />
                      <a
                        href={j.url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 rounded-xl liquid-pill text-zinc-400 hover:text-zinc-800 transition"
                        title="Open Official Job Board"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                      <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 group-hover:text-zinc-900 transition" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ----------------- TAB 2: ARCHITECTURE VIEW ----------------- */}
        {activeTab === 'architecture' && <ArchitectureView />}

        {/* ----------------- TAB 2B: JOB SOURCES VIEW ----------------- */}
        {activeTab === 'sources' && <SourcesView onSelectJob={(url) => setSelectedJobUrl(url)} />}

        {/* ----------------- TAB 3: ALL JOBS EXPLORER ----------------- */}
        {activeTab === 'jobs' && (
          <div className="space-y-4 animate-in fade-in duration-200">
            {/* Filter & Search Bar */}
            <div className="liquid-glass rounded-3xl p-4 sm:p-5 border border-white/90 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2 w-full md:w-auto flex-1">
                <div className="relative flex-1 max-w-md">
                  <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={jobSearch}
                    onChange={(e) => setJobSearch(e.target.value)}
                    placeholder="Search by role title, company, or keywords..."
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-2xl pl-9 pr-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                </div>

                <select
                  value={jobRoute}
                  onChange={(e) => setJobRoute(e.target.value)}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                >
                  <option value="ALL">All Routes</option>
                  <option value="DUAL_ATTACK">Dual Attack</option>
                  <option value="PORTAL_ONLY">Portal Only</option>
                  <option value="EMAIL_ONLY">Email Only</option>
                </select>

                <select
                  value={jobMinScore}
                  onChange={(e) => setJobMinScore(Number(e.target.value))}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                >
                  <option value="0">All Scores (0+)</option>
                  <option value="5">Score 5+ (Medium)</option>
                  <option value="8">Score 8+ (High Fit)</option>
                </select>
              </div>

              <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                <button
                  onClick={() => setAddJobOpen(true)}
                  className="liquid-pill-dark px-3.5 py-2 rounded-2xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <Plus className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Add Job</span>
                </button>
              </div>
            </div>

            {/* Jobs Table Container */}
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60 text-xs text-zinc-500 font-semibold px-2">
                <span>Showing {jobs.length} of {jobPagination.total.toLocaleString()} listings</span>
                <span>Page {jobPage} of {jobPagination.totalPages}</span>
              </div>

              {jobsLoading ? (
                <div className="py-20 text-center text-xs text-zinc-400">Loading open listings...</div>
              ) : jobs.length === 0 ? (
                <div className="py-20 text-center text-xs text-zinc-500">No jobs matched your filter criteria.</div>
              ) : (
                <div className="space-y-2">
                  {jobs.map((j) => (
                    <div
                      key={j.url}
                      onClick={() => openJob(j.url)}
                      className="liquid-row rounded-2xl p-3.5 flex items-center justify-between gap-3 cursor-pointer group"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-xs text-zinc-900 group-hover:text-cyan-700 transition">
                            {j.title}
                          </span>
                          {j.fit_score != null && (
                            <span className={`px-2 py-0.2 rounded-full text-[10px] font-bold border ${getScoreColor(j.fit_score)}`}>
                              {j.fit_score}/10
                            </span>
                          )}
                          <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-zinc-100 text-zinc-600 border border-zinc-200">
                            {j.execution_route || 'PORTAL_ONLY'}
                          </span>
                          <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-zinc-100 text-zinc-500 border border-zinc-200 capitalize">
                            {j.ats_provider || 'Direct'}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-500 flex items-center gap-3">
                          <span className="font-medium text-zinc-800">{j.company}</span>
                          <span>•</span>
                          <span>{j.location || 'Remote'}</span>
                          {j.salary_raw && <span>• {j.salary_raw}</span>}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <AutoApplyButton
                          jobUrl={j.url}
                          initialState={j.state}
                          onApplied={() => {
                            fetchStats();
                            fetchJobs(jobPage);
                          }}
                          onOpenTicket={(ticketId) => {
                            setSelectedJobUrl(null);
                            setSelectedTicketId(ticketId);
                          }}
                        />
                        <a
                          href={j.url}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="p-1.5 rounded-xl liquid-pill text-zinc-400 hover:text-zinc-800 transition"
                          title="Open Official Job Board"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                        <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 group-hover:text-zinc-900 transition" />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Smart Pagination Bar */}
              <PaginationControls
                page={jobPage}
                totalPages={jobPagination.totalPages}
                total={jobPagination.total}
                limit={jobPagination.limit}
                onPageChange={(p) => fetchJobs(p, jobPagination.limit)}
                onLimitChange={(l) => {
                  setJobLimit(l);
                  setJobPagination((prev) => ({ ...prev, limit: l }));
                  fetchJobs(1, l);
                }}
                itemName="listings"
              />
            </div>
          </div>
        )}

        {/* ----------------- TAB 4: COMPANY WATCHLIST ----------------- */}
        {activeTab === 'companies' && (
          <div className="space-y-4 animate-in fade-in duration-200">
            {/* Filter Bar */}
            <div className="liquid-glass rounded-3xl p-4 sm:p-5 border border-white/90 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2 w-full md:w-auto flex-1">
                <div className="relative flex-1 max-w-md">
                  <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={companySearch}
                    onChange={(e) => setCompanySearch(e.target.value)}
                    placeholder="Search company name, domain..."
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-2xl pl-9 pr-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                </div>

                <button
                  onClick={() => setCompanyVipOnly(!companyVipOnly)}
                  className={`px-3 py-2 rounded-2xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer ${
                    companyVipOnly
                      ? 'bg-amber-100 text-amber-900 border border-amber-300 shadow-2xs'
                      : 'liquid-pill text-zinc-700 shadow-2xs'
                  }`}
                >
                  <Star className={`w-3.5 h-3.5 ${companyVipOnly ? 'fill-amber-500 text-amber-600' : 'text-zinc-400'}`} />
                  <span>VIP Targets Only</span>
                </button>
              </div>

              <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                <button
                  onClick={() => setAddCompanyOpen(true)}
                  className="liquid-pill-dark px-3.5 py-2 rounded-2xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <Plus className="w-3.5 h-3.5 text-amber-400" />
                  <span>Add Company</span>
                </button>
              </div>
            </div>

            {/* Companies List */}
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60 text-xs text-zinc-500 font-semibold px-2">
                <span>Showing {companies.length} of {companyPagination.total.toLocaleString()} companies</span>
                <span>Page {companyPage} of {companyPagination.totalPages}</span>
              </div>

              {companiesLoading ? (
                <div className="py-20 text-center text-xs text-zinc-400">Loading companies...</div>
              ) : companies.length === 0 ? (
                <div className="py-20 text-center text-xs text-zinc-500">No companies found.</div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3.5">
                  {companies.map((c) => {
                    const domain = c.official_domain || `${c.company_name.toLowerCase().replace(/[^a-z0-9]/g, '')}.com`;
                    const faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
                    const openRoles = c.open_roles_count || 0;
                    const initial = (c.company_name || 'C').charAt(0).toUpperCase();

                    return (
                      <div
                        key={c.company_name}
                        onClick={() => openCompany(c.company_name)}
                        className="liquid-card rounded-2xl p-4 flex flex-col items-center text-center justify-between transition-all duration-200 hover:scale-[1.02] hover:shadow-md hover:border-amber-300 cursor-pointer group relative overflow-hidden min-h-[165px] border border-white/80 bg-white/70"
                      >
                        {c.is_vip === 1 && (
                          <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded-full text-[9px] font-extrabold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-0.5">
                            <Star className="w-2.5 h-2.5 fill-amber-500 text-amber-600" />
                            VIP
                          </span>
                        )}

                        {/* 1. Icon / Logo of Company */}
                        <div className="w-12 h-12 rounded-2xl bg-white p-1 border border-zinc-200/90 shadow-2xs flex items-center justify-center shrink-0 mb-2 group-hover:shadow-xs transition-shadow overflow-hidden">
                          <img
                            src={faviconUrl}
                            alt={c.company_name}
                            className="w-full h-full object-contain rounded-xl"
                            onError={(e) => {
                              const target = e.currentTarget;
                              target.style.display = 'none';
                              if (target.parentElement) {
                                target.parentElement.innerHTML = `<span class="text-base font-black text-amber-700">${initial}</span>`;
                              }
                            }}
                          />
                        </div>

                        {/* 2. Name of Company */}
                        <div className="w-full mb-2">
                          <h4
                            className="font-bold text-xs text-zinc-950 truncate px-1 group-hover:text-amber-700 transition-colors"
                            title={c.company_name}
                          >
                            {c.company_name}
                          </h4>
                          <span className="text-[10px] text-zinc-500 font-mono block truncate">
                            {c.official_domain || c.ats_provider || 'Enterprise'}
                          </span>
                        </div>

                        {/* 3. Count of Jobs in that Company */}
                        <div className="w-full pt-2 border-t border-zinc-200/50">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-extrabold w-full justify-center ${
                              openRoles > 0
                                ? 'bg-amber-100 text-amber-900 border border-amber-300'
                                : 'bg-zinc-100 text-zinc-500 border border-zinc-200'
                            }`}
                          >
                            <Briefcase className="w-3 h-3 text-amber-600 shrink-0" />
                            {openRoles} {openRoles === 1 ? 'Job' : 'Jobs'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Smart Pagination Bar */}
              <PaginationControls
                page={companyPage}
                totalPages={companyPagination.totalPages}
                total={companyPagination.total}
                limit={companyPagination.limit}
                onPageChange={(p) => fetchCompanies(p, companyPagination.limit)}
                onLimitChange={(l) => {
                  setCompanyLimit(l);
                  setCompanyPagination((prev) => ({ ...prev, limit: l }));
                  fetchCompanies(1, l);
                }}
                itemName="companies"
              />
            </div>
          </div>
        )}

        {/* ----------------- TAB 5: RECRUITER OUTREACH HUB ----------------- */}
        {activeTab === 'leads' && (
          <div className="space-y-4 animate-in fade-in duration-200">
            {/* Control & Batch Bar */}
            <div className="liquid-glass rounded-3xl p-4 sm:p-5 border border-white/90 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2 w-full md:w-auto flex-1">
                <div className="relative flex-1 max-w-md">
                  <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={leadSearch}
                    onChange={(e) => setLeadSearch(e.target.value)}
                    placeholder="Search recruiter name, company, email..."
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-2xl pl-9 pr-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                </div>

                <select
                  value={leadStatus}
                  onChange={(e) => setLeadStatus(e.target.value)}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="pending_review">Pending Review (Quarantined)</option>
                  <option value="approved">Approved</option>
                  <option value="sent">Dispatched / Sent</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>

              <div className="flex items-center gap-2 w-full md:w-auto justify-end flex-wrap">
                <button
                  onClick={handleApproveAllPending}
                  className="liquid-pill px-3 py-2 rounded-2xl text-xs font-semibold text-emerald-800 hover:text-emerald-950 flex items-center gap-1.5 cursor-pointer shadow-2xs"
                  title="Approve all pending review leads on current view"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Approve Visible</span>
                </button>

                <button
                  onClick={handleDispatchApprovedLeads}
                  disabled={dispatchingLeads}
                  className="liquid-pill-dark px-3.5 py-2 rounded-2xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <Send className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{dispatchingLeads ? 'Dispatching...' : 'Dispatch Approved'}</span>
                </button>

                <button
                  onClick={() => setAddLeadOpen(true)}
                  className="liquid-pill px-3.5 py-2 rounded-2xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-2xs"
                >
                  <Plus className="w-3.5 h-3.5 text-zinc-600" />
                  <span>Add Lead</span>
                </button>
              </div>
            </div>

            {dispatchMessage && (
              <div className="p-3.5 rounded-2xl bg-cyan-50 border border-cyan-200 text-xs text-cyan-900 font-semibold shadow-2xs">
                {dispatchMessage}
              </div>
            )}

            {/* Leads Table */}
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60 text-xs text-zinc-500 font-semibold px-2">
                <span>Showing {leads.length} of {leadPagination.total.toLocaleString()} leads</span>
                <span>Page {leadPage} of {leadPagination.totalPages}</span>
              </div>

              {leadsLoading ? (
                <div className="py-20 text-center text-xs text-zinc-400">Loading recruiter leads...</div>
              ) : leads.length === 0 ? (
                <div className="py-20 text-center text-xs text-zinc-500">No leads found matching filters.</div>
              ) : (
                <div className="space-y-2">
                  {leads.map((l) => (
                    <div
                      key={l.lead_id}
                      onClick={() => openLead(l.lead_id)}
                      className="liquid-row rounded-2xl p-3.5 flex items-center justify-between gap-3 cursor-pointer group"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-xs text-zinc-900 group-hover:text-cyan-700 transition">
                            {l.contact_name || 'Hiring Lead'}
                          </span>
                          <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-zinc-100 text-zinc-600 border border-zinc-200">
                            {l.contact_type}
                          </span>
                          <span className={`text-[10px] px-2 py-0.2 rounded-full font-semibold border ${
                            l.outreach_status === 'approved' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                            l.outreach_status === 'sent' ? 'bg-cyan-50 text-cyan-800 border-cyan-200' :
                            l.outreach_status === 'rejected' ? 'bg-rose-50 text-rose-800 border-rose-200' :
                            'bg-amber-50 text-amber-800 border-amber-200'
                          }`}>
                            {l.outreach_status}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-500 flex items-center gap-3">
                          <span className="font-semibold text-zinc-800">{l.company_name}</span>
                          <span>•</span>
                          <span className="font-mono text-zinc-600">{l.contact_email}</span>
                          {l.role_title && <span>• {l.role_title}</span>}
                        </div>
                      </div>

                      <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 group-hover:text-zinc-900 transition" />
                    </div>
                  ))}
                </div>
              )}

              {/* Smart Pagination Bar */}
              <PaginationControls
                page={leadPage}
                totalPages={leadPagination.totalPages}
                total={leadPagination.total}
                limit={leadPagination.limit}
                onPageChange={(p) => fetchLeads(p, leadPagination.limit)}
                onLimitChange={(l) => {
                  setLeadLimit(l);
                  setLeadPagination((prev) => ({ ...prev, limit: l }));
                  fetchLeads(1, l);
                }}
                itemName="leads"
              />
            </div>
          </div>
        )}

        {/* ----------------- TAB 6: HITL SAFETY TICKETS ----------------- */}
        {activeTab === 'hitl' && (
          <div className="space-y-4 animate-in fade-in duration-200">
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-zinc-900 tracking-tight flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-amber-600" />
                  <span>Human-in-the-Loop Application Barriers</span>
                </h3>
                <p className="text-xs text-zinc-500">
                  When auto-application forms require custom answers, tickets are quarantined here for one-click admin confirmation
                </p>
              </div>

              <select
                value={ticketStatus}
                onChange={(e) => setTicketStatus(e.target.value)}
                className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="pending">Pending Intervention</option>
                <option value="resolved">Resolved</option>
                <option value="dismissed">Dismissed</option>
              </select>
            </div>

            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-3">
              {ticketsLoading ? (
                <div className="py-20 text-center text-xs text-zinc-400">Loading intervention tickets...</div>
              ) : tickets.length === 0 ? (
                <div className="py-20 text-center text-xs text-zinc-500">
                  No pending intervention tickets. The pipeline is running smoothly without form blockers!
                </div>
              ) : (
                <div className="space-y-2">
                  {tickets.map((t) => (
                    <div
                      key={t.ticket_id}
                      onClick={() => openTicket(t.ticket_id)}
                      className="liquid-row rounded-2xl p-4 flex items-center justify-between gap-3 cursor-pointer group"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-zinc-900 group-hover:text-cyan-700 transition">
                            {t.role_title || 'Application Blocker'}
                          </span>
                          <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-amber-50 text-amber-800 border border-amber-200">
                            {t.blocker_type}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-500 flex items-center gap-3">
                          <span className="font-semibold text-zinc-800">{t.company}</span>
                          <span>•</span>
                          <span>{t.questions?.length || 0} Screening Questions</span>
                        </div>
                      </div>

                      <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 group-hover:text-zinc-900 transition" />
                    </div>
                  ))}
                </div>
              )}

              {/* Smart Pagination Bar */}
              <PaginationControls
                page={ticketPage}
                totalPages={ticketPagination.totalPages}
                total={ticketPagination.total}
                limit={ticketPagination.limit}
                onPageChange={(p) => fetchTickets(p, ticketPagination.limit)}
                onLimitChange={(l) => {
                  setTicketLimit(l);
                  setTicketPagination((prev) => ({ ...prev, limit: l }));
                  fetchTickets(1, l);
                }}
                itemName="tickets"
              />
            </div>
          </div>
        )}

        {/* ----------------- TAB 7: AGENT RADAR LIVE DAG ----------------- */}
        {activeTab === 'radar' && <AgentRadarView />}

        {/* ----------------- TAB 8: CANDIDATE PROFILE & CREDENTIALS (PHASE 2) ----------------- */}
        {activeTab === 'profile' && <ProfileView />}
      </main>

      {/* ----------------- DRAWERS & MODALS ----------------- */}
      <JobDetailDrawer
        jobUrl={selectedJobUrl}
        onClose={closeJob}
        onJobUpdated={() => {
          fetchStats();
          if (activeTab === 'jobs') fetchJobs(jobPage);
        }}
        onOpenLead={(lead) => {
          setSelectedJobUrl(null);
          setSelectedLeadId(lead.lead_id);
          setActiveTab('leads');
        }}
        onOpenTicket={(ticketId) => {
          setSelectedJobUrl(null);
          setSelectedTicketId(ticketId);
        }}
      />

      <CompanyDetailDrawer
        companyName={selectedCompany}
        onClose={closeCompany}
        onCompanyUpdated={() => {
          fetchStats();
          if (activeTab === 'companies') fetchCompanies(companyPage);
        }}
        onOpenJob={(jobUrl) => {
          setSelectedCompany(null);
          setSelectedJobUrl(jobUrl);
          setActiveTab('jobs');
        }}
        onOpenLead={(lead) => {
          setSelectedCompany(null);
          setSelectedLeadId(lead.lead_id);
          setActiveTab('leads');
        }}
      />

      <LeadDetailDrawer
        leadId={selectedLeadId}
        onClose={closeLead}
        onLeadUpdated={() => {
          fetchStats();
          if (activeTab === 'leads') fetchLeads(leadPage);
        }}
        onOpenCompany={(companyName) => {
          setSelectedLeadId(null);
          setSelectedCompany(companyName);
          setActiveTab('companies');
        }}
      />

      <HitlTicketModal
        ticketId={selectedTicketId}
        onClose={closeTicket}
        onTicketResolved={() => {
          fetchStats();
          fetchTickets(ticketPage);
        }}
      />

      <AddJobModal
        isOpen={addJobOpen}
        onClose={() => setAddJobOpen(false)}
        onJobAdded={() => {
          fetchStats();
          fetchJobs(1);
        }}
      />

      <AddCompanyModal
        isOpen={addCompanyOpen}
        onClose={() => setAddCompanyOpen(false)}
        onCompanyAdded={() => {
          fetchStats();
          fetchCompanies(1);
        }}
      />

      <AddLeadModal
        isOpen={addLeadOpen}
        onClose={() => setAddLeadOpen(false)}
        onLeadAdded={() => {
          fetchStats();
          fetchLeads(1);
        }}
      />
    </div>
  );
}


export default function DashboardPage(props: DashboardPageProps) {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-zinc-950/20 border-t-zinc-950 animate-spin" />
          <span className="text-xs font-semibold text-zinc-500">Loading ApplyPilot Studio...</span>
        </div>
      }
    >
      <DashboardContent {...props} />
    </Suspense>
  );
}
