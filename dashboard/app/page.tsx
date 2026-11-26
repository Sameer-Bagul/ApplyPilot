'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSession, signOut } from 'next-auth/react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
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
  UserCheck,
  Play,
  TrendingUp,
  Target,
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

export type TabType =
  | 'overview'
  | 'architecture'
  | 'sources'
  | 'jobs'
  | 'applied'
  | 'companies'
  | 'leads'
  | 'hitl'
  | 'radar'
  | 'profile';

interface DashboardPageProps {
  initialTab?: TabType;
}

function DashboardContent({ initialTab = 'overview' }: DashboardPageProps) {
  const { data: session, status } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Derive active tab from pathname if valid, else fall back to initialTab or 'overview'
  const currentTabFromPath: TabType = React.useMemo((): TabType => {
    if (!pathname) return initialTab || 'overview';
    const clean = pathname.replace(/^\//, '').split('/')[0];
    const validTabs: TabType[] = [
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
    if (validTabs.includes(clean as TabType)) {
      return clean as TabType;
    }
    return initialTab || 'overview';
  }, [pathname, initialTab]);

  const [activeTab, setActiveTab] = useState<TabType>(currentTabFromPath);

  useEffect(() => {
    setActiveTab(currentTabFromPath);
  }, [currentTabFromPath]);
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
  const [jobSort, setJobSort] = useState<string>('ranked'); // 'ranked' | 'newest' | 'company'
  const [jobWorkplace, setJobWorkplace] = useState<string>('ALL'); // 'ALL' | 'REMOTE' | 'HYBRID' | 'ONSITE'
  const [jobCategory, setJobCategory] = useState<string>('ALL'); // 'ALL' | 'AI_ML' | 'FULLSTACK' | 'BACKEND' | 'FRONTEND'
  const [jobPage, setJobPage] = useState(1);
  const [jobPagination, setJobPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [jobsLoading, setJobsLoading] = useState(false);

  // Companies State
  const [companies, setCompanies] = useState<any[]>([]);
  const [companySearch, setCompanySearch] = useState('');
  const [companyTier, setCompanyTier] = useState<string>('ALL'); // 'ALL' | 'VIP' | 'P2' | 'P3' | 'GTM_EXCLUDED'
  const [companyCluster, setCompanyCluster] = useState<string>('ALL'); // 'ALL' | 'pune' | 'magarpatta' | 'baner' | 'hinjawadi' | 'kharadi' | 'yerawada' | 'bengaluru' | 'remote' | 'us'
  const [companySector, setCompanySector] = useState('ALL');
  const [companyHasContacts, setCompanyHasContacts] = useState<string>('ALL'); // 'ALL' | 'YES' | 'NO'
  const [companyHasJobs, setCompanyHasJobs] = useState<string>('ALL'); // 'ALL' | 'YES' | 'NO'
  const [companyAts, setCompanyAts] = useState<string>('ALL'); // 'ALL' | 'greenhouse' | 'lever' | 'ashby' | 'workday' | 'custom'
  const [companySort, setCompanySort] = useState<string>('priority'); // 'priority' | 'jobs_count' | 'leads_count' | 'name' | 'created_at'
  const [companyViewMode, setCompanyViewMode] = useState<'table' | 'cards'>('table');
  const [companyPage, setCompanyPage] = useState(1);
  const [companyPagination, setCompanyPagination] = useState({ page: 1, limit: 25, total: 0, totalPages: 1 });
  const [companiesLoading, setCompaniesLoading] = useState(false);
  const [enrichingCompany, setEnrichingCompany] = useState<string | null>(null);
  const [batchEnrichRunning, setBatchEnrichRunning] = useState(false);

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

  // Dynamic document title based on active tab
  useEffect(() => {
    if (typeof document === 'undefined') return;
    const titles: Record<string, string> = {
      overview: 'Overview & Analytics — ApplyPilot',
      jobs: 'Jobs Explorer (26,500+ Roles) — ApplyPilot',
      companies: 'Company Watchlist — ApplyPilot',
      leads: 'Recruiter Leads & Outreach — ApplyPilot',
      hitl: 'Safety & Verification Queue — ApplyPilot',
      sources: 'ATS Discovery Sources — ApplyPilot',
      applied: 'Applied Jobs & Video Proofs — ApplyPilot',
      radar: 'Execution Flow & Agent Radar — ApplyPilot',
      profile: 'Candidate Profile & AI Matcher — ApplyPilot',
      architecture: 'System Architecture — ApplyPilot',
    };
    if (titles[activeTab]) {
      document.title = titles[activeTab];
    }
  }, [activeTab]);

  const switchTab = (tab: TabType) => {
    setActiveTab(tab);
    const targetPath = tab === 'overview' ? '/' : `/${tab}`;
    router.push(targetPath);
  };

  const openJob = (url: string) => {
    setSelectedJobUrl(url);
    const params = new URLSearchParams(searchParams ? searchParams.toString() : '');
    params.set('job', url);
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const closeJob = () => {
    setSelectedJobUrl(null);
    const params = new URLSearchParams(searchParams ? searchParams.toString() : '');
    params.delete('job');
    const q = params.toString();
    router.push(q ? `${pathname}?${q}` : (pathname || '/'), { scroll: false });
  };

  const openCompany = (companyName: string) => {
    setSelectedCompany(companyName);
    const params = new URLSearchParams(searchParams ? searchParams.toString() : '');
    params.set('company', companyName);
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const closeCompany = () => {
    setSelectedCompany(null);
    const params = new URLSearchParams(searchParams ? searchParams.toString() : '');
    params.delete('company');
    const q = params.toString();
    router.push(q ? `${pathname}?${q}` : (pathname || '/'), { scroll: false });
  };

  const openLead = (leadId: string) => {
    setSelectedLeadId(leadId);
    const params = new URLSearchParams(searchParams ? searchParams.toString() : '');
    params.set('lead', leadId);
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const closeLead = () => {
    setSelectedLeadId(null);
    const params = new URLSearchParams(searchParams ? searchParams.toString() : '');
    params.delete('lead');
    const q = params.toString();
    router.push(q ? `${pathname}?${q}` : (pathname || '/'), { scroll: false });
  };

  const openTicket = (ticketId: number) => {
    setSelectedTicketId(ticketId);
    const params = new URLSearchParams(searchParams ? searchParams.toString() : '');
    params.set('ticket', ticketId.toString());
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const closeTicket = () => {
    setSelectedTicketId(null);
    const params = new URLSearchParams(searchParams ? searchParams.toString() : '');
    params.delete('ticket');
    const q = params.toString();
    router.push(q ? `${pathname}?${q}` : (pathname || '/'), { scroll: false });
  };

  // Sync drawer selections from URL query parameters
  useEffect(() => {
    if (!searchParams) return;
    const jobParam = searchParams.get('job');
    if (jobParam) setSelectedJobUrl(jobParam);
    const companyParam = searchParams.get('company');
    if (companyParam) setSelectedCompany(companyParam);
    const leadParam = searchParams.get('lead');
    if (leadParam) setSelectedLeadId(leadParam);
    const ticketParam = searchParams.get('ticket');
    if (ticketParam) setSelectedTicketId(parseInt(ticketParam, 10));
  }, [searchParams]);

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
        `/api/jobs?page=${page}&limit=${limit}&search=${encodeURIComponent(jobSearch)}&route=${jobRoute}&state=${jobState}&minScore=${jobMinScore}&sort=${jobSort}&workplace=${jobWorkplace}&category=${jobCategory}`
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

  const fetchCompanies = async (
    page = companyPage,
    limit = companyLimit,
    overrides?: {
      search?: string;
      tier?: string;
      cluster?: string;
      sector?: string;
      hasContacts?: string;
      hasJobs?: string;
      ats?: string;
      sort?: string;
    }
  ) => {
    setCompaniesLoading(true);
    try {
      const s = overrides?.search !== undefined ? overrides.search : companySearch;
      const t = overrides?.tier !== undefined ? overrides.tier : companyTier;
      const cl = overrides?.cluster !== undefined ? overrides.cluster : companyCluster;
      const sec = overrides?.sector !== undefined ? overrides.sector : companySector;
      const hc = overrides?.hasContacts !== undefined ? overrides.hasContacts : companyHasContacts;
      const hj = overrides?.hasJobs !== undefined ? overrides.hasJobs : companyHasJobs;
      const ats = overrides?.ats !== undefined ? overrides.ats : companyAts;
      const sort = overrides?.sort !== undefined ? overrides.sort : companySort;

      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('limit', String(limit));
      if (s && s.trim()) params.set('q', s.trim());
      if (t !== 'ALL') params.set('tier', t.toLowerCase());
      if (cl !== 'ALL') params.set('cluster', cl.toLowerCase());
      if (sec !== 'ALL') params.set('sector', sec);
      if (hc === 'YES') params.set('has_contacts', 'true');
      if (hc === 'NO') params.set('has_contacts', 'false');
      if (hj === 'YES') params.set('has_jobs', 'true');
      if (hj === 'NO') params.set('has_jobs', 'false');
      if (ats !== 'ALL') params.set('ats', ats.toLowerCase());
      if (sort) params.set('sort', sort);

      const res = await fetch(`/api/companies?${params.toString()}`);
      const data = await res.json();
      if (data.success) {
        setCompanies(data.companies || []);
        setCompanyPagination(data.pagination || { page: 1, limit, total: 0, totalPages: 1 });
        setCompanyPage(page);
      }
    } catch (err) {
      console.error('Failed to fetch companies', err);
    } finally {
      setCompaniesLoading(false);
    }
  };

  const handleEnrichSingleCompany = async (companyName: string) => {
    if (!companyName) return;
    try {
      setEnrichingCompany(companyName);
      const res = await fetch('/api/companies/enrich', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: companyName, mode: 'single' }),
      });
      const data = await res.json();
      if (data.success) {
        fetchCompanies(companyPage);
      } else {
        alert(data.error || 'Failed to enrich company');
      }
    } catch (err: any) {
      console.error('Failed to enrich company:', err);
      alert('Enrich error: ' + err.message);
    } finally {
      setEnrichingCompany(null);
    }
  };

  const handleStartLooper = async () => {
    if (batchEnrichRunning) return;
    setBatchEnrichRunning(true);
    try {
      const res = await fetch('/api/companies/enrich', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'batch', limit: 30 }),
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message || 'Background company looper started! It will cycle through targets, deduce email patterns, and enrich decision makers.');
        fetchCompanies(companyPage);
      } else {
        alert('Looper status: ' + (data.error || 'Failed to start'));
      }
    } catch (err: any) {
      alert('Error triggering looper: ' + err.message);
    } finally {
      setBatchEnrichRunning(false);
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
    jobSort,
    jobWorkplace,
    jobCategory,
    companySearch,
    companyTier,
    companyCluster,
    companySector,
    companyHasContacts,
    companyHasJobs,
    companyAts,
    companySort,
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
      label: 'Overview',
      icon: LayoutDashboard,
      color: 'text-zinc-700',
      badge: null,
      badgeColor: '',
    },
    {
      id: 'leads',
      label: 'Recruiter Outreach',
      icon: Users,
      color: 'text-emerald-700',
      badge: stats?.totalLeads ? stats.totalLeads.toLocaleString() : null,
      badgeColor: 'bg-emerald-50 text-emerald-800 border-emerald-200/80 font-medium',
    },
    {
      id: 'jobs',
      label: 'Jobs Pipeline',
      icon: Briefcase,
      color: 'text-blue-700',
      badge: stats?.totalJobs ? stats.totalJobs.toLocaleString() : null,
      badgeColor: 'bg-blue-50 text-blue-800 border-blue-200/80 font-medium',
    },
    {
      id: 'companies',
      label: 'Target Companies',
      icon: Building2,
      color: 'text-amber-700',
      badge: stats?.totalCompanies ? stats.totalCompanies.toLocaleString() : null,
      badgeColor: 'bg-amber-50 text-amber-800 border-amber-200/80 font-medium',
    },
    {
      id: 'applied',
      label: 'Applications',
      icon: CheckCircle2,
      color: 'text-emerald-600',
      badge: stats?.appliedCount ? String(stats.appliedCount) : null,
      badgeColor: 'bg-emerald-50 text-emerald-800 border-emerald-200/80 font-semibold',
    },
    {
      id: 'hitl',
      label: 'Review Queue',
      icon: ShieldAlert,
      color: 'text-rose-600',
      badge: stats?.hitlCount ? `${stats.hitlCount} pending` : '0',
      badgeColor: stats?.hitlCount
        ? 'bg-rose-50 text-rose-800 border-rose-200/80'
        : 'bg-zinc-100 text-zinc-600 border-zinc-200',
    },
    {
      id: 'sources',
      label: 'ATS Sources',
      icon: Globe,
      color: 'text-indigo-600',
      badge: 'DIRECT',
      badgeColor: 'bg-indigo-50 text-indigo-800 border-indigo-200/80',
    },
    {
      id: 'profile',
      label: 'Profile & Resume',
      icon: User,
      color: 'text-zinc-700',
    },
    {
      id: 'radar',
      label: 'Execution Flow',
      icon: GitBranch,
      color: 'text-purple-600',
      badge: 'DAG',
      badgeColor: 'bg-purple-50 text-purple-800 border-purple-200/80',
    },
    {
      id: 'architecture',
      label: 'System Status',
      icon: Layers,
      color: 'text-zinc-600',
      badge: null,
      badgeColor: '',
    },
  ];

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3">
        <div className="w-7 h-7 rounded-full border-2 border-zinc-300 border-t-zinc-900 animate-spin" />
        <span className="text-xs font-medium text-zinc-500">Loading your workspace...</span>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    if (pathname && pathname !== '/' && pathname !== '/login') {
      router.replace(`/login?callbackUrl=${encodeURIComponent(pathname)}`);
      return (
        <div className="min-h-screen flex items-center justify-center text-xs text-zinc-400">
          Redirecting to workspace login...
        </div>
      );
    }
    return <LandingPage />;
  }

  return (
    <div className="flex flex-col md:flex-row min-h-screen p-2.5 sm:p-3 md:p-4 lg:p-5 2xl:p-7 gap-3 sm:gap-4 lg:gap-6 w-full max-w-none text-zinc-900">
      {/* ----------------- DESKTOP SIDEBAR ----------------- */}
      <aside
        className={`hidden md:flex flex-col gap-4 lg:gap-6 shrink-0 transition-all duration-300 md:sticky md:top-4 md:h-[calc(100vh-2rem)] ${
          sidebarCollapsed ? 'w-20' : 'w-56 lg:w-64'
        }`}
      >
        <div
          className={`saas-card rounded-2xl flex flex-col justify-between transition-all relative overflow-y-auto shadow-xs h-full ${
            sidebarCollapsed ? 'p-3 items-center gap-4' : 'p-4 lg:p-5 gap-5'
          }`}
        >
          <div className="space-y-5 w-full">
            {/* Logo, Title & Sidebar Collapse */}
            <div className={`flex items-center w-full ${sidebarCollapsed ? 'flex-col gap-2' : 'justify-between gap-3'}`}>
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-zinc-900 text-white shrink-0 flex items-center justify-center font-bold text-sm shadow-xs">
                  A
                </div>
                {!sidebarCollapsed && (
                  <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-base tracking-tight text-zinc-900 truncate">
                        ApplyPilot
                      </span>
                      <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-zinc-100 text-zinc-600 border border-zinc-200">
                        v2.4
                      </span>
                    </div>
                    <span className="text-[11px] text-zinc-400 font-medium">
                      Recruiter Outreach & Pipeline
                    </span>
                  </div>
                )}
              </div>

              <button
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                title={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
                className="saas-card rounded-lg p-1.5 text-zinc-500 hover:text-zinc-900 transition cursor-pointer shrink-0"
              >
                {sidebarCollapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
              </button>
            </div>

            {/* Navigation Items */}
            <nav className="flex flex-col gap-1 w-full">
              {navItems.map((item) => {
                const IconComponent = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => switchTab(item.id as any)}
                    className={`rounded-xl flex items-center gap-2.5 transition-all cursor-pointer ${
                      sidebarCollapsed ? 'p-2.5 justify-center' : 'p-2 sm:px-3 justify-between'
                    } ${
                      isActive
                        ? 'bg-zinc-900 text-white font-medium shadow-xs'
                        : 'text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <IconComponent
                        className={`w-4 h-4 shrink-0 transition-colors ${
                          isActive ? 'text-white' : item.color
                        }`}
                      />
                      {!sidebarCollapsed && <span className="text-xs truncate">{item.label}</span>}
                    </div>

                    {!sidebarCollapsed && item.badge && (
                      <span className={`text-[10px] font-medium px-1.5 py-0.2 rounded-md border ${
                        isActive ? 'bg-zinc-800 text-zinc-200 border-zinc-700' : item.badgeColor
                      }`}>
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
            <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200/80 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium text-zinc-500">Pipeline Status</span>
                <span className="flex items-center gap-1.5 text-emerald-700 font-medium text-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Active
                </span>
              </div>
              <div className="text-[11px] text-zinc-500 flex items-center justify-between">
                <span>ATS Connections</span>
                <span className="font-medium text-zinc-800">Ashby · Lever · Greenhouse</span>
              </div>
              <div className="text-[11px] text-zinc-500 flex items-center justify-between">
                <span>Email Verifier</span>
                <span className="font-medium text-emerald-700">MX Verified</span>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* ----------------- MAIN DASHBOARD CONTENT ----------------- */}
      <main className="flex-1 flex flex-col gap-4 lg:gap-5 min-w-0">
        {/* Top Header Bar */}
        <header className="saas-card rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xs">
          {/* Left: Greeting & Subtitle */}
          <div className="flex items-center gap-3">
            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden saas-card rounded-lg p-2 text-zinc-700 hover:text-zinc-950 transition cursor-pointer"
            >
              <Menu className="w-4 h-4" />
            </button>

            <div className="space-y-0.5">
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-950 flex items-center gap-2">
                <span>{greeting}, Sameer</span>
              </h2>
              <p className="text-xs text-zinc-500">
                Track job openings, verify recruiter mailboxes, and review personalized outreach.
              </p>
            </div>
          </div>

          {/* Right: Search, Live Worker Pill, User Auth & Backdrop Switcher */}
          <div className="flex items-center gap-2.5 sm:gap-3 flex-wrap">
            {/* Search Input Trigger */}
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-50 border border-zinc-200 text-xs text-zinc-400 w-56">
              <Search className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
              <span>Search pipeline...</span>
              <kbd className="ml-auto text-[10px] bg-white border border-zinc-200 px-1 py-0.2 rounded text-zinc-400 font-mono">⌘K</kbd>
            </div>

            {/* Active Worker Pill */}
            <div className="saas-card rounded-lg px-2.5 py-1.5 flex items-center gap-2 text-xs font-medium text-zinc-700 shadow-2xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="hidden sm:inline">Continuous Sync Active</span>
            </div>

            {/* Authenticated User Pill & Sign Out */}
            {session?.user && (
              <div className="flex items-center gap-2 saas-card rounded-lg pl-2 pr-2.5 py-1 text-xs font-medium text-zinc-800 shadow-2xs">
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
                  title="Sign out of workspace"
                  className="ml-1 text-zinc-400 hover:text-rose-600 transition cursor-pointer p-0.5 rounded-md hover:bg-rose-50"
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

        {/* ----------------- TAB 1: OVERVIEW ----------------- */}
        {activeTab === 'overview' && (
          <div className="space-y-5 lg:space-y-6 animate-in fade-in duration-200">
            {/* Top Metric Tiles */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-5">
              <div className="saas-card rounded-xl p-5 hover:border-zinc-300 transition-all">
                <div className="flex items-center justify-between text-zinc-500 mb-2">
                  <span className="text-xs font-medium text-zinc-500">Active Postings</span>
                  <div className="p-2 rounded-lg bg-zinc-100 text-zinc-700">
                    <Briefcase className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">
                  {stats?.totalJobs ? stats.totalJobs.toLocaleString() : '2,554+'}
                </div>
                <div className="text-xs text-zinc-500 font-medium mt-1">
                  Direct career page roles
                </div>
              </div>

              <div className="saas-card rounded-xl p-5 hover:border-zinc-300 transition-all">
                <div className="flex items-center justify-between text-zinc-500 mb-2">
                  <span className="text-xs font-medium text-zinc-500">Target Companies</span>
                  <div className="p-2 rounded-lg bg-zinc-100 text-zinc-700">
                    <Building2 className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">
                  {stats?.totalCompanies ? stats.totalCompanies.toLocaleString() : '136'}
                </div>
                <div className="text-xs text-zinc-500 font-medium mt-1 flex items-center gap-1">
                  <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                  <span>{stats?.vipCompanies || 24} High-priority targets</span>
                </div>
              </div>

              <div className="saas-card rounded-xl p-5 hover:border-zinc-300 transition-all">
                <div className="flex items-center justify-between text-zinc-500 mb-2">
                  <span className="text-xs font-medium text-zinc-500">Recruiter Contacts</span>
                  <div className="p-2 rounded-lg bg-zinc-100 text-zinc-700">
                    <Users className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">
                  {stats?.totalLeads ? stats.totalLeads.toLocaleString() : '230'}
                </div>
                <div className="text-xs text-emerald-700 font-medium mt-1">
                  Verified mailboxes
                </div>
              </div>

              <div className="saas-card rounded-xl p-5 hover:border-zinc-300 transition-all">
                <div className="flex items-center justify-between text-zinc-500 mb-2">
                  <span className="text-xs font-medium text-zinc-500">Outreach Queue</span>
                  <div className="p-2 rounded-lg bg-zinc-100 text-zinc-700">
                    <Zap className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">
                  {stats?.routes?.dualAttack || 42}
                </div>
                <div className="text-xs text-zinc-500 font-medium mt-1">
                  Drafts ready for review
                </div>
              </div>
            </div>

            {/* Strategy Breakdown & Actions Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              {/* Route Breakdown Card */}
              <div className="saas-card rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                    Outreach Distribution
                  </h3>
                  <Zap className="w-4 h-4 text-zinc-400" />
                </div>

                <div className="space-y-3">
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-zinc-800">
                      <span>Paired Outreach (Founder + HR Team)</span>
                      <span className="font-mono">{stats?.routes?.dualAttack || 42}</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-zinc-100 overflow-hidden">
                      <div className="h-full bg-zinc-900 rounded-full" style={{ width: '45%' }} />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-zinc-800">
                      <span>Direct Portal Applications</span>
                      <span className="font-mono">{stats?.routes?.portalOnly || 1800}</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-zinc-100 overflow-hidden">
                      <div className="h-full bg-zinc-400 rounded-full" style={{ width: '70%' }} />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-zinc-800">
                      <span>Direct Founder Email</span>
                      <span className="font-mono">{stats?.routes?.emailOnly || 188}</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-zinc-100 overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: '25%' }} />
                    </div>
                  </div>
                </div>
              </div>

              {/* Direct ATS Harvest Providers */}
              <div className="saas-card rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                    Direct ATS Sources
                  </h3>
                  <Compass className="w-4 h-4 text-zinc-400" />
                </div>

                <div className="grid grid-cols-2 gap-2.5 text-xs">
                  {(stats?.topAts || [
                    { provider: 'greenhouse', count: 1240 },
                    { provider: 'lever', count: 820 },
                    { provider: 'ashby', count: 340 },
                    { provider: 'workday', count: 154 },
                  ]).map((ats, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                      <span className="text-[11px] font-medium text-zinc-500 block capitalize">
                        {ats.provider}
                      </span>
                      <span className="text-base font-bold text-zinc-900 font-mono">{ats.count.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick Actions Card */}
              <div className="saas-card rounded-xl p-5 space-y-4 flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1.5">
                    Quick Actions
                  </h3>
                  <p className="text-xs text-zinc-500 leading-relaxed">
                    Track a target role, add a company account, or review pending recruiter drafts.
                  </p>
                </div>

                <div className="flex flex-col gap-2 pt-2">
                  <button
                    onClick={() => setAddJobOpen(true)}
                    className="saas-card w-full py-2 px-3 rounded-lg flex items-center justify-between text-xs font-medium text-zinc-800 hover:bg-zinc-50 transition cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <Briefcase className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Add Target Job</span>
                    </div>
                    <Plus className="w-3.5 h-3.5 text-zinc-400" />
                  </button>

                  <button
                    onClick={() => setAddCompanyOpen(true)}
                    className="saas-card w-full py-2 px-3 rounded-lg flex items-center justify-between text-xs font-medium text-zinc-800 hover:bg-zinc-50 transition cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <Building2 className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Add Target Company</span>
                    </div>
                    <Plus className="w-3.5 h-3.5 text-zinc-400" />
                  </button>

                  <button
                    onClick={() => switchTab('leads')}
                    className="w-full py-2 px-3 rounded-lg bg-zinc-900 text-white flex items-center justify-between text-xs font-medium hover:bg-zinc-800 transition cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <Users className="w-3.5 h-3.5 text-zinc-300" />
                      <span>Review Recruiter Drafts</span>
                    </div>
                    <ArrowUpRight className="w-3.5 h-3.5 text-zinc-400" />
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
            {/* Quick-Ranking Presets Bar */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
              <span className="text-zinc-600 font-semibold text-[11px] uppercase tracking-wider shrink-0 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-cyan-700" />
                Quick Rank:
              </span>
              <button
                onClick={() => {
                  setJobSort('ranked');
                  setJobMinScore(7);
                  setJobWorkplace('ALL');
                  setJobCategory('ALL');
                }}
                className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer shrink-0 flex items-center gap-1.5 ${
                  jobSort === 'ranked' && jobMinScore >= 7
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'liquid-pill text-zinc-700 hover:text-zinc-950'
                }`}
              >
                <Target className="w-3.5 h-3.5" />
                <span>🎯 Top Matches (Score 7+)</span>
              </button>
              <button
                onClick={() => {
                  setJobWorkplace(jobWorkplace === 'REMOTE' ? 'ALL' : 'REMOTE');
                }}
                className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer shrink-0 flex items-center gap-1.5 ${
                  jobWorkplace === 'REMOTE'
                    ? 'bg-cyan-600 text-white shadow-xs'
                    : 'liquid-pill text-zinc-700 hover:text-zinc-950'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                <span>🌐 Remote Only</span>
              </button>
              <button
                onClick={() => {
                  setJobCategory(jobCategory === 'AI_ML' ? 'ALL' : 'AI_ML');
                }}
                className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer shrink-0 flex items-center gap-1.5 ${
                  jobCategory === 'AI_ML'
                    ? 'bg-purple-600 text-white shadow-xs'
                    : 'liquid-pill text-zinc-700 hover:text-zinc-950'
                }`}
              >
                <Cpu className="w-3.5 h-3.5" />
                <span>🤖 AI & Agents</span>
              </button>
              <button
                onClick={() => {
                  setJobCategory(jobCategory === 'FULLSTACK' ? 'ALL' : 'FULLSTACK');
                }}
                className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer shrink-0 flex items-center gap-1.5 ${
                  jobCategory === 'FULLSTACK'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'liquid-pill text-zinc-700 hover:text-zinc-950'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>⚡ Fullstack & Python</span>
              </button>
              <button
                onClick={() => {
                  setJobSort('newest');
                  setJobMinScore(0);
                }}
                className={`px-3 py-1.5 rounded-xl font-semibold transition-all cursor-pointer shrink-0 flex items-center gap-1.5 ${
                  jobSort === 'newest'
                    ? 'bg-zinc-800 text-white shadow-xs'
                    : 'liquid-pill text-zinc-700 hover:text-zinc-950'
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                <span>⏱️ Newest Discoveries</span>
              </button>
            </div>

            {/* Filter & Search Bar */}
            <div className="liquid-glass rounded-3xl p-4 sm:p-5 border border-white/90 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2 w-full md:w-auto flex-1 flex-wrap">
                <div className="relative flex-1 min-w-[220px] max-w-md">
                  <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={jobSearch}
                    onChange={(e) => setJobSearch(e.target.value)}
                    placeholder="Search by role title, company, or tech stack..."
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-2xl pl-9 pr-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                  {jobSearch && (
                    <button
                      onClick={() => setJobSearch('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Sort / Ranking Dropdown */}
                <select
                  value={jobSort}
                  onChange={(e) => setJobSort(e.target.value)}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs font-semibold text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs cursor-pointer"
                >
                  <option value="ranked">🎯 Sort: Best Match (Fit Score)</option>
                  <option value="newest">⚡ Sort: Newest Discovered</option>
                  <option value="company">🏢 Sort: Company Name (A-Z)</option>
                </select>

                {/* Workplace Filter */}
                <select
                  value={jobWorkplace}
                  onChange={(e) => setJobWorkplace(e.target.value)}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs cursor-pointer"
                >
                  <option value="ALL">All Workplaces</option>
                  <option value="REMOTE">🌐 Remote Only</option>
                  <option value="HYBRID">🏢 Hybrid</option>
                  <option value="ONSITE">📍 Onsite</option>
                </select>

                {/* Category Filter */}
                <select
                  value={jobCategory}
                  onChange={(e) => setJobCategory(e.target.value)}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs cursor-pointer"
                >
                  <option value="ALL">All Role Types</option>
                  <option value="AI_ML">🤖 AI & ML Engineer</option>
                  <option value="FULLSTACK">⚡ Fullstack Developer</option>
                  <option value="BACKEND">⚙️ Backend Engineer</option>
                  <option value="FRONTEND">🎨 Frontend Engineer</option>
                </select>

                {/* Route Filter */}
                <select
                  value={jobRoute}
                  onChange={(e) => setJobRoute(e.target.value)}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs cursor-pointer"
                >
                  <option value="ALL">All Routes</option>
                  <option value="DUAL_ATTACK">Dual Attack</option>
                  <option value="PORTAL_ONLY">Portal Only</option>
                  <option value="EMAIL_ONLY">Email Only</option>
                </select>

                {/* Min Score Filter */}
                <select
                  value={jobMinScore}
                  onChange={(e) => setJobMinScore(Number(e.target.value))}
                  className="bg-white/80 border border-zinc-200/90 rounded-2xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs cursor-pointer"
                >
                  <option value="0">All Scores (0+)</option>
                  <option value="5">Score 5+ (Medium)</option>
                  <option value="8">Score 8+ (Top Match)</option>
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
                <div className="flex items-center gap-2">
                  <span>Showing {jobs.length} of {jobPagination.total.toLocaleString()} listings</span>
                  {jobSort === 'ranked' && (
                    <span className="px-2 py-0.2 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                      🎯 Ranked by Candidate Fit
                    </span>
                  )}
                </div>
                <span>Page {jobPage} of {jobPagination.totalPages}</span>
              </div>

              {jobsLoading ? (
                <div className="py-20 text-center text-xs text-zinc-400">Loading open listings...</div>
              ) : jobs.length === 0 ? (
                <div className="py-20 text-center text-xs text-zinc-500">No jobs matched your filter criteria.</div>
              ) : (
                <div className="space-y-2.5">
                  {jobs.map((j) => {
                    const meta = j.metadata;
                    const resumeMatch = meta?.resume_match;
                    const matchPct = resumeMatch?.match_percentage ?? (j.fit_score != null ? Math.round(j.fit_score * 10) : null);
                    const workplace = meta?.workplace_type || (j.location?.toLowerCase().includes('remote') ? 'Remote' : (j.location?.toLowerCase().includes('hybrid') ? 'Hybrid' : 'Onsite'));
                    const skills: string[] = resumeMatch?.matched_skills || meta?.tech_stack || [];
                    const minExp = meta?.min_experience_years;
                    const maxExp = meta?.max_experience_years;

                    return (
                      <div
                        key={j.url}
                        onClick={() => openJob(j.url)}
                        className="liquid-row rounded-2xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 cursor-pointer group hover:border-purple-300/60 transition-all duration-150"
                      >
                        <div className="space-y-1.5 min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-sm text-zinc-900 group-hover:text-cyan-700 transition">
                              {j.title}
                            </span>

                            {/* Match Score Badge */}
                            {matchPct != null ? (
                              <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border flex items-center gap-1 ${
                                matchPct >= 80
                                  ? 'bg-emerald-50 text-emerald-800 border-emerald-300 shadow-2xs'
                                  : matchPct >= 50
                                  ? 'bg-amber-50 text-amber-800 border-amber-300 shadow-2xs'
                                  : 'bg-zinc-100 text-zinc-600 border-zinc-200'
                              }`}>
                                <Target className="w-3 h-3 text-emerald-600" />
                                <span>{matchPct}% Match</span>
                              </span>
                            ) : j.fit_score != null ? (
                              <span className={`px-2 py-0.2 rounded-full text-[10px] font-bold border ${getScoreColor(j.fit_score)}`}>
                                {j.fit_score}/10
                              </span>
                            ) : null}

                            {/* Workplace Badge */}
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                              workplace === 'Remote'
                                ? 'bg-cyan-50 text-cyan-800 border-cyan-200'
                                : workplace === 'Hybrid'
                                ? 'bg-amber-50 text-amber-800 border-amber-200'
                                : 'bg-zinc-100 text-zinc-600 border-zinc-200'
                            }`}>
                              {workplace === 'Remote' ? '🌐 Remote' : workplace === 'Hybrid' ? '🏢 Hybrid' : '📍 Onsite'}
                            </span>

                            {/* Experience Badge */}
                            {(minExp != null || maxExp != null) && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-blue-50 text-blue-800 border border-blue-200">
                                {minExp ? `${minExp}${maxExp ? `-${maxExp}` : '+'}y exp` : `<${maxExp}y exp`}
                              </span>
                            )}

                            {/* Route Badge */}
                            <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-zinc-100 text-zinc-600 border border-zinc-200">
                              {j.execution_route || 'PORTAL_ONLY'}
                            </span>

                            {/* ATS Provider Badge */}
                            <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-zinc-100 text-zinc-500 border border-zinc-200 capitalize">
                              {j.ats_provider || 'Direct'}
                            </span>
                          </div>

                          <div className="text-xs text-zinc-500 flex items-center gap-3 flex-wrap">
                            <span className="font-semibold text-zinc-800 flex items-center gap-1">
                              <Building2 className="w-3.5 h-3.5 text-cyan-600" />
                              {j.company}
                            </span>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                              {j.location || 'Remote'}
                            </span>
                            {j.salary_raw && (
                              <>
                                <span>•</span>
                                <span className="text-emerald-700 font-medium">{j.salary_raw}</span>
                              </>
                            )}
                          </div>

                          {/* Top Matched Skills Chips */}
                          {skills.length > 0 && (
                            <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                              {skills.slice(0, 4).map((tech) => (
                                <span
                                  key={tech}
                                  className="text-[10px] px-2 py-0.2 rounded-md font-medium bg-white/90 text-zinc-700 border border-zinc-200/80 shadow-2xs flex items-center gap-1"
                                >
                                  <Check className="w-2.5 h-2.5 text-emerald-600 stroke-[3]" />
                                  <span>{tech}</span>
                                </span>
                              ))}
                              {skills.length > 4 && (
                                <span className="text-[10px] text-zinc-400 font-medium">
                                  +{skills.length - 4} more
                                </span>
                              )}
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
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
                    );
                  })}
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
            {/* Filter Bar & Header */}
            <div className="liquid-glass rounded-3xl p-4 sm:p-5 border border-white/90 shadow-xs space-y-3.5">
              {/* Row 1: Search, Priority Tabs, Looper CTA, Add Company */}
              <div className="flex flex-col lg:flex-row items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 w-full lg:w-auto flex-1 flex-wrap">
                  <div className="relative flex-1 min-w-[220px] max-w-md">
                    <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={companySearch}
                      onChange={(e) => setCompanySearch(e.target.value)}
                      placeholder="Search 5,800+ target companies, Pune corridor, stack..."
                      className="w-full bg-white/90 border border-zinc-200/90 rounded-2xl pl-9 pr-8 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-amber-200 focus:border-amber-400 shadow-2xs"
                    />
                    {companySearch && (
                      <button
                        onClick={() => setCompanySearch('')}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>

                  {/* Priority Tier Tabs */}
                  <div className="flex items-center gap-1.5 text-xs bg-zinc-100/80 p-1 rounded-2xl border border-zinc-200/60 overflow-x-auto">
                    {[
                      { id: 'ALL', label: 'All Companies' },
                      { id: 'VIP', label: 'VIP (Tier 1)', icon: Star, vip: true },
                      { id: 'P2', label: 'Tier 2 Growth' },
                      { id: 'P3', label: 'Tier 3' },
                      { id: 'GTM_EXCLUDED', label: 'Staffing / Agency' },
                    ].map((tab) => {
                      const isActive = companyTier === tab.id;
                      const Icon = tab.icon;
                      return (
                        <button
                          key={tab.id}
                          type="button"
                          onClick={() => {
                            setCompanyTier(tab.id);
                            setCompanyPage(1);
                          }}
                          className={`px-3 py-1.5 rounded-xl font-medium transition cursor-pointer flex items-center gap-1.5 text-xs whitespace-nowrap ${
                            isActive
                              ? tab.vip
                                ? 'bg-amber-600 text-white shadow-xs font-semibold'
                                : 'bg-zinc-900 text-white shadow-xs font-semibold'
                              : 'text-zinc-600 hover:text-zinc-900 hover:bg-white/60'
                          }`}
                        >
                          {Icon && (
                            <Icon
                              className={`w-3.5 h-3.5 ${
                                isActive ? 'fill-white text-white' : 'fill-amber-500 text-amber-600'
                              }`}
                            />
                          )}
                          <span>{tab.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Right controls: View Toggle, Run Looper, Add Company */}
                <div className="flex items-center gap-2 w-full lg:w-auto justify-end flex-wrap">
                  {/* Table vs Cards switcher */}
                  <div className="flex items-center bg-zinc-100/90 rounded-2xl p-0.5 border border-zinc-200/70 text-xs">
                    <button
                      onClick={() => setCompanyViewMode('table')}
                      className={`px-2.5 py-1.5 rounded-xl font-medium transition flex items-center gap-1 cursor-pointer ${
                        companyViewMode === 'table' ? 'bg-white text-zinc-900 shadow-2xs font-semibold' : 'text-zinc-500 hover:text-zinc-900'
                      }`}
                      title="Table View (Attio style)"
                    >
                      <Layers className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Table</span>
                    </button>
                    <button
                      onClick={() => setCompanyViewMode('cards')}
                      className={`px-2.5 py-1.5 rounded-xl font-medium transition flex items-center gap-1 cursor-pointer ${
                        companyViewMode === 'cards' ? 'bg-white text-zinc-900 shadow-2xs font-semibold' : 'text-zinc-500 hover:text-zinc-900'
                      }`}
                      title="Cards Grid"
                    >
                      <LayoutDashboard className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Cards</span>
                    </button>
                  </div>

                  {/* Looper Trigger Button */}
                  <button
                    onClick={handleStartLooper}
                    disabled={batchEnrichRunning}
                    className="liquid-pill px-3.5 py-2 rounded-2xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs bg-amber-500/10 text-amber-900 border border-amber-300/80 hover:bg-amber-500/20 transition disabled:opacity-50"
                    title="Run background OSINT looper to deduce email patterns and enrich decision makers"
                  >
                    {batchEnrichRunning ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-700" />
                    ) : (
                      <Play className="w-3.5 h-3.5 fill-amber-700 text-amber-700" />
                    )}
                    <span>{batchEnrichRunning ? 'Looping...' : 'Run Looper'}</span>
                  </button>

                  <button
                    onClick={() => setAddCompanyOpen(true)}
                    className="liquid-pill-dark px-3.5 py-2 rounded-2xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <Plus className="w-3.5 h-3.5 text-amber-400" />
                    <span>Add Company</span>
                  </button>
                </div>
              </div>

              {/* Row 2: Secondary Dropdown Filters */}
              <div className="flex items-center gap-2 pt-2 border-t border-zinc-200/50 flex-wrap text-xs">
                {/* Pune Cluster / Corridor Filter */}
                <div className="flex items-center gap-1 bg-white/80 border border-zinc-200/90 rounded-2xl px-2.5 py-1.5 shadow-2xs">
                  <MapPin className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <select
                    value={companyCluster}
                    onChange={(e) => {
                      setCompanyCluster(e.target.value);
                      setCompanyPage(1);
                    }}
                    className="bg-transparent text-xs text-zinc-800 font-medium focus:outline-none cursor-pointer"
                  >
                    <option value="ALL">All Tech Corridors</option>
                    <option value="pune">All Pune Tech Hubs</option>
                    <option value="magarpatta">Magarpatta / Hadapsar (Cybercity)</option>
                    <option value="baner">Baner / Balewadi / Aundh (West)</option>
                    <option value="hinjawadi">Hinjawadi RGIP (Phase 1-3)</option>
                    <option value="kharadi">Kharadi (EON / WTC)</option>
                    <option value="yerawada">Yerawada (Commerzone)</option>
                    <option value="viman">Viman Nagar / Kalyani</option>
                    <option value="bengaluru">Bengaluru Tech Hub</option>
                    <option value="remote">Remote / Distributed</option>
                    <option value="us">US / Global HQ</option>
                  </select>
                </div>

                {/* Has Contacts Filter */}
                <div className="flex items-center gap-1 bg-white/80 border border-zinc-200/90 rounded-2xl px-2.5 py-1.5 shadow-2xs">
                  <Users className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <select
                    value={companyHasContacts}
                    onChange={(e) => {
                      setCompanyHasContacts(e.target.value);
                      setCompanyPage(1);
                    }}
                    className="bg-transparent text-xs text-zinc-800 font-medium focus:outline-none cursor-pointer"
                  >
                    <option value="ALL">All Contacts Status</option>
                    <option value="YES">Has Decision Makers</option>
                    <option value="NO">Needs People Discovery</option>
                  </select>
                </div>

                {/* Has Open Jobs Filter */}
                <div className="flex items-center gap-1 bg-white/80 border border-zinc-200/90 rounded-2xl px-2.5 py-1.5 shadow-2xs">
                  <Briefcase className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <select
                    value={companyHasJobs}
                    onChange={(e) => {
                      setCompanyHasJobs(e.target.value);
                      setCompanyPage(1);
                    }}
                    className="bg-transparent text-xs text-zinc-800 font-medium focus:outline-none cursor-pointer"
                  >
                    <option value="ALL">All Requisitions</option>
                    <option value="YES">Has Active Jobs</option>
                    <option value="NO">No Listed Roles</option>
                  </select>
                </div>

                {/* ATS Filter */}
                <div className="flex items-center gap-1 bg-white/80 border border-zinc-200/90 rounded-2xl px-2.5 py-1.5 shadow-2xs">
                  <Globe className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <select
                    value={companyAts}
                    onChange={(e) => {
                      setCompanyAts(e.target.value);
                      setCompanyPage(1);
                    }}
                    className="bg-transparent text-xs text-zinc-800 font-medium focus:outline-none cursor-pointer"
                  >
                    <option value="ALL">All ATS Engines</option>
                    <option value="greenhouse">Greenhouse</option>
                    <option value="lever">Lever</option>
                    <option value="ashby">Ashby</option>
                    <option value="workday">Workday</option>
                    <option value="custom">Custom / Direct</option>
                  </select>
                </div>

                {/* Sort Filter */}
                <div className="flex items-center gap-1 bg-white/80 border border-zinc-200/90 rounded-2xl px-2.5 py-1.5 shadow-2xs ml-auto">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <select
                    value={companySort}
                    onChange={(e) => {
                      setCompanySort(e.target.value);
                      setCompanyPage(1);
                    }}
                    className="bg-transparent text-xs text-zinc-800 font-medium focus:outline-none cursor-pointer"
                  >
                    <option value="priority">Sort: Priority & Intent</option>
                    <option value="jobs_count">Sort: Most Open Jobs</option>
                    <option value="leads_count">Sort: Most Contacts</option>
                    <option value="name">Sort: Company Name (A-Z)</option>
                    <option value="created_at">Sort: Recently Checked</option>
                  </select>
                </div>

                {/* Clear Filters Button */}
                {(companySearch ||
                  companyTier !== 'ALL' ||
                  companyCluster !== 'ALL' ||
                  companyHasContacts !== 'ALL' ||
                  companyHasJobs !== 'ALL' ||
                  companyAts !== 'ALL' ||
                  companySort !== 'priority') && (
                  <button
                    onClick={() => {
                      setCompanySearch('');
                      setCompanyTier('ALL');
                      setCompanyCluster('ALL');
                      setCompanyHasContacts('ALL');
                      setCompanyHasJobs('ALL');
                      setCompanyAts('ALL');
                      setCompanySort('priority');
                      setCompanyPage(1);
                    }}
                    className="px-2.5 py-1.5 rounded-2xl text-[11px] font-medium text-amber-700 hover:text-amber-900 bg-amber-50 hover:bg-amber-100 border border-amber-200 transition cursor-pointer flex items-center gap-1"
                  >
                    <X className="w-3 h-3" />
                    <span>Reset Filters</span>
                  </button>
                )}
              </div>
            </div>

            {/* Companies Data View */}
            <div className="liquid-glass rounded-3xl p-4 sm:p-5 border border-white/90 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60 text-xs text-zinc-500 font-semibold px-2">
                <span>Showing {companies.length} of {companyPagination.total.toLocaleString()} companies</span>
                <span>Page {companyPage} of {companyPagination.totalPages}</span>
              </div>

              {companiesLoading ? (
                <div className="py-24 text-center text-xs text-zinc-400 flex flex-col items-center justify-center gap-2">
                  <RefreshCw className="w-6 h-6 animate-spin text-amber-600" />
                  <span>Loading company intelligence...</span>
                </div>
              ) : companies.length === 0 ? (
                <div className="py-20 text-center text-xs text-zinc-500">
                  <Building2 className="w-8 h-8 text-zinc-300 mx-auto mb-2" />
                  <span>No target companies matching your criteria.</span>
                </div>
              ) : companyViewMode === 'table' ? (
                /* ----------------- HIGH-CRAFT TABLE VIEW ----------------- */
                <div className="overflow-x-auto rounded-2xl border border-zinc-200/80 bg-white/70 shadow-2xs backdrop-blur-sm">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-zinc-200/80 bg-zinc-50/70 text-[11px] font-bold text-zinc-600 uppercase tracking-wider">
                        <th className="py-3.5 px-4 min-w-[220px]">Company & Domain</th>
                        <th className="py-3.5 px-3 min-w-[150px]">Priority & Pattern</th>
                        <th className="py-3.5 px-4 min-w-[260px]">Decision Makers & Team</th>
                        <th className="py-3.5 px-3 min-w-[160px]">Tech Corridor</th>
                        <th className="py-3.5 px-3 min-w-[150px]">Tech Stack</th>
                        <th className="py-3.5 px-3 text-center min-w-[100px]">Roles</th>
                        <th className="py-3.5 px-4 text-right min-w-[140px]">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-200/60 text-xs">
                      {companies.map((c) => {
                        const domain = c.official_domain || `${c.company_name.toLowerCase().replace(/[^a-z0-9]/g, '')}.com`;
                        const faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
                        const openRoles = c.open_roles_count || 0;
                        const initial = (c.company_name || 'C').charAt(0).toUpperCase();
                        const persons = c.persons || [];
                        const isEnriching = enrichingCompany === c.company_name;

                        // Pune cluster badge styling
                        const cl = (c.pune_cluster || '').toLowerCase();
                        let clusterLabel = 'Global / Other';
                        let clusterClass = 'bg-zinc-100 text-zinc-600 border-zinc-200';
                        if (cl === 'magarpatta') {
                          clusterLabel = 'Magarpatta Cybercity';
                          clusterClass = 'bg-emerald-50 text-emerald-800 border-emerald-200';
                        } else if (cl === 'hinjawadi') {
                          clusterLabel = 'Hinjawadi RGIP';
                          clusterClass = 'bg-indigo-50 text-indigo-800 border-indigo-200';
                        } else if (cl === 'baner') {
                          clusterLabel = 'Baner Tech Belt';
                          clusterClass = 'bg-purple-50 text-purple-800 border-purple-200';
                        } else if (cl === 'kharadi') {
                          clusterLabel = 'Kharadi EON / WTC';
                          clusterClass = 'bg-cyan-50 text-cyan-800 border-cyan-200';
                        } else if (cl === 'yerawada') {
                          clusterLabel = 'Yerawada Tech Zone';
                          clusterClass = 'bg-blue-50 text-blue-800 border-blue-200';
                        } else if (cl === 'viman') {
                          clusterLabel = 'Viman Nagar / Kalyani';
                          clusterClass = 'bg-sky-50 text-sky-800 border-sky-200';
                        } else if (cl === 'pune' || cl === 'all_pune') {
                          clusterLabel = 'Pune Corridor';
                          clusterClass = 'bg-amber-50 text-amber-800 border-amber-200';
                        } else if (cl === 'bengaluru' || cl === 'bangalore') {
                          clusterLabel = 'Bengaluru Tech Hub';
                          clusterClass = 'bg-violet-50 text-violet-800 border-violet-200';
                        } else if (cl === 'remote') {
                          clusterLabel = 'Remote / Distributed';
                          clusterClass = 'bg-teal-50 text-teal-800 border-teal-200';
                        } else if (cl === 'us') {
                          clusterLabel = 'US / Global HQ';
                          clusterClass = 'bg-rose-50 text-rose-800 border-rose-200';
                        }

                        return (
                          <tr
                            key={c.company_name}
                            className="hover:bg-amber-50/30 transition-colors group"
                          >
                            {/* Column 1: Company & Domain */}
                            <td className="py-3 px-4 align-top">
                              <div className="flex items-start gap-3">
                                <div className="w-9 h-9 rounded-xl bg-white p-1 border border-zinc-200/90 shadow-2xs flex items-center justify-center shrink-0 overflow-hidden group-hover:border-amber-300 transition-colors">
                                  <img
                                    src={faviconUrl}
                                    alt={c.company_name}
                                    className="w-full h-full object-contain rounded-lg"
                                    onError={(e) => {
                                      const target = e.currentTarget;
                                      target.style.display = 'none';
                                      if (target.parentElement) {
                                        target.parentElement.innerHTML = `<span class="text-sm font-black text-amber-700">${initial}</span>`;
                                      }
                                    }}
                                  />
                                </div>
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center gap-1.5">
                                    <button
                                      type="button"
                                      onClick={() => openCompany(c.company_name)}
                                      className="font-bold text-zinc-950 hover:text-amber-700 text-left truncate cursor-pointer transition-colors"
                                      title={c.company_name}
                                    >
                                      {c.company_name}
                                    </button>
                                  </div>

                                  <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                                    <a
                                      href={
                                        c.official_domain
                                          ? `https://${c.official_domain}`
                                          : c.careers_page_url || '#'
                                      }
                                      target="_blank"
                                      rel="noreferrer"
                                      onClick={(e) => e.stopPropagation()}
                                      className="text-[11px] text-zinc-500 hover:text-amber-600 font-mono flex items-center gap-0.5 truncate"
                                      title="Open website"
                                    >
                                      <span>{c.official_domain || 'careers'}</span>
                                      <ExternalLink className="w-2.5 h-2.5 text-zinc-400" />
                                    </a>

                                    {c.sector && (
                                      <span className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-zinc-100 text-zinc-600 border border-zinc-200">
                                        {c.sector}
                                      </span>
                                    )}
                                  </div>

                                  {/* 1st Degree Referral Badge */}
                                  {c.referral_available === 1 && (
                                    <div className="mt-1">
                                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-300">
                                        <UserCheck className="w-3 h-3 text-emerald-600 shrink-0" />
                                        <span>Referral: {c.referrer_name || '1st Degree'}</span>
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </td>

                            {/* Column 2: Priority & Pattern */}
                            <td className="py-3 px-3 align-top">
                              <div className="space-y-1">
                                {c.is_vip === 1 || c.priority_tier === 1 ? (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-100 text-amber-900 border border-amber-300 shadow-2xs">
                                    <Star className="w-3 h-3 fill-amber-500 text-amber-600" />
                                    VIP (Tier 1)
                                  </span>
                                ) : c.priority_tier === 2 ? (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                                    Tier 2 Growth
                                  </span>
                                ) : c.stage === 'gtm_excluded' ? (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-rose-50 text-rose-700 border border-rose-200">
                                    Agency / Staffing
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-zinc-100 text-zinc-600 border border-zinc-200">
                                    Tier 3
                                  </span>
                                )}

                                {c.detected_email_pattern && (
                                  <div
                                    className="text-[10px] text-zinc-600 font-mono flex items-center gap-1"
                                    title={`Email Pattern: ${c.detected_email_pattern}`}
                                  >
                                    <Mail className="w-2.5 h-2.5 text-zinc-400 shrink-0" />
                                    <span className="truncate max-w-[130px]">
                                      {c.detected_email_pattern}
                                    </span>
                                  </div>
                                )}
                              </div>
                            </td>

                            {/* Column 3: Decision Makers & Persons */}
                            <td className="py-3 px-4 align-top">
                              {persons.length > 0 ? (
                                <div className="space-y-1.5">
                                  <div className="flex items-center gap-1.5 text-[11px] font-semibold text-zinc-700">
                                    <Users className="w-3 h-3 text-zinc-400" />
                                    <span>
                                      {c.leads_count || persons.length}{' '}
                                      {(c.leads_count || persons.length) === 1 ? 'contact' : 'contacts'}
                                    </span>
                                  </div>
                                  <div className="flex flex-col gap-1">
                                    {persons.slice(0, 2).map((p: any, idx: number) => (
                                      <div
                                        key={idx}
                                        onClick={() => openCompany(c.company_name)}
                                        className="flex items-center justify-between gap-1.5 bg-white/90 border border-zinc-200/80 rounded-xl px-2 py-1 text-[11px] shadow-2xs hover:border-amber-300 cursor-pointer transition-colors"
                                      >
                                        <div className="min-w-0 flex-1 truncate">
                                          <span className="font-bold text-zinc-900 truncate">
                                            {p.name}
                                          </span>
                                          <span className="text-[10px] text-zinc-500 block truncate">
                                            {p.title || 'Decision Maker'}
                                          </span>
                                        </div>
                                        <div className="flex items-center gap-1 shrink-0">
                                          {p.email ? (
                                            <span
                                              className="p-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200"
                                              title={`Email verified: ${p.email}`}
                                            >
                                              <Mail className="w-2.5 h-2.5" />
                                            </span>
                                          ) : (
                                            <span
                                              className="p-1 rounded-full bg-zinc-100 text-zinc-400"
                                              title="Email pending discovery"
                                            >
                                              <Mail className="w-2.5 h-2.5" />
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    ))}

                                    {(c.leads_count || persons.length) > 2 && (
                                      <button
                                        type="button"
                                        onClick={() => openCompany(c.company_name)}
                                        className="text-[10px] text-amber-700 hover:text-amber-900 font-semibold text-left pl-1 cursor-pointer"
                                      >
                                        +{(c.leads_count || persons.length) - 2} more decision makers →
                                      </button>
                                    )}
                                  </div>
                                </div>
                              ) : (
                                <div className="space-y-1">
                                  <span className="text-[11px] text-zinc-400 italic block">
                                    No contacts indexed
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => handleEnrichSingleCompany(c.company_name)}
                                    disabled={isEnriching}
                                    className="text-[10px] font-semibold text-amber-700 hover:text-amber-900 flex items-center gap-1 cursor-pointer disabled:opacity-50"
                                  >
                                    {isEnriching ? (
                                      <RefreshCw className="w-2.5 h-2.5 animate-spin" />
                                    ) : (
                                      <Sparkles className="w-2.5 h-2.5" />
                                    )}
                                    <span>{isEnriching ? 'Discovering...' : '+ Discover People'}</span>
                                  </button>
                                </div>
                              )}
                            </td>

                            {/* Column 4: Tech Corridor / Location */}
                            <td className="py-3 px-3 align-top">
                              <div className="space-y-1">
                                <span
                                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${clusterClass}`}
                                >
                                  <MapPin className="w-2.5 h-2.5 shrink-0" />
                                  <span className="truncate max-w-[130px]">{clusterLabel}</span>
                                </span>
                                <span className="text-[10px] text-zinc-500 block truncate max-w-[140px]">
                                  {c.location || c.area || 'Pune, India'}
                                </span>
                              </div>
                            </td>

                            {/* Column 5: Tech Stack */}
                            <td className="py-3 px-3 align-top">
                              {c.tech_stack && c.tech_stack.length > 0 ? (
                                <div className="flex flex-wrap gap-1 max-w-[160px]">
                                  {c.tech_stack.slice(0, 3).map((tech: string, tidx: number) => (
                                    <span
                                      key={tidx}
                                      className="px-1.5 py-0.5 rounded text-[9px] font-mono font-medium bg-zinc-100 text-zinc-700 border border-zinc-200 truncate"
                                    >
                                      {tech}
                                    </span>
                                  ))}
                                  {c.tech_stack.length > 3 && (
                                    <span className="px-1 py-0.5 rounded text-[9px] font-mono text-zinc-400">
                                      +{c.tech_stack.length - 3}
                                    </span>
                                  )}
                                </div>
                              ) : (
                                <span className="text-[10px] text-zinc-400 italic">Stack pending</span>
                              )}
                            </td>

                            {/* Column 6: Roles */}
                            <td className="py-3 px-3 align-top text-center">
                              <button
                                type="button"
                                onClick={() => {
                                  if (openRoles > 0) {
                                    setJobSearch(c.company_name);
                                    setActiveTab('jobs');
                                  } else {
                                    openCompany(c.company_name);
                                  }
                                }}
                                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold cursor-pointer transition ${
                                  openRoles > 0
                                    ? 'bg-amber-100 text-amber-900 border border-amber-300 hover:bg-amber-200'
                                    : 'bg-zinc-100 text-zinc-400 border border-zinc-200 hover:bg-zinc-200'
                                }`}
                                title={
                                  openRoles > 0
                                    ? `View ${openRoles} jobs in Jobs tab`
                                    : 'No active job requisitions found'
                                }
                              >
                                <Briefcase className="w-3 h-3 text-amber-700 shrink-0" />
                                <span>{openRoles}</span>
                              </button>
                            </td>

                            {/* Column 7: Actions */}
                            <td className="py-3 px-4 align-top text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => handleEnrichSingleCompany(c.company_name)}
                                  disabled={isEnriching}
                                  className="p-1.5 rounded-xl border border-zinc-200/90 text-zinc-600 hover:text-amber-800 hover:bg-amber-50 hover:border-amber-300 transition cursor-pointer disabled:opacity-50"
                                  title="Enrich emails and contacts for this company"
                                >
                                  {isEnriching ? (
                                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-600" />
                                  ) : (
                                    <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                                  )}
                                </button>

                                <button
                                  type="button"
                                  onClick={() => openCompany(c.company_name)}
                                  className="px-2.5 py-1 rounded-xl font-semibold text-[11px] bg-zinc-900 text-white hover:bg-zinc-800 shadow-2xs cursor-pointer transition flex items-center gap-1"
                                >
                                  <span>Intel</span>
                                  <ArrowUpRight className="w-3 h-3 text-zinc-300" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                /* ----------------- CARDS GRID VIEW ----------------- */
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
                        className="liquid-card rounded-2xl p-4 flex flex-col items-center text-center justify-between transition-all duration-200 hover:scale-[1.02] hover:shadow-md hover:border-amber-300 cursor-pointer group relative overflow-hidden min-h-[175px] border border-white/80 bg-white/70"
                      >
                        {c.is_vip === 1 && (
                          <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded-full text-[9px] font-extrabold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-0.5">
                            <Star className="w-2.5 h-2.5 fill-amber-500 text-amber-600" />
                            VIP
                          </span>
                        )}

                        {/* Icon / Logo */}
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

                        {/* Name */}
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
                          {c.referral_available === 1 && (
                            <span className="inline-flex items-center gap-0.5 text-[9px] font-bold text-emerald-700 mt-0.5">
                              <UserCheck className="w-2.5 h-2.5" /> Ref: {c.referrer_name || '1st'}
                            </span>
                          )}
                        </div>

                        {/* Job Count */}
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
                <div className="flex items-center gap-1 bg-zinc-100 p-1 rounded-xl border border-zinc-200 text-xs">
                  <button
                    onClick={() => setLeadPersona('ALL')}
                    className={`px-3 py-1 rounded-lg font-medium transition cursor-pointer ${
                      leadPersona === 'ALL' ? 'bg-white text-zinc-900 shadow-2xs font-semibold' : 'text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    All Contacts
                  </button>
                  <button
                    onClick={() => setLeadPersona('founder')}
                    className={`px-3 py-1 rounded-lg font-medium transition cursor-pointer ${
                      leadPersona === 'founder' ? 'bg-zinc-900 text-white shadow-2xs' : 'text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    Founders
                  </button>
                  <button
                    onClick={() => setLeadPersona('hr')}
                    className={`px-3 py-1 rounded-lg font-medium transition cursor-pointer ${
                      leadPersona === 'hr' ? 'bg-zinc-900 text-white shadow-2xs' : 'text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    Talent & HR
                  </button>
                  <button
                    onClick={() => setLeadPersona('engineer')}
                    className={`px-3 py-1 rounded-lg font-medium transition cursor-pointer ${
                      leadPersona === 'engineer' ? 'bg-zinc-900 text-white shadow-2xs' : 'text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    Engineering Leads
                  </button>
                </div>

                <select
                  value={leadStatus}
                  onChange={(e) => setLeadStatus(e.target.value)}
                  className="bg-white border border-zinc-200 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 shadow-2xs"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="drafted">Drafts Ready</option>
                  <option value="pending_review">Pending Review</option>
                  <option value="approved">Approved for Dispatch</option>
                  <option value="sent">Dispatched / Sent</option>
                  <option value="rejected">Rejected</option>
                </select>

                <select
                  value={leadSortBy}
                  onChange={(e) => setLeadSortBy(e.target.value)}
                  className="bg-white border border-zinc-200 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 shadow-2xs"
                >
                  <option value="priority">Priority Score (High to Low)</option>
                  <option value="date">Recently Discovered</option>
                </select>
              </div>

              <div className="flex items-center gap-2 w-full md:w-auto justify-end flex-wrap">
                <button
                  onClick={handleApproveAllPending}
                  className="saas-card px-3 py-2 rounded-xl text-xs font-medium text-emerald-800 hover:bg-emerald-50 flex items-center gap-1.5 cursor-pointer shadow-2xs"
                  title="Approve all visible pending review leads"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Approve Visible</span>
                </button>

                <button
                  onClick={handleDispatchApprovedLeads}
                  disabled={dispatchingLeads}
                  className="px-3.5 py-2 rounded-xl text-xs font-medium text-white bg-zinc-900 hover:bg-zinc-800 flex items-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5 text-zinc-300" />
                  <span>{dispatchingLeads ? 'Dispatching...' : 'Dispatch Approved'}</span>
                </button>
              </div>
            </div>

            {dispatchMessage && (
              <div className="p-3.5 rounded-xl bg-zinc-100 border border-zinc-200 text-xs text-zinc-800 font-medium shadow-2xs flex items-center justify-between">
                <span>{dispatchMessage}</span>
                <button onClick={() => setDispatchMessage(null)} className="text-zinc-500 hover:text-zinc-800">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Leads List */}
            <div className="saas-card rounded-2xl p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-200/80 text-xs text-zinc-500 font-medium px-2 flex-wrap gap-2">
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-1.5 cursor-pointer text-zinc-700 select-none">
                    <input
                      type="checkbox"
                      checked={leads.length > 0 && selectedLeadIds.length === leads.length}
                      onChange={handleToggleSelectAllLeads}
                      className="rounded accent-zinc-900 cursor-pointer"
                    />
                    <span>Select All</span>
                  </label>
                  <span>Showing {leads.length} of {leadPagination.total.toLocaleString()} recruiter contacts</span>
                </div>
                <span>Page {leadPage} of {leadPagination.totalPages}</span>
              </div>

              {/* Floating Batch Action Bar */}
              {selectedLeadIds.length > 0 && (
                <div className="p-3 rounded-xl bg-zinc-900 text-white flex items-center justify-between gap-3 shadow-md animate-in fade-in flex-wrap border border-zinc-800">
                  <div className="flex items-center gap-2 text-xs font-medium">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>{selectedLeadIds.length} contact{selectedLeadIds.length > 1 ? 's' : ''} selected</span>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      disabled={batchApproving}
                      onClick={handleBatchApproveSelected}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-800 text-white hover:bg-zinc-700 transition cursor-pointer"
                    >
                      {batchApproving ? 'Approving...' : 'Approve Selected'}
                    </button>
                    <button
                      type="button"
                      disabled={batchSending}
                      onClick={handleBatchSendSelected}
                      className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-500 transition cursor-pointer flex items-center gap-1.5"
                    >
                      <Send className="w-3.5 h-3.5 text-white" />
                      <span>{batchSending ? 'Sending...' : 'Send Selected'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedLeadIds([])}
                      className="text-zinc-400 hover:text-white text-xs underline cursor-pointer ml-2"
                    >
                      Deselect
                    </button>
                  </div>
                </div>
              )}

              {leadsLoading ? (
                <div className="py-20 text-center text-xs text-zinc-400">Loading recruiter contacts...</div>
              ) : leads.length === 0 ? (
                <div className="py-20 text-center text-xs text-zinc-500 space-y-2">
                  <p>No recruiter contacts match the selected persona or filters.</p>
                  <button
                    onClick={() => {
                      setLeadPersona('ALL');
                      setLeadStatus('ALL');
                      setLeadSearch('');
                      setLeadMinScore(0);
                    }}
                    className="text-zinc-900 underline font-medium text-xs cursor-pointer"
                  >
                    Reset all filters
                  </button>
                </div>
              ) : (
                <div className="space-y-2.5">
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
                        : 'bg-zinc-100 text-zinc-800 border-zinc-200';

                    const sBadgeClass =
                      score >= 80
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200 font-semibold'
                        : score >= 60
                        ? 'bg-zinc-100 text-zinc-800 border-zinc-200'
                        : 'bg-zinc-50 text-zinc-600 border-zinc-200';

                    const personaLabel =
                      personaVal === 'founder' ? 'Founder' : personaVal === 'hr' ? 'Talent / HR' : 'Engineering';

                    return (
                      <div
                        key={l.lead_id}
                        className={`saas-card rounded-xl p-3.5 border transition flex flex-col md:flex-row md:items-center justify-between gap-3.5 cursor-pointer ${
                          isSelected ? 'border-zinc-900 bg-zinc-50/60 shadow-xs' : 'hover:border-zinc-300'
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
                            className="w-4 h-4 rounded accent-zinc-900 cursor-pointer"
                          />
                        </div>

                        {/* Avatar Initials */}
                        <div className="w-8 h-8 rounded-lg bg-zinc-100 border border-zinc-200 shrink-0 flex items-center justify-center font-semibold text-xs text-zinc-800 hidden sm:flex">
                          {l.contact_name ? l.contact_name.charAt(0).toUpperCase() : 'C'}
                        </div>

                        {/* Lead Info & Intelligence Preview */}
                        <div className="space-y-1.5 min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-sm text-zinc-900 group-hover:text-zinc-700 transition">
                              {l.contact_name || 'Hiring Contact'}
                            </span>

                            <span className={`text-[10px] px-2 py-0.5 rounded-md border ${sBadgeClass}`}>
                              Score: {score}
                            </span>

                            <span className={`text-[10px] px-2 py-0.5 rounded-md font-medium border ${pBadgeClass}`}>
                              {personaLabel}
                            </span>

                            {/* MX Deliverability Badge */}
                            {l.mx_provider && (
                              <span className="text-[10px] px-2 py-0.5 rounded-md font-medium bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                <span>{l.mx_provider}</span>
                              </span>
                            )}

                            {/* Matched Job Citation */}
                            {l.matched_job_title && (
                              <span className="text-[10px] px-2 py-0.5 rounded-md font-medium bg-zinc-100 text-zinc-700 border border-zinc-200 flex items-center gap-1">
                                <Briefcase className="w-3 h-3 text-zinc-500" />
                                <span className="truncate max-w-[200px]">{l.matched_job_title}</span>
                              </span>
                            )}

                            {/* Coordinated Dual Attack Pair Indicator */}
                            {l.dual_attack_pair_id && (
                              <span className="text-[10px] px-2 py-0.5 rounded-md font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
                                Paired Outreach
                              </span>
                            )}

                            <span
                              className={`text-[10px] px-2 py-0.5 rounded-md font-medium border ${
                                l.outreach_status === 'approved'
                                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                  : l.outreach_status === 'sent'
                                  ? 'bg-blue-50 text-blue-800 border-blue-200'
                                  : l.outreach_status === 'rejected'
                                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                                  : 'bg-zinc-100 text-zinc-700 border-zinc-200'
                              }`}
                            >
                              {l.outreach_status}
                            </span>
                          </div>

                          <div className="text-xs text-zinc-500 flex items-center gap-2.5 flex-wrap">
                            <span className="font-semibold text-zinc-800">{l.company_name}</span>
                            <span>•</span>
                            <span className="font-mono text-zinc-600">{l.contact_email}</span>
                            {l.role_title && (
                              <>
                                <span>•</span>
                                <span className="text-zinc-600">{l.role_title}</span>
                              </>
                            )}
                          </div>

                          {/* Email Pitch Subject Snippet */}
                          {(l.email_subject || l.email_draft_subject) && (
                            <div className="text-xs text-zinc-600 bg-zinc-50 p-2 rounded-lg border border-zinc-200/80 font-sans truncate">
                              <span className="font-medium text-zinc-800">Draft:</span>{' '}
                              <span>{l.email_subject || l.email_draft_subject}</span>
                            </div>
                          )}
                        </div>

                        {/* Actions on Row */}
                        <div
                          className="flex items-center gap-2 shrink-0 md:self-center"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            type="button"
                            onClick={() => openLead(l.lead_id)}
                            className="saas-card px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-800 hover:bg-zinc-50 flex items-center gap-1.5 cursor-pointer"
                          >
                            <Mail className="w-3.5 h-3.5 text-zinc-500" />
                            <span>Review Draft</span>
                          </button>

                          {l.outreach_status !== 'sent' && (
                            <button
                              type="button"
                              disabled={quickSendingLeadId === l.lead_id}
                              onClick={() => handleQuickSendLead(l.lead_id, l.contact_email)}
                              className="px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-zinc-900 hover:bg-zinc-800 flex items-center gap-1.5 cursor-pointer transition disabled:opacity-50"
                              title="Send draft with attached resume"
                            >
                              <Send className="w-3.5 h-3.5 text-zinc-300" />
                              <span>{quickSendingLeadId === l.lead_id ? 'Sending...' : 'Send'}</span>
                            </button>
                          )}

                          {l.outreach_status === 'pending_review' && (
                            <button
                              type="button"
                              onClick={() => handleQuickApproveLead(l.lead_id)}
                              className="saas-card px-2 py-1.5 rounded-lg text-xs font-medium text-emerald-800 hover:bg-emerald-50 border border-emerald-200 cursor-pointer"
                              title="Approve draft"
                            >
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            </button>
                          )}

                          <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-zinc-900 transition" />
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
