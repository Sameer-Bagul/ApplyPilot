'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  ShieldAlert,
  CheckCircle2,
  Trash2,
  Save,
  HelpCircle,
  Building2,
  ExternalLink,
  Send,
  Check,
} from 'lucide-react';

interface HitlTicketModalProps {
  ticketId: number | null;
  onClose: () => void;
  onTicketResolved?: () => void;
}

export function HitlTicketModal({
  ticketId,
  onClose,
  onTicketResolved,
}: HitlTicketModalProps) {
  const [loading, setLoading] = useState(false);
  const [ticket, setTicket] = useState<any | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    if (!ticketId) {
      setTicket(null);
      return;
    }

    const fetchTicket = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/hitl/detail?id=${ticketId}`);
        const json = await res.json();
        if (json.success) {
          setTicket(json.ticket);
          const initial: Record<string, string> = {};
          (json.ticket.questions || []).forEach((q: any) => {
            initial[q.field_id || q.label] = q.suggested_draft || q.options?.[0] || '';
          });
          setAnswers(initial);
        }
      } catch (err) {
        console.error('Failed to load ticket detail', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTicket();
  }, [ticketId]);

  if (!ticketId) return null;

  const handleFieldChange = (fieldId: string, val: string) => {
    setAnswers((prev) => ({ ...prev, [fieldId]: val }));
  };

  const handleResolve = async (action: 'resolved' | 'dismissed') => {
    setResolving(true);
    try {
      const res = await fetch(`/api/hitl/detail?id=${ticketId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          answers,
          resolved_by: 'admin_dashboard',
        }),
      });
      const json = await res.json();
      if (json.success) {
        if (onTicketResolved) onTicketResolved();
        onClose();
      }
    } catch (err) {
      console.error('Failed to resolve ticket', err);
    } finally {
      setResolving(false);
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 overflow-hidden bg-slate-900/25 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl max-h-[90vh] liquid-glass-elevated bg-white/95 backdrop-blur-2xl border border-white/95 rounded-3xl shadow-2xl overflow-hidden flex flex-col relative text-zinc-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-zinc-200/70 bg-white/70 flex items-start justify-between gap-4 relative">
          <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />

          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                ticket?.status === 'resolved' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                'bg-amber-50 text-amber-800 border-amber-200'
              }`}>
                {ticket?.status === 'resolved' ? 'Resolved' : 'Requires Intervention'}
              </span>
              <span className="text-xs text-zinc-500 font-mono">Ticket #{ticketId}</span>
            </div>
            <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 truncate">
              <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />
              <span>{ticket?.role_title || 'Application Blocker / Screening'}</span>
            </h2>
            <div className="text-xs text-zinc-500 flex items-center gap-2">
              <Building2 className="w-3.5 h-3.5 text-cyan-600" />
              <span className="font-semibold text-zinc-800">{ticket?.company || 'Company'}</span>
              <span>•</span>
              <span className="font-mono text-zinc-600">{ticket?.blocker_type || 'screening_question'}</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="liquid-pill rounded-full p-2 text-zinc-600 hover:text-zinc-950 transition shadow-2xs"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {loading ? (
            <div className="py-12 text-center text-sm text-zinc-400">Loading screening questions...</div>
          ) : !ticket ? (
            <div className="py-12 text-center text-sm text-zinc-500">Ticket not found.</div>
          ) : (
            <>
              <div className="p-3.5 rounded-2xl bg-amber-50/80 border border-amber-200/80 text-xs text-amber-900 shadow-2xs">
                The autonomous runner encountered an application barrier or screening question requiring human confirmation before proceeding.
              </div>

              {/* Questions list */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                  Unanswered Form Questions ({ticket.questions?.length || 0})
                </h3>

                {ticket.questions && ticket.questions.length > 0 ? (
                  ticket.questions.map((q: any, idx: number) => {
                    const fieldKey = q.field_id || q.label || `q_${idx}`;
                    return (
                      <div key={idx} className="liquid-glass rounded-2xl p-4 border border-white/90 shadow-2xs space-y-2">
                        <label className="text-xs font-semibold text-zinc-800 block">
                          {q.label || `Question ${idx + 1}`}
                          {q.required && <span className="text-rose-500 ml-1">*</span>}
                        </label>

                        {q.help_text && (
                          <p className="text-[11px] text-zinc-500 leading-tight">{q.help_text}</p>
                        )}

                        {q.type === 'select' && q.options ? (
                          <select
                            value={answers[fieldKey] || ''}
                            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
                            className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                          >
                            <option value="">Select an option...</option>
                            {q.options.map((opt: string, i: number) => (
                              <option key={i} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        ) : q.type === 'textarea' ? (
                          <textarea
                            rows={3}
                            value={answers[fieldKey] || ''}
                            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
                            placeholder="Provide answer or explanation..."
                            className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                          />
                        ) : (
                          <input
                            type="text"
                            value={answers[fieldKey] || ''}
                            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
                            placeholder="Enter response..."
                            className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                          />
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="py-6 text-center text-xs text-zinc-500">
                    No custom questionnaire fields detected. Generic application checkpoint.
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 px-6 border-t border-zinc-200/70 bg-zinc-50/70 flex items-center justify-between gap-3">
          <button
            onClick={() => handleResolve('dismissed')}
            disabled={resolving}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold text-zinc-600 hover:text-zinc-950 transition cursor-pointer"
          >
            Dismiss Ticket
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="liquid-pill px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer shadow-2xs"
            >
              Cancel
            </button>
            <button
              onClick={() => handleResolve('resolved')}
              disabled={resolving}
              className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>{resolving ? 'Submitting...' : 'Save & Resume Pipeline'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
