'use client';

import React from 'react';
import { Zap, ExternalLink, Mail, ShieldAlert } from 'lucide-react';
import { Tooltip } from './Tooltip';

interface RouteBadgeProps {
  route?: string | null;
  compact?: boolean;
  className?: string;
}

export function RouteBadge({ route, compact = false, className = '' }: RouteBadgeProps) {
  const r = (route || 'PORTAL_ONLY').toUpperCase();

  if (r === 'DUAL_ATTACK') {
    return (
      <Tooltip
        content={
          <div className="flex flex-col gap-1 max-w-[230px]">
            <div className="flex items-center gap-1.5 border-b border-rose-200/60 pb-1 font-semibold text-rose-800 text-xs">
              <Zap className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>Dual-Attack Strategy</span>
            </div>
            <p className="text-[11px] text-zinc-600 leading-snug">
              Simultaneously submits the official ATS application AND dispatches tailored outreach to verified recruiter inboxes citing the application ID.
            </p>
          </div>
        }
      >
        <span
          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200/70 shadow-xs cursor-help transition-all hover:bg-rose-100/70 ${className}`}
        >
          <Zap className="w-3 h-3 text-rose-600 shrink-0" />
          {!compact && <span>DUAL ATTACK</span>}
        </span>
      </Tooltip>
    );
  }

  if (r === 'EMAIL_ONLY') {
    return (
      <Tooltip
        content={
          <div className="flex flex-col gap-1 max-w-[230px]">
            <div className="flex items-center gap-1.5 border-b border-indigo-200/60 pb-1 font-semibold text-indigo-800 text-xs">
              <Mail className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              <span>Email Outreach Only</span>
            </div>
            <p className="text-[11px] text-zinc-600 leading-snug">
              Direct personalized pitch delivered to verified hiring manager or founder inbox (no public ATS portal detected).
            </p>
          </div>
        }
      >
        <span
          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200/70 shadow-xs cursor-help transition-all hover:bg-indigo-100/70 ${className}`}
        >
          <Mail className="w-3 h-3 text-indigo-600 shrink-0" />
          {!compact && <span>EMAIL ONLY</span>}
        </span>
      </Tooltip>
    );
  }

  return (
    <Tooltip
      content={
        <div className="flex flex-col gap-1 max-w-[230px]">
          <div className="flex items-center gap-1.5 border-b border-emerald-200/60 pb-1 font-semibold text-emerald-800 text-xs">
            <ExternalLink className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>Portal Application Only</span>
          </div>
          <p className="text-[11px] text-zinc-600 leading-snug">
            Official application submitted via employer ATS (Greenhouse, Ashby, etc.). No verified recruiter inboxes discovered.
          </p>
        </div>
      }
    >
      <span
        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/70 shadow-xs cursor-help transition-all hover:bg-emerald-100/70 ${className}`}
      >
        <ExternalLink className="w-3 h-3 text-emerald-600 shrink-0" />
        {!compact && <span>PORTAL</span>}
      </span>
    </Tooltip>
  );
}

