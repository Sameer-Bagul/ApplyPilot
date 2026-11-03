'use client';

import React from 'react';
import {
  Sprout,
  Sparkles,
  Sliders,
  Building2,
  Compass,
  Target,
  Share2,
  MapPin,
  Terminal,
  ShieldCheck,
  TrendingUp,
  Globe,
  Briefcase,
  LucideIcon,
} from 'lucide-react';
import { Tooltip } from './Tooltip';

export interface SourceMeta {
  key: string;
  name: string;
  shortName: string;
  category: string;
  icon: LucideIcon;
  badgeClass: string;
  dotColor: string;
  tooltipTitle: string;
  tooltipDesc: string;
}

const SOURCES: Record<string, SourceMeta> = {
  greenhouse: {
    key: 'greenhouse',
    name: 'Greenhouse',
    shortName: 'Greenhouse',
    category: 'Direct ATS',
    icon: Sprout,
    badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200/70',
    dotColor: 'bg-emerald-500',
    tooltipTitle: 'Greenhouse ATS API',
    tooltipDesc: 'Direct keyless REST API (boards-api.greenhouse.io). Zero auth, high-signal public board.',
  },
  ashby: {
    key: 'ashby',
    name: 'Ashby',
    shortName: 'Ashby',
    category: 'Direct ATS',
    icon: Sparkles,
    badgeClass: 'bg-purple-50 text-purple-800 border-purple-200/70',
    dotColor: 'bg-purple-500',
    tooltipTitle: 'Ashby Job Board API',
    tooltipDesc: 'Modern venture-backed startup ATS. Keyless REST/GraphQL posting API.',
  },
  lever: {
    key: 'lever',
    name: 'Lever',
    shortName: 'Lever',
    category: 'Direct ATS',
    icon: Sliders,
    badgeClass: 'bg-amber-50 text-amber-800 border-amber-200/70',
    dotColor: 'bg-amber-500',
    tooltipTitle: 'Lever Postings API',
    tooltipDesc: 'High-frequency tech hiring board. Direct JSON stream (api.lever.co).',
  },
  workday: {
    key: 'workday',
    name: 'Workday',
    shortName: 'Workday',
    category: 'Enterprise ATS',
    icon: Building2,
    badgeClass: 'bg-blue-50 text-blue-800 border-blue-200/70',
    dotColor: 'bg-blue-500',
    tooltipTitle: 'Workday CXS Endpoint',
    tooltipDesc: 'Enterprise careers portal. Automated CXS JSON queries with 2FA OTP support.',
  },
  naukri: {
    key: 'naukri',
    name: 'Naukri India',
    shortName: 'Naukri',
    category: 'India Portal',
    icon: Compass,
    badgeClass: 'bg-cyan-50 text-cyan-800 border-cyan-200/70',
    dotColor: 'bg-cyan-600',
    tooltipTitle: 'Naukri India Feed',
    tooltipDesc: "India's premier tech hiring portal. Live feed covering Bangalore, Pune, Hyderabad, NCR.",
  },
  indeed: {
    key: 'indeed',
    name: 'Indeed (India/US)',
    shortName: 'Indeed',
    category: 'Aggregator',
    icon: Target,
    badgeClass: 'bg-sky-50 text-sky-800 border-sky-200/70',
    dotColor: 'bg-sky-600',
    tooltipTitle: 'Indeed (India & Global)',
    tooltipDesc: 'Global high-volume job aggregator with live markdown and salary range data.',
  },
  linkedin: {
    key: 'linkedin',
    name: 'LinkedIn Jobs',
    shortName: 'LinkedIn',
    category: 'Network',
    icon: Share2,
    badgeClass: 'bg-indigo-50 text-indigo-800 border-indigo-200/70',
    dotColor: 'bg-indigo-600',
    tooltipTitle: 'LinkedIn Jobs & Posts',
    tooltipDesc: 'Professional network postings and recruiter hiring threads via JobSpy & DDG dorks.',
  },
  bangalore_map: {
    key: 'bangalore_map',
    name: 'BLR Startup Map',
    shortName: 'BLR Map',
    category: 'Startup Directory',
    icon: MapPin,
    badgeClass: 'bg-rose-50 text-rose-800 border-rose-200/70',
    dotColor: 'bg-rose-500',
    tooltipTitle: 'Bangalore Startup Map',
    tooltipDesc: 'Ingested from 1,085+ curated Bangalore startups across Koramangala, Indiranagar, HSR.',
  },
  hackernews: {
    key: 'hackernews',
    name: 'Hacker News',
    shortName: 'HN',
    category: 'Community',
    icon: Terminal,
    badgeClass: 'bg-orange-50 text-orange-800 border-orange-200/70',
    dotColor: 'bg-orange-500',
    tooltipTitle: 'Hacker News (YC)',
    tooltipDesc: 'Monthly Y Combinator "Who is hiring?" developer threads.',
  },
  freehire: {
    key: 'freehire',
    name: 'Freehire',
    shortName: 'Freehire',
    category: 'Directory',
    icon: ShieldCheck,
    badgeClass: 'bg-teal-50 text-teal-800 border-teal-200/70',
    dotColor: 'bg-teal-500',
    tooltipTitle: 'Freehire Directory',
    tooltipDesc: 'Verified engineering listings and company salary insights.',
  },
  topstartups: {
    key: 'topstartups',
    name: 'TopStartups',
    shortName: 'TopStartups',
    category: 'VC Directory',
    icon: TrendingUp,
    badgeClass: 'bg-yellow-50 text-yellow-800 border-yellow-200/70',
    dotColor: 'bg-yellow-600',
    tooltipTitle: 'TopStartups.io',
    tooltipDesc: 'Venture-backed fast-growing startup talent board.',
  },
  custom: {
    key: 'custom',
    name: 'Direct Portal',
    shortName: 'Direct',
    category: 'Career Page',
    icon: Globe,
    badgeClass: 'bg-zinc-100 text-zinc-700 border-zinc-200/70',
    dotColor: 'bg-zinc-500',
    tooltipTitle: 'Direct / Custom Career Page',
    tooltipDesc: 'Discovered via Schema.org JSON-LD or custom company careers page.',
  },
};

