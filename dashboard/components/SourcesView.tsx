'use client';

import React, { useEffect, useState } from 'react';
import {
  Globe,
  Briefcase,
  Search,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  Building2,
  Calendar,
  Sparkles,
  ArrowUpRight,
  Filter,
  CheckCircle2,
  Layers,
  Flame,
} from 'lucide-react';

interface SourceStatItem {
  id: string;
  name: string;
  badge: string;
  type: string;
  total_jobs: number;
  avg_score: number | null;
  last_seen: string | null;
  top_companies: string[];
  status: 'ACTIVE' | 'CONNECTED';
  description: string;
}

interface SourcesViewProps {
  onSelectJob?: (url: string) => void;
}

// Custom brand SVGs for prominent platforms
function SourcePlatformIcon({ id, className = "w-5 h-5" }: { id: string; className?: string }) {
  switch (id) {
    case 'linkedin':
      return (
        <svg className={className} viewBox="0 0 24 24" fill="#0A66C2">
          <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9h2.76v8.37H6.46V10.9M7.84 6.2a1.62 1.62 0 1 0 1.62 1.62A1.62 1.62 0 0 0 7.84 6.2" />
        </svg>
      );
    case 'workday':
      return (
        <svg className={className} viewBox="0 0 24 24" fill="none">
          <rect width="24" height="24" rx="6" fill="#005CB9" />
          <path d="M7 16V8h2.3l2.7 5.1L14.7 8H17v8h-2.1v-5.2l-2.4 4.5h-1L9.1 10.8V16H7z" fill="white" />
          <path d="M4 19.5c4-1.8 12-1.8 16 0" stroke="#FF7900" strokeWidth="2" strokeLinecap="round" />
        </svg>
      );
    case 'internet_search':
      return (
        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 via-emerald-500 to-amber-500 flex items-center justify-center p-0.5 shadow-2xs">
          <div className="w-full h-full bg-white rounded-[5px] flex items-center justify-center">
            <Globe className="w-3.5 h-3.5 text-blue-600" />
          </div>
        </div>
      );
    case 'greenhouse':
      return (
        <div className="w-6 h-6 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold text-xs shadow-2xs">
          GH
        </div>
      );
    case 'ashby':
      return (
        <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow-2xs">
          A
        </div>
      );
    case 'lever':
      return (
        <div className="w-6 h-6 rounded-lg bg-amber-500 flex items-center justify-center text-white font-bold text-xs shadow-2xs">
          L
        </div>
      );
    case 'hackernews':
      return (
        <div className="w-6 h-6 rounded-lg bg-[#FF6600] flex items-center justify-center text-white font-black text-xs shadow-2xs">
          Y
        </div>
      );
    case 'naukri':
      return (
        <div className="w-6 h-6 rounded-lg bg-blue-700 flex items-center justify-center text-white font-extrabold text-[10px] shadow-2xs">
          NK
        </div>
      );
    default:
      return <Globe className={`${className} text-zinc-600`} />;
  }
}

