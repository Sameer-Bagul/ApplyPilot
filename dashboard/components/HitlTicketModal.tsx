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
  Sparkles,
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
  const [solvingCaptcha, setSolvingCaptcha] = useState(false);
  const [saveToKb, setSaveToKb] = useState(true);

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

  const isReviewOnly =
    ticket?.blocker_type === 'review' ||
    (ticket?.questions &&
      ticket.questions.length > 0 &&
      ticket.questions.every(
        (q: any) =>
          q.field_type === 'submit' ||
          q.type === 'submit' ||
          q.label?.toLowerCase().includes('submission review') ||
          q.label?.toLowerCase().includes('form fields filled')
      ));

  const handleFieldChange = (fieldId: string, val: string) => {
    setAnswers((prev) => ({ ...prev, [fieldId]: val }));
  };

  const handleSolveCaptcha = async () => {
    setSolvingCaptcha(true);
    try {
      const res = await fetch('/api/hitl/solve-captcha', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticketId, auto_submit: true }),
      });
      const json = await res.json();
      if (json.success) {
        if (onTicketResolved) onTicketResolved();
        onClose();
      } else {
        alert(json.error || 'Failed to complete CAPTCHA resolution.');
      }
    } catch (err: any) {
      alert(err.message || 'Error triggering CAPTCHA resolution.');
    } finally {
      setSolvingCaptcha(false);
    }
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
          save_to_qa_knowledge: saveToKb,
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
                isReviewOnly ? 'bg-cyan-50 text-cyan-800 border-cyan-200' :
                'bg-amber-50 text-amber-800 border-amber-200'
              }`}>
                {ticket?.status === 'resolved' ? 'Resolved' : isReviewOnly ? 'Final Review' : 'Requires Intervention'}
              </span>
              <span className="text-xs text-zinc-500 font-mono">Ticket #{ticketId}</span>
            </div>
            <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 truncate">
              {isReviewOnly ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              ) : (
                <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />
              )}
              <span>{ticket?.role_title || (isReviewOnly ? 'Final Submission Review' : 'Application Blocker / Screening')}</span>
            </h2>
            <div className="text-xs text-zinc-500 flex items-center gap-2">
              <Building2 className="w-3.5 h-3.5 text-cyan-600" />
              <span className="font-semibold text-zinc-800">{ticket?.company || 'Company'}</span>
              <span>•</span>
              <span className="font-mono text-zinc-600">{isReviewOnly ? 'submission_review' : ticket?.blocker_type || 'screening_question'}</span>
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
              {ticket.blocker_type === 'captcha' ? (
                <div className="space-y-4">
                  <div className="liquid-glass-elevated rounded-2xl p-5 border border-amber-200/90 bg-amber-50/50 shadow-xs space-y-3">
                    <div className="flex items-center gap-2 text-amber-800 font-bold text-sm">
                      <ShieldAlert className="w-5 h-5 text-amber-600" />
                      <span>Security Challenge / CAPTCHA Flagged</span>
                    </div>
                    <p className="text-xs text-zinc-700 leading-relaxed">
                      This job application hit an anti-bot gate or verification challenge (e.g. Cloudflare Turnstile, Google reCAPTCHA, or puzzle).
                      ApplyPilot quarantined it here so you and the app can work together to resolve it seamlessly.
                    </p>
                    <div className="p-3 bg-white/80 rounded-xl border border-amber-200/60 text-xs text-zinc-600 space-y-1.5">
                      <div className="font-semibold text-zinc-800 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
                        <span>Collaborative Resolution Flow:</span>
                      </div>
                      <div>1. Click below to launch the headed browser directly onto your desktop.</div>
                      <div>2. ApplyPilot plays an audible alert chime and highlights the challenge.</div>
                      <div>3. You solve the CAPTCHA directly in the window.</div>
                      <div>4. ApplyPilot auto-detects resolution, chimes success, submits, and marks this ticket resolved!</div>
                    </div>
                  </div>

                  <div className="flex justify-center pt-2">
                    <button
                      type="button"
                      disabled={solvingCaptcha}
                      onClick={handleSolveCaptcha}
                      className="liquid-pill-dark px-6 py-3 rounded-2xl text-xs font-bold flex items-center gap-2 shadow-md cursor-pointer transition hover:scale-[1.02] disabled:opacity-50"
                    >
                      <Sparkles className="w-4 h-4 text-cyan-300" />
                      <span>{solvingCaptcha ? 'Browser Active on Screen (Listening...)' : 'Solve with App (Launch Headed Browser)'}</span>
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {isReviewOnly ? (
                    <div className="p-3.5 rounded-2xl bg-emerald-50/80 border border-emerald-200/80 text-xs text-emerald-900 shadow-2xs flex items-start gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold block text-emerald-950">All Form Fields Filled from Profile</span>
                        No screening questions are missing. ApplyPilot auto-filled your credentials and attached your resume. The application was paused for candidate confirmation.
                      </div>
                    </div>
                  ) : (
                    <div className="p-3.5 rounded-2xl bg-blue-50/80 border border-blue-200/80 text-xs text-blue-900 shadow-2xs">
                      This job application has required screening questions not yet present in your profile. Provide answers below, and ApplyPilot will auto-learn them into your Q&A knowledge base!
                    </div>
                  )}

                  {/* Questions list */}
                  <div className="space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                      {isReviewOnly ? 'Submission Review Checkpoint' : `Unanswered Form Questions (${ticket.questions?.length || 0})`}
                    </h3>

                    {ticket.questions && ticket.questions.length > 0 ? (
                      ticket.questions.map((q: any, idx: number) => {
                        const fieldKey = q.field_id || q.label || `q_${idx}`;
                        const isReviewCheckpoint =
                          q.field_type === 'submit' ||
                          q.type === 'submit' ||
                          q.label?.toLowerCase().includes('submission review') ||
                          q.label?.toLowerCase().includes('form fields filled');

                        if (isReviewCheckpoint) {
                          return (
                            <div key={idx} className="liquid-glass rounded-2xl p-4 border border-emerald-200/90 bg-emerald-50/40 shadow-2xs space-y-2.5">
                              <div className="flex items-center gap-2 text-xs font-bold text-emerald-800">
                                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                                <span>All Profile Fields & Resume Pre-Filled</span>
                              </div>
                              <p className="text-[11px] text-zinc-600 leading-relaxed">
                                No questions are missing. ApplyPilot filled your name, email, contact details, and resume. The application was paused for your final visual review before submission (because review mode is enabled in your profile).
                              </p>
                              <div className="pt-1">
                                <button
                                  type="button"
                                  onClick={handleSolveCaptcha}
                                  disabled={solvingCaptcha}
                                  className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs hover:scale-[1.01] transition"
                                >
                                  <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                                  <span>{solvingCaptcha ? 'Opening Browser...' : 'Open Headed Browser & Submit'}</span>
                                </button>
                              </div>
                            </div>
                          );
                        }

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
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 px-6 border-t border-zinc-200/70 bg-zinc-50/70 flex items-center justify-between gap-3">
          <button
            onClick={() => handleResolve('dismissed')}
            disabled={resolving || solvingCaptcha}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold text-zinc-600 hover:text-zinc-950 transition cursor-pointer"
          >
            Dismiss Ticket
          </button>

          <div className="flex items-center gap-3">
            {ticket?.blocker_type !== 'captcha' && !isReviewOnly && (
              <label className="flex items-center gap-2 text-xs text-zinc-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={saveToKb}
                  onChange={(e) => setSaveToKb(e.target.checked)}
                  className="rounded border-zinc-300 text-purple-600 focus:ring-purple-400 cursor-pointer"
                />
                <span>Auto-learn into Q&A Knowledge Base</span>
              </label>
            )}

            <button
              onClick={onClose}
              className="liquid-pill px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer shadow-2xs"
            >
              Close
            </button>
            {isReviewOnly ? (
              <button
                type="button"
                onClick={handleSolveCaptcha}
                disabled={solvingCaptcha}
                className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs hover:scale-[1.01] transition"
              >
                <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                <span>{solvingCaptcha ? 'Opening Browser & Submitting...' : 'Open Browser & Submit Now'}</span>
              </button>
            ) : ticket?.blocker_type !== 'captcha' ? (
              <button
                onClick={() => handleResolve('resolved')}
                disabled={resolving}
                className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>{resolving ? 'Submitting...' : 'Save & Resume Pipeline'}</span>
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
