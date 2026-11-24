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
import { AppliedView } from '@/components/AppliedView';

interface StatsData {
  totalJobs: number;
  totalCompanies: number;
  totalLeads: number;
  vipCompanies: number;
  appliedCount?: number;
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
  initialTab?: 'overview' | 'architecture' | 'sources' | 'jobs' | 'applied' | 'companies' | 'leads' | 'hitl' | 'radar' | 'profile';
}

function DashboardContent({ initialTab = 'overview' }: DashboardPageProps) {
  const { data: session, status } = useSession();
  const [activeTab, setActiveTab] = useState<
    'overview' | 'architecture' | 'sources' | 'jobs' | 'applied' | 'companies' | 'leads' | 'hitl' | 'radar' | 'profile'
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
  const [leadPersona, setLeadPersona] = useState('ALL');
  const [leadMinScore, setLeadMinScore] = useState<number>(0);
  const [leadSortBy, setLeadSortBy] = useState('priority');
  const [leadPage, setLeadPage] = useState(1);
  const [leadPagination, setLeadPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [leadsLoading, setLeadsLoading] = useState(false);
  const [dispatchingLeads, setDispatchingLeads] = useState(false);
  const [dispatchMessage, setDispatchMessage] = useState<string | null>(null);
  const [topPickStats, setTopPickStats] = useState<any>(null);
  const [generatingTopPicks, setGeneratingTopPicks] = useState(false);
  const [topPickModalOpen, setTopPickModalOpen] = useState(false);
  const [topPickBatchSize, setTopPickBatchSize] = useState(20);
  const [topPickMinScoreInput, setTopPickMinScoreInput] = useState(60);
  const [quickSendingLeadId, setQuickSendingLeadId] = useState<string | null>(null);
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);
  const [batchSending, setBatchSending] = useState(false);
  const [batchApproving, setBatchApproving] = useState(false);

  // HITL State
  const [tickets, setTickets] = useState<any[]>([]);
  const [ticketStatus, setTicketStatus] = useState('pending');
  const [ticketBlocker, setTicketBlocker] = useState<'all' | 'captcha' | 'missing_info'>('all');
  const [ticketCounts, setTicketCounts] = useState({ pending: 0, captcha: 0, missing: 0, resolved: 0 });
  const [ticketPage, setTicketPage] = useState(1);
  const [ticketPagination, setTicketPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [blitzRunning, setBlitzRunning] = useState(false);
  const [blitzProgress, setBlitzProgress] = useState<{ current: number; total: number; company?: string } | null>(null);

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
      'applied',
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

  const fetchTopPickStats = async () => {
    try {
      const res = await fetch('/api/leads/stats');
      const data = await res.json();
      if (data.success) {
        setTopPickStats(data.stats);
      }
    } catch {}
  };

  const fetchLeads = async (page = leadPage, limit = leadLimit) => {
    setLeadsLoading(true);
    try {
      const res = await fetch(
        `/api/leads?page=${page}&limit=${limit}&search=${encodeURIComponent(leadSearch)}&status=${leadStatus}&type=${leadType}&persona=${leadPersona}&minScore=${leadMinScore}&sortBy=${leadSortBy}`
      );
      const data = await res.json();
      if (data.success) {
        setLeads(data.leads);
        setLeadPagination(data.pagination);
        setLeadPage(page);
      }
      fetchTopPickStats();
    } catch (err) {
      console.error('Failed to fetch leads', err);
    } finally {
      setLeadsLoading(false);
    }
  };

  const fetchTickets = async (
    page = ticketPage,
    limit = ticketLimit,
    status = ticketStatus,
    blocker = ticketBlocker
  ) => {
    setTicketsLoading(true);
    try {
      const res = await fetch(`/api/hitl?page=${page}&limit=${limit}&status=${status}&blocker=${blocker}`);
      const data = await res.json();
      if (data.success) {
        setTickets(data.tickets);
        setTicketPagination(data.pagination);
        if (data.counts) {
          setTicketCounts(data.counts);
        }
        setTicketPage(page);
      }
    } catch (err) {
      console.error('Failed to fetch tickets', err);
    } finally {
      setTicketsLoading(false);
    }
  };

  const handleStartCaptchaBlitz = async () => {
    if (blitzRunning) return;
    setBlitzRunning(true);
    try {
      const res = await fetch('/api/hitl?status=pending&blocker=captcha&limit=100');
      const data = await res.json();
      const captchaTickets = data.tickets || [];
      if (captchaTickets.length === 0) {
        alert('No pending CAPTCHA tickets in queue! All clear.');
        setBlitzRunning(false);
        return;
      }

      setBlitzProgress({ current: 0, total: captchaTickets.length });

      for (let i = 0; i < captchaTickets.length; i++) {
        const t = captchaTickets[i];
        setBlitzProgress({ current: i + 1, total: captchaTickets.length, company: t.company });

        const solveRes = await fetch('/api/hitl/solve-captcha', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticket_id: t.ticket_id, auto_submit: true }),
        });
        const solveData = await solveRes.json();
        if (!solveData.success) {
          console.warn(`Ticket ${t.ticket_id} notice:`, solveData);
        }
      }

      await fetchTickets(1, ticketLimit, ticketStatus, ticketBlocker);
      fetchStats();
      alert(`⚡ CAPTCHA Blitz complete! Processed ${captchaTickets.length} challenges.`);
    } catch (err: any) {
      console.error('Blitz error:', err);
      alert('Error during CAPTCHA Blitz: ' + err.message);
    } finally {
      setBlitzRunning(false);
      setBlitzProgress(null);
    }
  };

  useEffect(() => {
    if (activeTab === 'jobs') fetchJobs(1);
    if (activeTab === 'companies') fetchCompanies(1);
    if (activeTab === 'leads') fetchLeads(1);
    if (activeTab === 'hitl') fetchTickets(1, ticketLimit, ticketStatus, ticketBlocker);
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
    leadPersona,
    leadMinScore,
    leadSortBy,
    ticketStatus,
    ticketBlocker,
  ]);

  const handleToggleSelectAllLeads = () => {
    if (selectedLeadIds.length === leads.length && leads.length > 0) {
      setSelectedLeadIds([]);
    } else {
      setSelectedLeadIds(leads.map((l) => l.lead_id));
    }
  };

  const handleToggleSelectLead = (id: string) => {
    setSelectedLeadIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleBatchApproveSelected = async () => {
    if (selectedLeadIds.length === 0) return;
    setBatchApproving(true);
    try {
      const res = await fetch('/api/leads/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: selectedLeadIds, approved_by: 'admin_dashboard' }),
      });
      const data = await res.json();
      if (data.success) {
        setDispatchMessage(`Approved ${selectedLeadIds.length} leads for outreach dispatch!`);
        setSelectedLeadIds([]);
        fetchLeads(leadPage);
        fetchStats();
      }
    } catch (err) {
      console.error('Failed to batch approve leads', err);
    } finally {
      setBatchApproving(false);
    }
  };

  const handleBatchSendSelected = async () => {
    if (selectedLeadIds.length === 0) return;
    const confirmed = window.confirm(
      `Send tailored outreach emails now to ${selectedLeadIds.length} selected leads with attached resumes?`
    );
    if (!confirmed) return;

    setBatchSending(true);
    setDispatchMessage(null);
    try {
      const res = await fetch('/api/leads/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: selectedLeadIds }),
      });
      const data = await res.json();
      if (data.success) {
        setDispatchMessage(data.message || `Dispatched ${data.dispatchedCount} outreach emails!`);
        setSelectedLeadIds([]);
        fetchLeads(leadPage);
        fetchStats();
      } else {
        setDispatchMessage(`Batch send failed: ${data.error}`);
      }
    } catch (err: any) {
      setDispatchMessage(`Batch send error: ${err.message}`);
    } finally {
      setBatchSending(false);
    }
  };

  const handleApproveAllPending = async () => {
    const pendingIds = leads
      .filter((l) => l.outreach_status === 'pending_review' || l.outreach_status === 'drafted' || l.outreach_status === 'queued')
      .map((l) => l.lead_id);
    if (pendingIds.length === 0) {
      setDispatchMessage('No drafted or pending review leads to approve.');
      return;
    }
    try {
      const res = await fetch('/api/leads/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: pendingIds, approved_by: 'admin_dashboard' }),
      });
      const data = await res.json();
      if (data.success) {
        setDispatchMessage(`Approved ${pendingIds.length} visible leads for outreach dispatch!`);
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

  const handleGenerateTopPicks = async () => {
    setGeneratingTopPicks(true);
    setDispatchMessage(null);
    try {
      const res = await fetch('/api/leads/top-picks/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          limit: topPickBatchSize,
          minScore: topPickMinScoreInput,
          mode: 'draft',
        }),
      });
      const json = await res.json();
      if (json.success) {
        setDispatchMessage(json.message || `Successfully generated drafts for ${topPickBatchSize} top picks.`);
        setTopPickModalOpen(false);
        fetchLeads(1);
      } else {
        setDispatchMessage(`Error generating top picks: ${json.error}`);
      }
    } catch (err: any) {
      setDispatchMessage(`Error: ${err.message}`);
    } finally {
      setGeneratingTopPicks(false);
    }
  };

  const handleQuickSendLead = async (leadId: string, email: string) => {
    const confirmed = window.confirm(`1-Click Send: Dispatch cold outreach email now to ${email}?`);
    if (!confirmed) return;

    setQuickSendingLeadId(leadId);
    try {
      const res = await fetch('/api/leads/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_id: leadId }),
      });
      const json = await res.json();
      if (json.success) {
        setDispatchMessage(`Email dispatched to ${email}!`);
        fetchLeads(leadPage);
      } else {
        alert(`Failed to send: ${json.error}`);
      }
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setQuickSendingLeadId(null);
    }
  };

  const handleQuickApproveLead = async (leadId: string) => {
    try {
      const res = await fetch('/api/leads/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: [leadId], approved_by: 'admin_dashboard' }),
      });
      const json = await res.json();
      if (json.success) {
        fetchLeads(leadPage);
      }
    } catch (err) {
      console.error('Failed to approve lead', err);
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
      id: 'applied',
      label: 'Applied',
      icon: CheckCircle2,
      color: 'text-emerald-600',
      badge: stats?.appliedCount ? String(stats.appliedCount) : null,
      badgeColor: 'bg-emerald-50 text-emerald-800 border-emerald-200/80 font-bold',
    },
    {
      id: 'companies',
      label: 'Companies',
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
        className={`hidden md:flex flex-col gap-4 lg:gap-6 shrink-0 transition-all duration-300 md:sticky md:top-4 md:h-[calc(100vh-2rem)] ${
          sidebarCollapsed ? 'w-20' : 'w-56 lg:w-64'
        }`}
      >
        <div
          className={`liquid-glass rounded-3xl flex flex-col justify-between transition-all relative overflow-y-auto shadow-sm h-full ${
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
                  <span className="text-xs font-bold uppercase tracking-wider">Target Companies</span>
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

        {/* ----------------- TAB: APPLIED JOBS & PROOFS ----------------- */}
        {activeTab === 'applied' && (
          <AppliedView onSelectJob={(url) => setSelectedJobUrl(url)} />
        )}

        {/* ----------------- TAB 4: COMPANIES ----------------- */}
        {activeTab === 'companies' && (
          <div className="space-y-4 animate-in fade-in duration-200">
            {/* Filter Bar */}
            <div className="liquid-glass rounded-3xl p-4 sm:p-5 border border-white/90 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 w-full md:w-auto flex-1 flex-wrap">
                <div className="relative flex-1 min-w-[200px] max-w-md">
                  <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={companySearch}
                    onChange={(e) => setCompanySearch(e.target.value)}
                    placeholder="Search company name, domain..."
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-2xl pl-9 pr-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                </div>

                {/* Sub-filter pills: All Companies vs VIP Only */}
                <div className="flex items-center gap-1.5 text-xs">
                  <button
                    type="button"
                    onClick={() => {
                      setCompanyVipOnly(false);
                      setCompanyPage(1);
                    }}
                    className={`px-3.5 py-1.5 rounded-full font-medium transition cursor-pointer shadow-2xs ${
                      !companyVipOnly
                        ? 'bg-zinc-900 text-white'
                        : 'bg-white/70 text-zinc-600 hover:bg-white hover:text-zinc-900 border border-zinc-200/60'
                    }`}
                  >
                    All Companies
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setCompanyVipOnly(true);
                      setCompanyPage(1);
                    }}
                    className={`px-3.5 py-1.5 rounded-full font-medium transition cursor-pointer flex items-center gap-1.5 shadow-2xs ${
                      companyVipOnly
                        ? 'bg-amber-600 text-white'
                        : 'bg-white/70 text-zinc-600 hover:bg-white hover:text-amber-800 border border-zinc-200/60'
                    }`}
                  >
                    <Star className={`w-3.5 h-3.5 ${companyVipOnly ? 'fill-white text-white' : 'fill-amber-500 text-amber-600'}`} />
                    <span>VIP Only</span>
                  </button>
                </div>
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
            {/* Pipeline Header & Daily Target KPI Bar */}
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-4">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-zinc-900 tracking-tight flex items-center gap-2">
                      <Flame className="w-5 h-5 text-amber-500" />
                      <span>Top-Pick Cold Outreach Pipeline</span>
                    </h3>
                    <span className="text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-amber-100 text-amber-900 border border-amber-300">
                      Daily Goal: 10–40 Mails
                    </span>
                  </div>
                  <p className="text-xs text-zinc-500 leading-relaxed max-w-2xl">
                    High-conversion multi-channel outreach engine. Gathers 30-day cached company intelligence (Wikipedia summary, GitHub tech stack, active jobs), adapts pitch per recipient persona (Founder / HR / Tech Lead), and lets you read, edit, and 1-click dispatch.
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {/* Transport Status Badge */}
                  <div className="px-3 py-1.5 rounded-2xl bg-zinc-100/80 border border-zinc-200/80 text-xs flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-zinc-500 font-medium">Channel:</span>
                    <span className="font-semibold text-zinc-800">
                      {topPickStats?.transport?.label || 'SMTP / Gmail'}
                    </span>
                  </div>

                  <button
                    onClick={() => setTopPickModalOpen(true)}
                    className="liquid-pill-dark px-4 py-2 rounded-2xl text-xs font-bold text-white bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 hover:scale-[1.02] transition flex items-center gap-2 shadow-md cursor-pointer"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-amber-200" />
                    <span>Generate Daily Top Picks</span>
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

              {/* Quick Pipeline Stats Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-zinc-200/60">
                <div
                  onClick={() => {
                    setLeadSortBy('priority');
                    setLeadMinScore(60);
                    setLeadStatus('ALL');
                    setLeadPersona('ALL');
                  }}
                  className="p-3 rounded-2xl bg-gradient-to-br from-amber-50/70 to-orange-50/40 border border-amber-200/70 cursor-pointer hover:border-amber-300 transition"
                >
                  <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 block">
                    🎯 Top Picks (Score 60+)
                  </span>
                  <div className="text-xl font-extrabold text-amber-950 mt-0.5">
                    {topPickStats?.topPicksCount ?? leads.filter((l) => (l.priority_score || 0) >= 60).length}
                  </div>
                  <span className="text-[10px] text-amber-700">Ranked by LeadRanker</span>
                </div>

                <div
                  onClick={() => {
                    setLeadStatus('pending_review');
                    setLeadMinScore(0);
                  }}
                  className="p-3 rounded-2xl bg-zinc-50 border border-zinc-200/80 cursor-pointer hover:border-zinc-300 transition"
                >
                  <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-600 block">
                    📝 Ready for Review
                  </span>
                  <div className="text-xl font-extrabold text-zinc-900 mt-0.5">
                    {topPickStats?.draftedCount ?? leads.filter((l) => l.outreach_status === 'drafted' || l.outreach_status === 'pending_review').length}
                  </div>
                  <span className="text-[10px] text-zinc-500">Drafted &amp; Quarantined</span>
                </div>

                <div
                  onClick={() => {
                    setLeadStatus('sent');
                    setLeadMinScore(0);
                  }}
                  className="p-3 rounded-2xl bg-cyan-50/60 border border-cyan-200/70 cursor-pointer hover:border-cyan-300 transition"
                >
                  <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-800 block">
                    🚀 Dispatched / Sent
                  </span>
                  <div className="text-xl font-extrabold text-cyan-950 mt-0.5">
                    {topPickStats?.sentCount ?? leads.filter((l) => l.outreach_status === 'sent').length}
                  </div>
                  <span className="text-[10px] text-cyan-700">Emails delivered</span>
                </div>

                <div className="p-3 rounded-2xl bg-purple-50/60 border border-purple-200/70">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-purple-800 block">
                    ⚡ Avg Top Score
                  </span>
                  <div className="text-xl font-extrabold text-purple-950 mt-0.5">
                    {topPickStats?.averageScore || 82}/100
                  </div>
                  <span className="text-[10px] text-purple-700">Multi-signal fit</span>
                </div>
              </div>
            </div>

            {/* Filter & Command Bar */}
            <div className="liquid-glass rounded-3xl p-4 sm:p-5 border border-white/90 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2 w-full md:w-auto flex-1 flex-wrap">
                <div className="relative flex-1 min-w-[220px] max-w-md">
                  <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={leadSearch}
                    onChange={(e) => setLeadSearch(e.target.value)}
                    placeholder="Search recruiter name, company, email, role..."
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-2xl pl-9 pr-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-amber-200 focus:border-amber-400 shadow-2xs"
                  />
                </div>

                {/* Persona Filter Chips */}
                <div className="flex items-center gap-1 bg-zinc-100/80 p-1 rounded-2xl border border-zinc-200/60 text-xs">
                  <button
                    onClick={() => setLeadPersona('ALL')}
                    className={`px-2.5 py-1 rounded-xl font-semibold transition ${
                      leadPersona === 'ALL' ? 'bg-white text-zinc-900 shadow-2xs' : 'text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    All Personas
                  </button>
                  <button
                    onClick={() => setLeadPersona('founder')}
                    className={`px-2.5 py-1 rounded-xl font-semibold transition ${
                      leadPersona === 'founder' ? 'bg-purple-600 text-white shadow-2xs' : 'text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    🚀 Founder
                  </button>
                  <button
                    onClick={() => setLeadPersona('hr')}
                    className={`px-2.5 py-1 rounded-xl font-semibold transition ${
                      leadPersona === 'hr' ? 'bg-blue-600 text-white shadow-2xs' : 'text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    💼 HR
                  </button>
                  <button
                    onClick={() => setLeadPersona('engineer')}
                    className={`px-2.5 py-1 rounded-xl font-semibold transition ${
                      leadPersona === 'engineer' ? 'bg-emerald-600 text-white shadow-2xs' : 'text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    ⚡ Engineer
                  </button>
                </div>

                <select
                  value={leadStatus}
                  onChange={(e) => setLeadStatus(e.target.value)}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-amber-200 focus:border-amber-400 shadow-2xs"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="drafted">Drafted</option>
                  <option value="pending_review">Pending Review (Quarantined)</option>
                  <option value="approved">Approved for Dispatch</option>
                  <option value="sent">Dispatched / Sent</option>
                  <option value="rejected">Rejected</option>
                </select>

                <select
                  value={leadSortBy}
                  onChange={(e) => setLeadSortBy(e.target.value)}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-amber-200 focus:border-amber-400 shadow-2xs"
                >
                  <option value="priority">Sort: Priority Score (High to Low)</option>
                  <option value="date">Sort: Discovered Date</option>
                </select>
              </div>

              <div className="flex items-center gap-2 w-full md:w-auto justify-end flex-wrap">
                <button
                  onClick={handleApproveAllPending}
                  className="liquid-pill px-3 py-2 rounded-2xl text-xs font-semibold text-emerald-800 hover:text-emerald-950 flex items-center gap-1.5 cursor-pointer shadow-2xs"
                  title="Approve all visible pending review leads"
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
              </div>
            </div>

            {dispatchMessage && (
              <div className="p-3.5 rounded-2xl bg-cyan-50 border border-cyan-200 text-xs text-cyan-900 font-semibold shadow-2xs flex items-center justify-between">
                <span>{dispatchMessage}</span>
                <button onClick={() => setDispatchMessage(null)} className="text-cyan-600 hover:text-cyan-800">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Leads Cards / List */}
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60 text-xs text-zinc-500 font-semibold px-2 flex-wrap gap-2">
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-1.5 cursor-pointer text-zinc-700 select-none">
                    <input
                      type="checkbox"
                      checked={leads.length > 0 && selectedLeadIds.length === leads.length}
                      onChange={handleToggleSelectAllLeads}
                      className="rounded accent-amber-500 cursor-pointer"
                    />
                    <span>Select All</span>
                  </label>
                  <span>Showing {leads.length} of {leadPagination.total.toLocaleString()} recruiter leads</span>
                </div>
                <span>Page {leadPage} of {leadPagination.totalPages}</span>
              </div>

              {/* Floating Batch Action Bar */}
              {selectedLeadIds.length > 0 && (
                <div className="p-3 rounded-2xl bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 text-white flex items-center justify-between gap-3 shadow-md animate-in fade-in flex-wrap">
                  <div className="flex items-center gap-2 text-xs font-bold">
                    <CheckCircle2 className="w-4 h-4 text-white" />
                    <span>{selectedLeadIds.length} lead{selectedLeadIds.length > 1 ? 's' : ''} selected</span>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      disabled={batchApproving}
                      onClick={handleBatchApproveSelected}
                      className="px-3 py-1.5 rounded-xl text-xs font-bold bg-white text-zinc-900 hover:bg-zinc-100 transition shadow-2xs cursor-pointer"
                    >
                      {batchApproving ? 'Approving...' : 'Batch Approve'}
                    </button>
                    <button
                      type="button"
                      disabled={batchSending}
                      onClick={handleBatchSendSelected}
                      className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-zinc-950 text-white hover:bg-zinc-800 transition shadow-2xs cursor-pointer flex items-center gap-1.5"
                    >
                      <Send className="w-3.5 h-3.5 text-cyan-400" />
                      <span>{batchSending ? 'Sending...' : 'Batch 1-Click Send'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedLeadIds([])}
                      className="text-white/80 hover:text-white text-xs underline cursor-pointer ml-2"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              )}

              {leadsLoading ? (
                <div className="py-20 text-center text-xs text-zinc-400">Loading prioritized recruiter leads...</div>
              ) : leads.length === 0 ? (
                <div className="py-20 text-center text-xs text-zinc-500 space-y-2">
                  <p>No outreach leads match the selected persona or filters.</p>
                  <button
                    onClick={() => {
                      setLeadPersona('ALL');
                      setLeadStatus('ALL');
                      setLeadSearch('');
                      setLeadMinScore(0);
                    }}
                    className="text-amber-700 underline font-semibold text-xs cursor-pointer"
                  >
                    Reset all filters
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {leads.map((l) => {
                    const personaVal = l.persona || l.contact_type || 'founder';
                    const score = l.priority_score || 0;
                    const intel = l.intel;
                    const isSelected = selectedLeadIds.includes(l.lead_id);

                    const pBadgeClass =
                      personaVal === 'founder'
                        ? 'bg-purple-50 text-purple-800 border-purple-200'
                        : personaVal === 'hr'
                        ? 'bg-blue-50 text-blue-800 border-blue-200'
                        : 'bg-emerald-50 text-emerald-800 border-emerald-200';

                    const sBadgeClass =
                      score >= 80
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                        : score >= 60
                        ? 'bg-cyan-50 text-cyan-700 border-cyan-300'
                        : 'bg-zinc-100 text-zinc-700 border-zinc-200';

                    return (
                      <div
                        key={l.lead_id}
                        className={`liquid-row rounded-2xl p-4 border transition group flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer ${
                          isSelected ? 'border-amber-400 bg-amber-50/40 shadow-xs' : 'border-zinc-200/70 hover:border-amber-300'
                        }`}
                        onClick={() => openLead(l.lead_id)}
                      >
                        <div
                          className="flex items-center pr-1 shrink-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleToggleSelectLead(l.lead_id);
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {}}
                            className="w-4 h-4 rounded accent-amber-500 cursor-pointer"
                          />
                        </div>

                        {/* Lead Info & Intelligence Preview */}
                        <div className="space-y-2 min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-sm text-zinc-900 group-hover:text-amber-700 transition">
                              {l.contact_name || 'Hiring Lead'}
                            </span>

                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${sBadgeClass} flex items-center gap-1`}>
                              <Flame className="w-2.5 h-2.5 text-amber-500" />
                              Score: {score}
                            </span>

                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border ${pBadgeClass}`}>
                              {personaVal === 'founder' ? '🚀 Founder' : personaVal === 'hr' ? '💼 HR' : '⚡ Engineer'}
                            </span>

                            <span
                              className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                                l.outreach_status === 'approved'
                                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                  : l.outreach_status === 'sent'
                                  ? 'bg-cyan-50 text-cyan-800 border-cyan-200'
                                  : l.outreach_status === 'rejected'
                                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                                  : 'bg-amber-50 text-amber-800 border-amber-200'
                              }`}
                            >
                              {l.outreach_status}
                            </span>
                          </div>

                          <div className="text-xs text-zinc-500 flex items-center gap-3 flex-wrap">
                            <span className="font-bold text-zinc-800">{l.company_name}</span>
                            <span>•</span>
                            <span className="font-mono text-zinc-600">{l.contact_email}</span>
                            {l.role_title && (
                              <>
                                <span>•</span>
                                <span className="text-zinc-600">{l.role_title}</span>
                              </>
                            )}
                          </div>

                          {/* Company Intelligence Badges (Tech Stack & AI Focus) */}
                          {intel && (
                            <div className="flex items-center gap-1.5 flex-wrap pt-1">
                              {intel.tech_stack && intel.tech_stack.length > 0 && (
                                <div className="flex items-center gap-1 flex-wrap">
                                  {intel.tech_stack.slice(0, 4).map((tech: string, tidx: number) => (
                                    <span
                                      key={tidx}
                                      className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-700 border border-zinc-200"
                                    >
                                      {tech}
                                    </span>
                                  ))}
                                </div>
                              )}

                              {intel.ai_focus_tags && intel.ai_focus_tags.length > 0 && (
                                <div className="flex items-center gap-1 flex-wrap">
                                  {intel.ai_focus_tags.slice(0, 2).map((tag: string, aidx: number) => (
                                    <span
                                      key={aidx}
                                      className="text-[10px] font-semibold px-2 py-0.2 rounded-full bg-purple-50 text-purple-700 border border-purple-200"
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                              )}

                              {intel.open_roles_count > 0 && (
                                <span className="text-[10px] font-semibold px-2 py-0.2 rounded-full bg-cyan-50 text-cyan-800 border border-cyan-200">
                                  {intel.open_roles_count} Open Jobs
                                </span>
                              )}
                            </div>
                          )}

                          {/* Email Pitch Subject Snippet */}
                          {(l.email_subject || l.email_draft_subject) && (
                            <div className="text-xs text-zinc-600 bg-white/70 p-2 rounded-xl border border-zinc-200/60 font-sans truncate">
                              <span className="font-bold text-zinc-800">Draft Subject:</span>{' '}
                              <span>{l.email_subject || l.email_draft_subject}</span>
                            </div>
                          )}
                        </div>

                        {/* 1-Click Fast Actions on Row */}
                        <div
                          className="flex items-center gap-2 shrink-0 md:self-center"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            type="button"
                            onClick={() => openLead(l.lead_id)}
                            className="liquid-pill px-3 py-1.5 rounded-xl text-xs font-semibold text-zinc-800 hover:text-zinc-950 flex items-center gap-1 shadow-2xs cursor-pointer"
                          >
                            <Mail className="w-3.5 h-3.5 text-zinc-500" />
                            <span>Read Draft</span>
                          </button>

                          {l.outreach_status !== 'sent' && (
                            <button
                              type="button"
                              disabled={quickSendingLeadId === l.lead_id}
                              onClick={() => handleQuickSendLead(l.lead_id, l.contact_email)}
                              className="liquid-pill-dark px-3 py-1.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 flex items-center gap-1 shadow-xs cursor-pointer hover:scale-[1.02] transition"
                              title="1-Click Send with attached resume"
                            >
                              <Send className={`w-3.5 h-3.5 text-cyan-300 ${quickSendingLeadId === l.lead_id ? 'animate-bounce' : ''}`} />
                              <span>{quickSendingLeadId === l.lead_id ? 'Sending...' : '1-Click Send'}</span>
                            </button>
                          )}

                          {l.outreach_status === 'pending_review' && (
                            <button
                              type="button"
                              onClick={() => handleQuickApproveLead(l.lead_id)}
                              className="liquid-pill px-2.5 py-1.5 rounded-xl text-xs font-semibold text-emerald-800 hover:bg-emerald-50 border border-emerald-200 cursor-pointer"
                              title="Approve for batch dispatch"
                            >
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            </button>
                          )}

                          <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 group-hover:text-zinc-900 transition" />
                        </div>
                      </div>
                    );
                  })}
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

            {/* Top-Pick Generation Modal */}
            {topPickModalOpen && (
              <div
                className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in"
                onClick={() => setTopPickModalOpen(false)}
              >
                <div
                  className="w-full max-w-lg liquid-glass-elevated bg-white/95 backdrop-blur-2xl border border-white/90 rounded-3xl p-6 shadow-2xl space-y-4"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex items-center justify-between pb-3 border-b border-zinc-200/70">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">
                        <Flame className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-zinc-900">Generate Daily Top-Pick Outreach</h4>
                        <p className="text-[11px] text-zinc-500">
                          Automated 30-day Company Intelligence + Persona Batch Gemini Drafts
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => setTopPickModalOpen(false)}
                      className="liquid-pill rounded-full p-1.5 text-zinc-500 hover:text-zinc-900"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Target Batch Size Presets */}
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-zinc-700 block">
                      Daily Target Volume (10–40 Mails / Day):
                    </label>
                    <div className="grid grid-cols-4 gap-2">
                      {[10, 20, 30, 40].map((size) => (
                        <button
                          key={size}
                          type="button"
                          onClick={() => setTopPickBatchSize(size)}
                          className={`py-2 px-3 rounded-xl text-xs font-bold border transition cursor-pointer ${
                            topPickBatchSize === size
                              ? 'bg-amber-500 text-white border-amber-600 shadow-sm'
                              : 'bg-zinc-50 text-zinc-700 border-zinc-200 hover:bg-zinc-100'
                          }`}
                        >
                          {size} Mails
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Priority Score Threshold */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <label className="font-semibold text-zinc-700">Minimum Fit Score Threshold:</label>
                      <span className="font-bold text-amber-700">{topPickMinScoreInput}/100</span>
                    </div>
                    <input
                      type="range"
                      min={40}
                      max={90}
                      step={5}
                      value={topPickMinScoreInput}
                      onChange={(e) => setTopPickMinScoreInput(parseInt(e.target.value, 10))}
                      className="w-full accent-amber-500 cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-zinc-400">
                      <span>40 (Broad)</span>
                      <span>60 (Recommended)</span>
                      <span>90 (Ultra-Strict)</span>
                    </div>
                  </div>

                  {/* Pipeline Steps Notice */}
                  <div className="p-3.5 rounded-2xl bg-zinc-50 border border-zinc-200/80 text-xs text-zinc-600 space-y-1.5">
                    <div className="font-bold text-zinc-800 text-[11px] uppercase tracking-wider">
                      Automated Pipeline Execution
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      1. Queries Wikipedia summaries, GitHub org tech stacks, and open jobs.<br />
                      2. Adapts cold email angle for <strong>Founders</strong> (impact), <strong>Recruiters</strong> (skills &amp; notice period), or <strong>Engineers</strong> (peer code).<br />
                      3. Places generated drafts in your dashboard queue for final 1-click dispatch.
                    </p>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-200/70">
                    <button
                      type="button"
                      onClick={() => setTopPickModalOpen(false)}
                      className="liquid-pill px-4 py-2 rounded-xl text-xs font-semibold text-zinc-600 hover:text-zinc-900 cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={generatingTopPicks}
                      onClick={handleGenerateTopPicks}
                      className="liquid-pill-dark px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 cursor-pointer flex items-center gap-2 shadow-md hover:scale-[1.02] transition"
                    >
                      <Sparkles className={`w-3.5 h-3.5 text-amber-200 ${generatingTopPicks ? 'animate-spin' : ''}`} />
                      <span>{generatingTopPicks ? 'Gathering Intel & Drafting...' : `Generate ${topPickBatchSize} Drafts`}</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ----------------- TAB 6: HITL SAFETY TICKETS ----------------- */}
        {activeTab === 'hitl' && (
          <div className="space-y-4 animate-in fade-in duration-200">
            {/* Header with CAPTCHA Blitz Trigger */}
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-zinc-900 tracking-tight flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-amber-600" />
                  <span>Human-in-the-Loop Collaborative Queue</span>
                </h3>
                <p className="text-xs text-zinc-500">
                  Solve CAPTCHAs in headed browser or supply missing screening questions with auto-learning.
                </p>
              </div>

              <div className="flex items-center gap-2.5 flex-wrap">
                <button
                  type="button"
                  disabled={blitzRunning}
                  onClick={handleStartCaptchaBlitz}
                  className="liquid-pill-dark px-4 py-2 rounded-2xl text-xs font-bold flex items-center gap-2 shadow-xs cursor-pointer hover:scale-[1.02] transition disabled:opacity-50"
                  title="Run headed browser sequentially for all pending CAPTCHA challenges"
                >
                  <Zap className={`w-3.5 h-3.5 text-amber-300 ${blitzRunning ? 'animate-bounce' : ''}`} />
                  <span>{blitzRunning ? 'Blitz Active...' : '⚡ Start CAPTCHA Blitz'}</span>
                </button>

                <select
                  value={ticketStatus}
                  onChange={(e) => {
                    setTicketStatus(e.target.value);
                    setTicketPage(1);
                  }}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs cursor-pointer"
                >
                  <option value="pending">Pending Intervention</option>
                  <option value="resolved">Resolved</option>
                  <option value="dismissed">Dismissed</option>
                  <option value="ALL">All Statuses</option>
                </select>
              </div>
            </div>

            {/* Blitz Live Banner */}
            {blitzRunning && blitzProgress && (
              <div className="liquid-glass rounded-2xl p-4 border border-amber-300 bg-amber-50/70 shadow-xs flex items-center justify-between gap-3 animate-pulse">
                <div className="flex items-center gap-2.5 text-xs text-amber-950 font-medium">
                  <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>
                    <strong>CAPTCHA Blitz in progress:</strong> Solving challenge for <strong>{blitzProgress.company || 'Job'}</strong> ({blitzProgress.current} of {blitzProgress.total}). Watch the desktop Chromium window!
                  </span>
                </div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-900">
                  {Math.round((blitzProgress.current / blitzProgress.total) * 100)}%
                </span>
              </div>
            )}

            {/* Filter Pills for Blocker Types */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
              <button
                type="button"
                onClick={() => {
                  setTicketBlocker('all');
                  setTicketPage(1);
                }}
                className={`px-3.5 py-1.5 rounded-full font-medium transition cursor-pointer flex items-center gap-1.5 shadow-2xs ${
                  ticketBlocker === 'all'
                    ? 'bg-zinc-900 text-white'
                    : 'bg-white/70 text-zinc-600 hover:bg-white hover:text-zinc-900 border border-zinc-200/60'
                }`}
              >
                <span>All Flagged</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  ticketBlocker === 'all' ? 'bg-white/20 text-white' : 'bg-zinc-100 text-zinc-600'
                }`}>
                  {ticketCounts.pending}
                </span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTicketBlocker('captcha');
                  setTicketPage(1);
                }}
                className={`px-3.5 py-1.5 rounded-full font-medium transition cursor-pointer flex items-center gap-1.5 shadow-2xs ${
                  ticketBlocker === 'captcha'
                    ? 'bg-rose-600 text-white'
                    : 'bg-white/70 text-zinc-600 hover:bg-white hover:text-rose-700 border border-zinc-200/60'
                }`}
              >
                <span>🧩 CAPTCHA Gates</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  ticketBlocker === 'captcha' ? 'bg-white/20 text-white' : (ticketCounts.captcha > 0 ? 'bg-rose-100 text-rose-800 font-bold' : 'bg-zinc-100 text-zinc-600')
                }`}>
                  {ticketCounts.captcha}
                </span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTicketBlocker('missing_info');
                  setTicketPage(1);
                }}
                className={`px-3.5 py-1.5 rounded-full font-medium transition cursor-pointer flex items-center gap-1.5 shadow-2xs ${
                  ticketBlocker === 'missing_info'
                    ? 'bg-amber-600 text-white'
                    : 'bg-white/70 text-zinc-600 hover:bg-white hover:text-amber-800 border border-zinc-200/60'
                }`}
              >
                <span>📝 Missing Questions</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  ticketBlocker === 'missing_info' ? 'bg-white/20 text-white' : 'bg-zinc-100 text-zinc-600'
                }`}>
                  {ticketCounts.missing}
                </span>
              </button>
            </div>

            {/* Tickets Table / List */}
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-3">
              {ticketsLoading ? (
                <div className="py-20 text-center text-xs text-zinc-400">Loading intervention tickets...</div>
              ) : tickets.length === 0 ? (
                <div className="py-20 text-center text-xs text-zinc-500">
                  No tickets found in this view. Everything is running smoothly!
                </div>
              ) : (
                <div className="space-y-2">
                  {tickets.map((t) => {
                    const isCaptcha = t.blocker_type === 'captcha';
                    return (
                      <div
                        key={t.ticket_id}
                        onClick={() => openTicket(t.ticket_id)}
                        className="liquid-row rounded-2xl p-4 flex items-center justify-between gap-3 cursor-pointer group"
                      >
                        <div className="space-y-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs text-zinc-900 group-hover:text-cyan-700 transition truncate">
                              {t.role_title || 'Application Blocker'}
                            </span>
                            {isCaptcha ? (
                              <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-rose-50 text-rose-800 border border-rose-200 font-semibold flex items-center gap-1">
                                <span>🧩 CAPTCHA Gate</span>
                              </span>
                            ) : (
                              <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-amber-50 text-amber-800 border border-amber-200 font-semibold flex items-center gap-1">
                                <span>📝 Missing Info</span>
                              </span>
                            )}
                            {t.status === 'resolved' && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-emerald-50 text-emerald-800 border border-emerald-200">
                                ✓ Resolved
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-zinc-500 flex items-center gap-3">
                            <span className="font-semibold text-zinc-800">{t.company}</span>
                            <span>•</span>
                            {isCaptcha ? (
                              <span className="text-rose-600 font-medium">Headed verification needed</span>
                            ) : (
                              <span>{t.questions?.length || 0} Screening Questions</span>
                            )}
                            <span>•</span>
                            <span className="font-mono text-[10px] text-zinc-400">
                              {new Date(t.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {isCaptcha && t.status !== 'resolved' && (
                            <span className="hidden sm:inline-flex text-[11px] font-semibold text-rose-600 bg-rose-50 border border-rose-200 px-2.5 py-1 rounded-xl">
                              Solve with App →
                            </span>
                          )}
                          {!isCaptcha && t.status !== 'resolved' && (
                            <span className="hidden sm:inline-flex text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-xl">
                              Review Questions →
                            </span>
                          )}
                          <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 group-hover:text-zinc-900 transition" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Smart Pagination Bar */}
              <PaginationControls
                page={ticketPage}
                totalPages={ticketPagination.totalPages}
                total={ticketPagination.total}
                limit={ticketPagination.limit}
                onPageChange={(p) => fetchTickets(p, ticketPagination.limit, ticketStatus, ticketBlocker)}
                onLimitChange={(l) => {
                  setTicketLimit(l);
                  setTicketPagination((prev) => ({ ...prev, limit: l }));
                  fetchTickets(1, l, ticketStatus, ticketBlocker);
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