export function getSourceMeta(siteString?: string | null): SourceMeta {
  if (!siteString) return SOURCES.custom;
  const s = siteString.toLowerCase().trim();

  if (s.includes('greenhouse')) return SOURCES.greenhouse;
  if (s.includes('ashby')) return SOURCES.ashby;
  if (s.includes('lever')) return SOURCES.lever;
  if (s.includes('workday')) return SOURCES.workday;
  if (s.includes('naukri')) return SOURCES.naukri;
  if (s.includes('indeed')) return SOURCES.indeed;
  if (s.includes('linkedin')) return SOURCES.linkedin;
  if (s.includes('bangalore') || s.includes('startupmap') || s.includes('arena')) return SOURCES.bangalore_map;
  if (s.includes('hackernews') || s.includes('hn')) return SOURCES.hackernews;
  if (s.includes('freehire')) return SOURCES.freehire;
  if (s.includes('topstartup')) return SOURCES.topstartups;
  if (s.includes('glassdoor')) {
    return {
      key: 'glassdoor',
      name: 'Glassdoor',
      shortName: 'Glassdoor',
      category: 'Aggregator',
      icon: Building2,
      badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200/70',
      dotColor: 'bg-emerald-600',
      tooltipTitle: 'Glassdoor Jobs',
      tooltipDesc: 'Company ratings and verified job postings stream.',
    };
  }
  if (s.includes('ziprecruiter') || s.includes('zip_recruiter')) {
    return {
      key: 'ziprecruiter',
      name: 'ZipRecruiter',
      shortName: 'ZipRecruiter',
      category: 'Aggregator',
      icon: Briefcase,
      badgeClass: 'bg-indigo-50 text-indigo-800 border-indigo-200/70',
      dotColor: 'bg-indigo-600',
      tooltipTitle: 'ZipRecruiter',
      tooltipDesc: 'High-frequency recruiter marketplace stream.',
    };
  }

  // Return formatted custom source
  return {
    ...SOURCES.custom,
    name: siteString.length > 18 ? siteString.slice(0, 16) + '...' : siteString,
    shortName: siteString.split('.')[0] || 'Direct',
    tooltipTitle: siteString,
  };
}

interface SourceBadgeProps {
  site?: string | null;
  compact?: boolean;
  className?: string;
}

export function SourceBadge({ site, compact = false, className = '' }: SourceBadgeProps) {
  const meta = getSourceMeta(site);
  const Icon = meta.icon;

  const tooltipContent = (
    <div className="flex flex-col gap-1 max-w-[220px]">
      <div className="flex items-center justify-between gap-2 border-b border-zinc-200/60 pb-1">
        <span className="font-semibold text-zinc-900 text-xs flex items-center gap-1.5">
          <Icon className="w-3.5 h-3.5 text-zinc-700" />
          {meta.tooltipTitle}
        </span>
        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-100 text-zinc-600">
          {meta.category}
        </span>
      </div>
      <p className="text-[11px] text-zinc-600 leading-snug">
        {meta.tooltipDesc}
      </p>
      {site && site !== meta.name && (
        <span className="text-[9.5px] font-mono text-zinc-400 truncate">
          src: {site}
        </span>
      )}
    </div>
  );

  return (
    <Tooltip content={tooltipContent}>
      <span
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-xs font-medium border transition-all cursor-help shadow-xs hover:shadow-sm ${meta.badgeClass} ${className}`}
      >
        <Icon className="w-3.5 h-3.5 shrink-0" />
        {!compact && (
          <span className="font-medium tracking-tight whitespace-nowrap">
            {meta.shortName}
          </span>
        )}
      </span>
    </Tooltip>
  );
}

