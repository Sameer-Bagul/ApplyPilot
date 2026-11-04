'use client';

import React, { useState } from 'react';
import {
  Layers,
  Cpu,
  Mail,
  ShieldCheck,
  Zap,
  Repeat,
  Compass,
  CheckCircle2,
  Database,
  Search,
  Globe,
  Radio,
  Clock,
  Terminal,
  ArrowRight,
  Sparkles,
  Lock,
  Flame,
  Copy,
  Check,
} from 'lucide-react';

export function ArchitectureView() {
  const [copiedCommand, setCopiedCommand] = useState<string | null>(null);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCommand(text);
    setTimeout(() => setCopiedCommand(null), 2000);
  };

  const engines = [
    {
      id: 'ats-harvester',
      title: '4.7M+ Direct ATS Harvester',
      badge: 'Zero Aggregators',
      badgeClass: 'bg-cyan-50 text-cyan-800 border-cyan-200/80',
      icon: Compass,
      iconClass: 'bg-cyan-500/10 text-cyan-700 border-cyan-200',
      description:
        'Bypasses noisy third-party job aggregators to stream open roles directly from official career boards at origin.',
      highlights: [
        'FreeHire & direct ATS adapters for Ashby, Greenhouse, Lever, and Workday',
        'Direct JSON endpoints and clean DOM extraction with zero page bloat',
        'De-duplicates listings automatically via canonical URL hashing',
        'Continuous ingestion supporting over 4.7 million real-time career postings',
      ],
      command: 'applypilot marathon --continuous',
    },
    {
      id: 'local-matcher',
      title: 'Deterministic 4-Factor Local Matcher',
      badge: 'Zero External LLM Tokens',
      badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
      icon: Cpu,
      iconClass: 'bg-emerald-500/10 text-emerald-700 border-emerald-200',
      description:
        'Evaluates candidates against jobs in sub-millisecond execution times without costly external LLM API bills.',
      highlights: [
        'Factor 1: Role Relevance & Title Alignment (0-4 points)',
        'Factor 2: Tech Stack & Skill Matrix (Python, TS, Next.js, AI Agents) (0-3 points)',
        'Factor 3: Seniority, Staff & Lead Alignment (0-2 points)',
        'Factor 4: Domain, Location & Remote Culture Alignment (0-1 point)',
        'Universal Job Retention: Non-matching jobs are preserved as low_score for future matching—never discarded!',
      ],
      command: 'applypilot match-jobs --re-score-all',
    },
    {
      id: 'marathon-looper',
      title: 'Continuous Marathon Looper & Dead Job Eviction',
      badge: 'Autonomous Cycling',
      badgeClass: 'bg-purple-50 text-purple-800 border-purple-200/80',
      icon: Repeat,
      iconClass: 'bg-purple-500/10 text-purple-700 border-purple-200',
      description:
        'Sustained multi-loop orchestration running indefinitely with automated health monitoring and dead listing eviction.',
      highlights: [
        'Automated Dead Job Eviction: Checks HTTP 404/410 and Closed Job signals to clean stale postings',
        'Dynamic Backoff & Jitter: Prevents rate-limits on career sites through intelligent staggered polling',
        'State Transitions Engine: Moves jobs through discovered -> enriching -> scored -> applied with audit logs',
        'Priority Watchlist Ordering: Discovers high-priority Tier 1 and VIP companies first',
      ],
      command: 'applypilot marathon --continuous --concurrency 3',
    },
    {
      id: 'email-harvester',
      title: '100% Free B2B Email Harvester',
      badge: 'Zero Paid API Credits',
      badgeClass: 'bg-amber-50 text-amber-800 border-amber-200/80',
      icon: Mail,
      iconClass: 'bg-amber-500/10 text-amber-700 border-amber-200',
      description:
        'Discovers direct recruiter and hiring manager emails without requiring Apollo, Hunter, or ZoomInfo subscriptions.',
      highlights: [
        'Cascade Waterfall 1: Free GitHub Commit Log Harvester (public author emails for tech leads)',
        'Cascade Waterfall 2: Security.txt, RFC 9116 & Website Contact DOM Parsers',
        'Cascade Waterfall 3: Deterministic MX Pattern Synthesizer ({first}.{last}@{domain}) with DNS MX validation',
        'Strict RFC Email Syntax Validation with disposables and catch-all discard filter',
      ],
      command: 'applypilot drill-emails --all-companies',
    },
    {
      id: 'hitl-gate',
      title: 'Admin Human-in-the-Loop (HITL) Gate',
      badge: 'Full Human Control',
      badgeClass: 'bg-rose-50 text-rose-800 border-rose-200/80',
      icon: ShieldCheck,
      iconClass: 'bg-rose-500/10 text-rose-700 border-rose-200',
      description:
        'Protects your professional reputation by requiring explicit human review and approval before any cold email is dispatched.',
      highlights: [
        'Dual-State Quarantine: Discovered leads enter pending_review state automatically',
        'Full Preview & Inline Edit: Inspect recipient, subject, and personalized body pitch before dispatching',
        'Screening Blocker Intervention: Halts auto-applications when unhandled custom screening questions appear',
        'Audit Logging: Logs exact timestamp, approver, and email response headers for every contact',
      ],
      command: 'applypilot leads --pending-review',
    },
    {
      id: 'dual-attack',
      title: 'Autonomous Dual-Attack Orchestration',
      badge: '2x Interview Rate',
      badgeClass: 'bg-indigo-50 text-indigo-800 border-indigo-200/80',
      icon: Zap,
      iconClass: 'bg-indigo-500/10 text-indigo-700 border-indigo-200',
      description:
        'Executes synchronized portal submissions and direct warm recruiter outreach in parallel for Tier 1 roles.',
      highlights: [
        'Vector 1 (Official ATS Portal): Automated headless application submission with customized resume',
        'Vector 2 (Direct Recruiter Outreach): Warm, personalized email dispatched to verified Hiring Manager',
        'Unified Tracking: Tracks application submission ID and recruiter thread response in single dashboard view',
        'Automatic State Sync: Updates job status from discovered to applied seamlessly',
      ],
      command: 'applypilot apply --workers 2',
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Hero Banner - White Liquid Glass Elevated */}
      <div className="liquid-glass-elevated rounded-3xl p-6 sm:p-8 border border-white/95 shadow-md relative overflow-hidden">
        {/* Specular rim */}
        <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
        <div className="absolute -top-12 -right-12 w-80 h-80 bg-gradient-to-br from-cyan-200/30 via-indigo-200/20 to-transparent rounded-full blur-2xl pointer-events-none" />

        <div className="relative z-10 max-w-4xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold liquid-pill border border-white/95 text-zinc-800 shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
            ApplyPilot Core Architecture Blueprint
          </div>
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-zinc-900 tracking-tight">
            Autonomous Career Acceleration Engine
          </h1>
          <p className="text-zinc-600 text-sm sm:text-base leading-relaxed">
            ApplyPilot is engineered with 100% free, deterministic, and autonomous subsystems. It combines
            direct-to-source ATS harvesting, sub-millisecond zero-token local job matching, universal listing retention,
            free B2B email discovery, and a strict Human-in-the-Loop admin safety gate.
          </p>

          <div className="flex flex-wrap gap-3 pt-2">
            <div className="flex items-center gap-1.5 text-xs text-zinc-700 font-medium liquid-pill px-3 py-1 rounded-full shadow-2xs">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Zero External LLM Token Cost</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-zinc-700 font-medium liquid-pill px-3 py-1 rounded-full shadow-2xs">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Universal Job Retention (Never Lost)</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-zinc-700 font-medium liquid-pill px-3 py-1 rounded-full shadow-2xs">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>100% Free Email Harvesting</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-zinc-700 font-medium liquid-pill px-3 py-1 rounded-full shadow-2xs">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Admin HITL Email Approval Gate</span>
            </div>
          </div>
        </div>
      </div>

      {/* Engine Architecture Cards Grid - Frosted Liquid Glass */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {engines.map((eng) => {
          const IconComponent = eng.icon;
          return (
            <div
              key={eng.id}
              className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs hover:shadow-md transition-all duration-300 flex flex-col justify-between space-y-5 group relative overflow-hidden"
            >
              <div className="absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className={`p-2.5 rounded-2xl border ${eng.iconClass} group-hover:scale-105 transition-transform duration-200 shadow-2xs`}>
                    <IconComponent className="w-5 h-5" />
                  </div>
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${eng.badgeClass}`}>
                    {eng.badge}
                  </span>
                </div>

                <div>
                  <h3 className="text-base font-bold text-zinc-900 group-hover:text-cyan-700 transition-colors">
                    {eng.title}
                  </h3>
                  <p className="text-xs text-zinc-500 leading-relaxed mt-1.5">
                    {eng.description}
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-zinc-200/60">
                  <span className="text-[10.5px] font-bold uppercase tracking-wider text-zinc-400">
                    Engine Capabilities:
                  </span>
                  <ul className="space-y-1.5">
                    {eng.highlights.map((h, i) => (
                      <li key={i} className="text-xs text-zinc-700 flex items-start gap-2 leading-tight">
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 mt-1 shrink-0" />
                        <span>{h}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* CLI Command Box with Apple Obsidian Contrast */}
              <div className="pt-2">
                <div className="flex items-center justify-between bg-zinc-900 text-zinc-200 px-3 py-2 rounded-xl text-[11.5px] font-mono border border-zinc-800 shadow-inner group/cmd">
                  <div className="flex items-center gap-2 truncate min-w-0">
                    <Terminal className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                    <span className="truncate">{eng.command}</span>
                  </div>
                  <button
                    onClick={() => copyToClipboard(eng.command)}
                    title="Copy command"
                    className="p-1 hover:text-white text-zinc-400 transition ml-2 cursor-pointer shrink-0"
                  >
                    {copiedCommand === eng.command ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