export function SourcesView({ onSelectJob }: SourcesViewProps) {
  const [sources, setSources] = useState<SourceStatItem[]>([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [totalPlatforms, setTotalPlatforms] = useState(0);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Filtered jobs state
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [totalFilteredJobs, setTotalFilteredJobs] = useState(0);

  // Fetch sources list
  useEffect(() => {
    async function loadSources() {
      setLoading(true);
      try {
        const res = await fetch('/api/sources');
        const json = await res.json();
        if (json.success) {
          setSources(json.sources || []);
          setTotalJobs(json.totalJobs || 0);
          setTotalPlatforms(json.totalPlatforms || 0);
        }
      } catch (e) {
        console.error('Failed to load sources', e);
      } finally {
        setLoading(false);
      }
    }
    loadSources();
  }, []);

  // Fetch jobs when source filter or search query changes
  useEffect(() => {
    async function loadFilteredJobs() {
      setJobsLoading(true);
      try {
        const params = new URLSearchParams();
        if (selectedSourceId) {
          params.set('ats', selectedSourceId);
        }
        if (searchQuery) {
          params.set('search', searchQuery);
        }
        params.set('page', page.toString());
        params.set('limit', '25');

        const res = await fetch(`/api/jobs?${params.toString()}`);
        const json = await res.json();
        if (json.success) {
          setJobs(json.jobs || []);
          setTotalFilteredJobs(json.pagination?.total || 0);
        }
      } catch (e) {
        console.error('Failed to load source jobs', e);
      } finally {
        setJobsLoading(false);
      }
    }
    loadFilteredJobs();
  }, [selectedSourceId, searchQuery, page]);

  const activeSourceObj = sources.find((s) => s.id === selectedSourceId);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* ---------------- Top Hero Bar ---------------- */}
      <div className="liquid-glass rounded-3xl p-5 sm:p-6 border border-white/90 shadow-xs relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-blue-100/50 via-cyan-100/30 to-transparent rounded-full blur-2xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-extrabold tracking-wider px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                MULTI-CHANNEL INGESTION ENGINES
              </span>
              <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live Ingestion Active
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-black text-zinc-950 tracking-tight">
              Job Discovery Sources & Crawlers
            </h1>
            <p className="text-xs sm:text-sm text-zinc-600 max-w-2xl">
              Real-time audit of all platforms powering ApplyPilot. Track jobs discovered via 
              <strong> LinkedIn</strong>, <strong>Workday Enterprise</strong>, <strong>Google Search / OSINT Web Crawlers</strong>, 
              and direct ATS boards.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="liquid-card px-4 py-3 rounded-2xl border border-white text-center shadow-2xs">
              <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block">Total Harvesters</span>
              <span className="text-xl font-extrabold text-zinc-900">{totalPlatforms} Platforms</span>
            </div>
            <div className="liquid-card px-4 py-3 rounded-2xl border border-white text-center shadow-2xs bg-white/70">
              <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block">Jobs Grabbed</span>
              <span className="text-xl font-extrabold text-blue-600">{totalJobs.toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ---------------- Sources Platforms Grid ---------------- */}
      <div>
        <div className="flex items-center justify-between mb-3 px-1">
          <h2 className="text-sm font-bold text-zinc-800 flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" />
            Active Sourcing Platforms
            <span className="text-xs font-normal text-zinc-500">
              (Click any platform to view its grabbed jobs)
            </span>
          </h2>
          {selectedSourceId && (
            <button
              onClick={() => {
                setSelectedSourceId(null);
                setPage(1);
              }}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition cursor-pointer flex items-center gap-1"
            >
              Clear filter (Show All)
            </button>
          )}
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs text-zinc-400">Loading discovery sources...</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5">
            {sources.map((src) => {
              const isSelected = selectedSourceId === src.id;
              return (
                <div
                  key={src.id}
                  onClick={() => {
                    setSelectedSourceId(isSelected ? null : src.id);
                    setPage(1);
                  }}
                  className={`liquid-card rounded-2xl p-4 transition-all duration-200 cursor-pointer relative overflow-hidden group border ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50/50 shadow-md ring-2 ring-blue-300'
                      : 'border-white/80 hover:border-zinc-300 hover:shadow-xs hover:bg-white/95'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 rounded-xl bg-zinc-50 border border-zinc-200/80 flex items-center justify-center shrink-0 shadow-2xs group-hover:scale-105 transition-transform">
                        <SourcePlatformIcon id={src.id} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-bold text-xs text-zinc-900 truncate group-hover:text-blue-600 transition-colors">
                          {src.name}
                        </h3>
                        <span className="text-[10px] text-zinc-500 font-medium block truncate">
                          {src.type}
                        </span>
                      </div>
                    </div>

                    <span className="text-[9px] font-extrabold tracking-wider px-1.5 py-0.5 rounded-full bg-zinc-100 text-zinc-700 border border-zinc-200 uppercase shrink-0">
                      {src.badge}
                    </span>
                  </div>

                  <p className="text-[11px] text-zinc-600 line-clamp-2 mb-3 min-h-[32px]">
                    {src.description}
                  </p>

                  <div className="pt-2 border-t border-zinc-200/60 flex items-center justify-between text-xs">
                    <div>
                      <span className="text-[10px] text-zinc-400 font-semibold block uppercase tracking-wider">
                        Jobs Grabbed
                      </span>
                      <span className="font-extrabold text-zinc-950 text-sm">
                        {src.total_jobs.toLocaleString()}
                      </span>
                    </div>

                    {src.avg_score && (
                      <div className="text-right">
                        <span className="text-[10px] text-zinc-400 font-semibold block uppercase tracking-wider">
                          Avg Match
                        </span>
                        <span className="font-extrabold text-emerald-600 text-sm">
                          {src.avg_score}/10
                        </span>
                      </div>
                    )}
                  </div>

                  {src.top_companies && src.top_companies.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-zinc-100 text-[10px] text-zinc-500 truncate">
                      <span className="font-semibold text-zinc-700">Top:</span> {src.top_companies.join(', ')}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ---------------- Jobs Grabbed from Selected Platform ---------------- */}
      <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-200/60">
          <div className="flex items-center gap-2.5">
            {selectedSourceId && <SourcePlatformIcon id={selectedSourceId} className="w-5 h-5" />}
            <div>
              <h3 className="font-bold text-sm text-zinc-900 flex items-center gap-2">
                {activeSourceObj ? `Jobs grabbed from ${activeSourceObj.name}` : 'All Grabbed Jobs across All Sources'}
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                  {totalFilteredJobs.toLocaleString()} roles
                </span>
              </h3>
              <p className="text-xs text-zinc-500">
                {activeSourceObj
                  ? `Filtered specifically for postings harvested from ${activeSourceObj.name}.`
                  : 'Click on any source card above to filter jobs by specific platform.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                placeholder="Search title, company..."
                className="bg-white/90 border border-zinc-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-200 w-48 sm:w-60 shadow-2xs"
              />
            </div>
          </div>
        </div>

        {/* Jobs Table */}
        <div className="overflow-x-auto">
          {jobsLoading ? (
            <div className="py-16 text-center text-xs text-zinc-400">Loading platform jobs...</div>
          ) : jobs.length === 0 ? (
            <div className="py-16 text-center text-xs text-zinc-500">No jobs found for this source query.</div>
          ) : (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-zinc-200/80 text-[11px] text-zinc-500 font-bold uppercase tracking-wider">
                  <th className="py-2.5 px-3">Source</th>
                  <th className="py-2.5 px-3">Role Title</th>
                  <th className="py-2.5 px-3">Company</th>
                  <th className="py-2.5 px-3">Location</th>
                  <th className="py-2.5 px-3 text-center">Score</th>
                  <th className="py-2.5 px-3">Route</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-medium">
                {jobs.map((job) => {
                  const siteLower = (job.site || '').toLowerCase();
                  let sourceBadge = 'Web';
                  let iconId = 'internet_search';
                  if (siteLower.includes('workday')) {
                    sourceBadge = 'Workday';
                    iconId = 'workday';
                  } else if (siteLower.includes('linkedin')) {
                    sourceBadge = 'LinkedIn';
                    iconId = 'linkedin';
                  } else if (siteLower.includes('greenhouse')) {
                    sourceBadge = 'Greenhouse';
                    iconId = 'greenhouse';
                  } else if (siteLower.includes('ashby')) {
                    sourceBadge = 'Ashby';
                    iconId = 'ashby';
                  } else if (siteLower.includes('hackernews') || siteLower.includes('ycombinator')) {
                    sourceBadge = 'HackerNews';
                    iconId = 'hackernews';
                  } else if (siteLower.includes('lever')) {
                    sourceBadge = 'Lever';
                    iconId = 'lever';
                  } else if (siteLower.includes('google') || siteLower.includes('company_careers')) {
                    sourceBadge = 'Google Search';
                    iconId = 'internet_search';
                  }

                  return (
                    <tr
                      key={job.url}
                      className="hover:bg-blue-50/40 transition-colors group cursor-pointer"
                      onClick={() => onSelectJob && onSelectJob(job.url)}
                    >
                      <td className="py-3 px-3 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <SourcePlatformIcon id={iconId} className="w-4 h-4" />
                          <span className="font-semibold text-zinc-800 text-[11px]">{sourceBadge}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-bold text-zinc-950 group-hover:text-blue-600 transition-colors line-clamp-1 max-w-xs sm:max-w-md">
                          {job.title}
                        </div>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap text-zinc-700 font-semibold">
                        {job.company}
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap text-zinc-500 text-[11px]">
                        {job.location || 'Remote'}
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap text-center">
                        {job.fit_score !== null && job.fit_score !== undefined ? (
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full font-black text-[11px] ${
                              job.fit_score >= 8
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                : job.fit_score >= 6
                                ? 'bg-blue-100 text-blue-800 border border-blue-300'
                                : 'bg-zinc-100 text-zinc-700 border border-zinc-200'
                            }`}
                          >
                            {job.fit_score}/10
                          </span>
                        ) : (
                          <span className="text-zinc-400 text-[10px]">—</span>
                        )}
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-700 border border-zinc-200">
                          {job.execution_route || 'PORTAL'}
                        </span>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {job.url && (
                            <a
                              href={job.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="p-1 rounded-lg hover:bg-zinc-200 text-zinc-500 hover:text-zinc-900 transition"
                              title="Open original job posting"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                          <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-blue-600 transition-colors" />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

