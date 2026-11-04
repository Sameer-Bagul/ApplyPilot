'use client';

import React, { useState } from 'react';
import { signIn } from 'next-auth/react';
import {
  ShieldCheck,
  Zap,
  Briefcase,
  Building2,
  Users,
  Compass,
  ArrowRight,
  Lock,
  KeyRound,
  Sparkles,
  Layers,
  Terminal,
  Activity,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Globe,
} from 'lucide-react';

interface LandingPageProps {
  error?: string | null;
}

export function LandingPage({ error: initialError }: LandingPageProps) {
  const [passcode, setPasscode] = useState('');
  const [email, setEmail] = useState('sameerbagul2004@gmail.com');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(initialError || null);

  const handleCredentialsLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passcode.trim()) {
      setError('Please enter the admin passcode.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await signIn('credentials', {
        passcode,
        email,
        redirect: false,
      });

      if (res?.error) {
        setError('Invalid passcode or unauthorized email. Access is strictly restricted.');
      } else if (res?.ok) {
        window.location.href = '/';
      }
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    setLoading(true);
    signIn('google', { callbackUrl: '/' });
  };

  return (
    <div className="min-h-screen flex flex-col justify-between p-4 sm:p-6 lg:p-10 max-w-7xl mx-auto selection:bg-rose-100 selection:text-rose-900">
      {/* Top Floating Glass Navigation */}
      <header className="liquid-glass rounded-3xl p-4 sm:px-6 sm:py-4 flex items-center justify-between shadow-sm relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full orb-peach shrink-0 flex items-center justify-center shadow-md relative">
            <div className="w-2.5 h-2.5 rounded-full bg-white/90 shadow-xs" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-xl tracking-tight text-zinc-950">ApplyPilot</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-rose-50 text-rose-800 border border-rose-200">
                Studio v2.0
              </span>
            </div>
            <p className="text-[11px] text-zinc-500 font-medium">Autonomous Career Acquisition & Intelligence</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="liquid-pill rounded-full px-3 py-1 flex items-center gap-2 text-xs font-semibold text-zinc-700 shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="hidden sm:inline">Turso Cloud Mumbai</span>
          </div>
          <div className="liquid-pill rounded-full px-3 py-1 flex items-center gap-1.5 text-xs font-semibold text-rose-700 bg-rose-50/50 border border-rose-200/80 shadow-2xs">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Restricted Access</span>
          </div>
        </div>
      </header>

      {/* Main Hero & Auth Split */}
      <main className="my-8 sm:my-12 lg:my-16 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
        {/* Left: Product Value Proposition & Metrics */}
        <div className="lg:col-span-7 space-y-6 sm:space-y-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/80 border border-white/90 shadow-2xs text-xs font-semibold text-zinc-800">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Multi-Agent Swarm • Headed Playwright Engine • 4-Factor Matching</span>
          </div>

          <div className="space-y-4">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-zinc-950 leading-[1.08]">
              Your Private Autonomous <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-zinc-950 via-zinc-800 to-rose-700">
                Career War Room.
              </span>
            </h1>
            <p className="text-base sm:text-lg text-zinc-600 font-normal leading-relaxed max-w-2xl">
              Continuous 24/7 omni-channel sweeping across LinkedIn, FreeHire, Greenhouse, Lever, and Ashby.
              Sub-20ms local deterministic matching, verified recruiter lead discovery, and automated headed browser application dispatch.
            </p>
          </div>

          {/* Live Data Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="liquid-glass rounded-2xl p-4 border border-white/90 shadow-2xs">
              <div className="text-2xl sm:text-3xl font-black text-zinc-900 tracking-tight">4,409+</div>
              <div className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider mt-0.5">Live Openings</div>
            </div>
            <div className="liquid-glass rounded-2xl p-4 border border-white/90 shadow-2xs">
              <div className="text-2xl sm:text-3xl font-black text-zinc-900 tracking-tight">927</div>
              <div className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider mt-0.5">Tracked Companies</div>
            </div>
            <div className="liquid-glass rounded-2xl p-4 border border-white/90 shadow-2xs">
              <div className="text-2xl sm:text-3xl font-black text-zinc-900 tracking-tight">1,284</div>
              <div className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider mt-0.5">Recruiter Leads</div>
            </div>
            <div className="liquid-glass rounded-2xl p-4 border border-white/90 shadow-2xs">
              <div className="text-2xl sm:text-3xl font-black text-emerald-700 tracking-tight">0 Tokens</div>
              <div className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider mt-0.5">Matcher Cost</div>
            </div>
          </div>

          {/* Architectural Pillars */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
            <div className="liquid-glass rounded-2xl p-3.5 flex items-start gap-3 border border-white/90 shadow-2xs">
              <div className="p-2 rounded-xl bg-blue-50 text-blue-700 border border-blue-200/60 shrink-0">
                <Briefcase className="w-4 h-4" />
              </div>
              <div className="space-y-0.5">
                <h3 className="text-xs font-bold text-zinc-900">Dual-Attack Execution</h3>
                <p className="text-[11px] text-zinc-500 leading-snug">
                  Simultaneously auto-fills portal forms and drafts personalized cold outreach to talent partners.
                </p>
              </div>
            </div>

            <div className="liquid-glass rounded-2xl p-3.5 flex items-start gap-3 border border-white/90 shadow-2xs">
              <div className="p-2 rounded-xl bg-purple-50 text-purple-700 border border-purple-200/60 shrink-0">
                <Terminal className="w-4 h-4" />
              </div>
              <div className="space-y-0.5">
                <h3 className="text-xs font-bold text-zinc-900">Headed Playwright Browser</h3>
                <p className="text-[11px] text-zinc-500 leading-snug">
                  Launches real visible browsers with Human-in-the-Loop checkpoints for CAPTCHAs and custom questions.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Liquid Glass Auth Card */}
        <div className="lg:col-span-5 flex justify-center">
          <div className="w-full max-w-md liquid-glass-elevated rounded-3xl p-6 sm:p-8 border border-white/90 shadow-xl relative overflow-hidden">
            {/* Top specular glow */}
            <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none" />

            <div className="space-y-5">
              <div className="space-y-1.5 text-center sm:text-left">
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-100 text-zinc-700 text-[11px] font-bold">
                  <Lock className="w-3.5 h-3.5 text-rose-600" />
                  <span>Authorized Personnel Only</span>
                </div>
                <h2 className="text-2xl font-black text-zinc-950 tracking-tight">Access Mission Control</h2>
                <p className="text-xs text-zinc-500">
                  Private workspace protected by whitelist authentication.
                </p>
              </div>

              {/* Error Banner */}
              {error && (
                <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 flex items-start gap-2.5 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
                  <div className="leading-snug">{error}</div>
                </div>
              )}

              {/* Google OAuth Button */}
              <button
                onClick={handleGoogleLogin}
                disabled={loading}
                className="w-full liquid-glass rounded-2xl py-3 px-4 flex items-center justify-center gap-3 font-bold text-xs text-zinc-900 hover:bg-white transition-all shadow-xs hover:shadow-md cursor-pointer border border-white/90 active:scale-[0.98]"
              >
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Sign in with Google</span>
              </button>

              <div className="relative flex py-1 items-center">
                <div className="flex-grow border-t border-zinc-200/80"></div>
                <span className="flex-shrink mx-3 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                  or Admin Passcode
                </span>
                <div className="flex-grow border-t border-zinc-200/80"></div>
              </div>

              {/* Passcode Unlock Form */}
              <form onSubmit={handleCredentialsLogin} className="space-y-3.5">
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider block">
                    Account Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="sameerbagul2004@gmail.com"
                    required
                    className="w-full text-xs font-medium px-3.5 py-2.5 rounded-xl bg-white/70 border border-zinc-200/80 focus:outline-none focus:ring-2 focus:ring-zinc-950/20 text-zinc-900 transition"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider block">
                    Admin Passcode
                  </label>
                  <div className="relative">
                    <input
                      type="password"
                      value={passcode}
                      onChange={(e) => setPasscode(e.target.value)}
                      placeholder="Enter admin passcode"
                      required
                      className="w-full text-xs font-medium pl-3.5 pr-10 py-2.5 rounded-xl bg-white/70 border border-zinc-200/80 focus:outline-none focus:ring-2 focus:ring-zinc-950/20 text-zinc-900 transition"
                    />
                    <KeyRound className="w-4 h-4 text-zinc-400 absolute right-3 top-3 pointer-events-none" />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full liquid-pill rounded-xl py-2.5 px-4 bg-zinc-950 text-white font-bold text-xs flex items-center justify-center gap-2 hover:bg-zinc-800 active:scale-[0.98] transition cursor-pointer shadow-md disabled:opacity-50"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Authenticating...
                    </span>
                  ) : (
                    <>
                      <span>Unlock Mission Control</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </form>

              {/* Whitelist Security Notice */}
              <div className="p-3 rounded-2xl bg-zinc-50 border border-zinc-200/70 text-[11px] text-zinc-500 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-zinc-700">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Whitelisted Account Guarantee</span>
                </div>
                <p>
                  Personal data, resume knowledge graphs, and outbound email dispatching are strictly restricted to{' '}
                  <span className="font-semibold text-zinc-800">sameerbagul2004@gmail.com</span>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="liquid-glass rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between text-[11px] text-zinc-500 gap-3 border border-white/90">
        <div>
          ApplyPilot • Designed for Sameer Bagul. Powered by Turso Cloud, Next.js 16 & Playwright.
        </div>
        <div className="flex items-center gap-4 font-semibold">
          <span className="flex items-center gap-1 text-emerald-700">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Turso DB Online (Mumbai)
          </span>
          <span className="text-zinc-400">•</span>
          <span>Dual-Attack Auto Apply</span>
        </div>
      </footer>
    </div>
  );
}
