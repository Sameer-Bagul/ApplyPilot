'use client';

import React, { useState } from 'react';
import { Play, CheckCircle2, ShieldAlert, AlertCircle, Loader2, Monitor } from 'lucide-react';

interface AutoApplyButtonProps {
  jobUrl: string;
  initialState?: string;
  onApplied?: () => void;
  onOpenTicket?: (ticketId: number) => void;
  size?: 'sm' | 'md';
}

export function AutoApplyButton({
  jobUrl,
  initialState,
  onApplied,
  onOpenTicket,
  size = 'sm',
}: AutoApplyButtonProps) {
  const isAlreadyApplied = initialState === 'applied';
  const [status, setStatus] = useState<'idle' | 'applying' | 'applied' | 'ticket' | 'error'>(
    isAlreadyApplied ? 'applied' : 'idle'
  );
  const [ticketId, setTicketId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleAutoApply = async (e: React.MouseEvent) => {
    e.stopPropagation();

    // If there's an active ticket, open it
    if (status === 'ticket' && ticketId && onOpenTicket) {
      onOpenTicket(ticketId);
      return;
    }

    if (status === 'applying' || status === 'applied') return;

    setStatus('applying');
    setErrorMessage(null);

    try {
      const res = await fetch('/api/apply/job', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jobUrl,
          mode: 'headed',
          headless: false,
        }),
      });

      const json = await res.json();

      if (json.success) {
        if (json.ticket_id || json.status === 'needs_human') {
          setStatus('ticket');
          setTicketId(json.ticket_id || 1);
        } else if (json.status === 'applied') {
          setStatus('applied');
          if (onApplied) onApplied();
        } else {
          // Running / launched headed browser
          setStatus('applied');
          if (onApplied) onApplied();
        }
      } else {
        if (json.ticket_id) {
          setStatus('ticket');
          setTicketId(json.ticket_id);
        } else {
          setStatus('error');
          setErrorMessage(json.error || 'Apply failed');
          setTimeout(() => setStatus('idle'), 4000);
        }
      }
    } catch (err: any) {
      setStatus('error');
      setErrorMessage(err.message || 'Network error');
      setTimeout(() => setStatus('idle'), 4000);
    }
  };

  const padClass = size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3.5 py-1.5 text-xs';

  if (status === 'applying') {
    return (
      <button
        type="button"
        onClick={(e) => e.stopPropagation()}
        disabled
        className={`${padClass} rounded-xl font-semibold bg-cyan-50 border border-cyan-300 text-cyan-900 flex items-center gap-1.5 shadow-2xs animate-pulse cursor-wait shrink-0`}
        title="Launching visible browser window to auto-apply from your credentials"
      >
        <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-700" />
        <span>Launching Browser...</span>
      </button>
    );
  }

  if (status === 'applied') {
    return (
      <span
        onClick={(e) => e.stopPropagation()}
        className={`${padClass} rounded-xl font-bold bg-emerald-50 border border-emerald-300 text-emerald-800 flex items-center gap-1.5 shadow-2xs shrink-0`}
      >
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
        <span>Applied</span>
      </span>
    );
  }

  if (status === 'ticket') {
    return (
      <button
        type="button"
        onClick={handleAutoApply}
        className={`${padClass} rounded-xl font-bold bg-amber-500 hover:bg-amber-600 text-white border border-amber-600 flex items-center gap-1.5 shadow-xs transition cursor-pointer shrink-0 animate-bounce-subtle`}
        title="Blocked on screening question. Click to answer."
      >
        <ShieldAlert className="w-3.5 h-3.5" />
        <span>Review Ticket {ticketId ? `#${ticketId}` : ''}</span>
      </button>
    );
  }

  if (status === 'error') {
    return (
      <button
        type="button"
        onClick={handleAutoApply}
        className={`${padClass} rounded-xl font-medium bg-rose-50 border border-rose-300 text-rose-800 flex items-center gap-1.5 shadow-2xs shrink-0 cursor-pointer`}
        title={errorMessage || 'Click to retry'}
      >
        <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
        <span>Retry Apply</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleAutoApply}
      className={`liquid-pill ${padClass} rounded-xl font-semibold text-zinc-800 hover:text-cyan-900 hover:border-cyan-300 flex items-center gap-1.5 shadow-2xs group transition cursor-pointer shrink-0 bg-white/90 hover:bg-cyan-50/60`}
      title="Launch visible desktop browser and auto-fill form using your candidate profile & resume"
    >
      <Monitor className="w-3.5 h-3.5 text-cyan-600 group-hover:scale-110 transition shrink-0" />
      <span>Auto Apply</span>
    </button>
  );
}
