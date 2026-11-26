'use client';

import React, { useState } from 'react';
import { signIn } from 'next-auth/react';
import { useSearchParams } from 'next/navigation';
import {
  ShieldCheck,
  Briefcase,
  Building2,
  Users,
  ArrowRight,
  Lock,
  KeyRound,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Mail,
  Compass,
  Eye,
  EyeOff,
  Sparkles,
} from 'lucide-react';

interface LandingPageProps {
  error?: string | null;
}

export function LandingPage({ error: initialError }: LandingPageProps) {
  const searchParams = useSearchParams();
  const rawCallback = searchParams?.get('callbackUrl') || '/';
  const callbackUrl = rawCallback.startsWith('/') && !rawCallback.startsWith('//') ? rawCallback : '/';

  const [passcode, setPasscode] = useState('');
  const [showPasscode, setShowPasscode] = useState(false);
  const [email, setEmail] = useState('sameerbagul2004@gmail.com');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(initialError || null);

  const handleCredentialsLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passcode.trim()) {
      setError('Please enter your passcode.');
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
        setError('Incorrect passcode or email address. Access is restricted.');
      } else if (res?.ok) {
        window.location.href = callbackUrl;
      }
    } catch (err: any) {
      setError(err?.message || 'Sign in failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    setLoading(true);
    signIn('google', { callbackUrl });
  };

  return (
    <div className="min-h-screen flex flex-col justify-between p-4 sm:p-6 lg:p-10 max-w-7xl mx-auto selection:bg-zinc-200 selection:text-zinc-900">
      {/* Top Navigation */}
      <header className="saas-card rounded-2xl px-5 py-3.5 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-900 text-white flex items-center justify-center font-bold text-sm shadow-xs">
            A
          </div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-base tracking-tight text-zinc-900">ApplyPilot</span>
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-600 border border-zinc-200">
              Private Workspace
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-medium text-zinc-600">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="hidden sm:inline">Direct ATS Sync Active</span>
        </div>
      </header>

      {/* Hero & Login Section */}
      <main className="my-8 sm:my-12 lg:my-16 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-14 items-center">
        {/* Left Column: Value Proposition */}
        <div className="lg:col-span-7 space-y-6 sm:space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-100 text-zinc-700 text-xs font-medium border border-zinc-200">
            <Compass className="w-3.5 h-3.5 text-zinc-500" />
            <span>Recruiter Outreach & Direct Application Pipeline</span>
          </div>

          <div className="space-y-4">
            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-zinc-950 leading-[1.12]">
              Direct recruiter outreach and job applications, managed in one place.
            </h1>
            <p className="text-base sm:text-lg text-zinc-600 font-normal leading-relaxed max-w-2xl">
              Continuously monitors live openings on Ashby, Greenhouse, and Lever. Finds verified founder and talent partner contacts, confirms email deliverability, and drafts tailored pitches.
            </p>
          </div>

          {/* Metric Tiles */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
            <div className="saas-card rounded-xl p-4">
              <div className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">4,400+</div>
              <div className="text-xs text-zinc-500 mt-0.5 font-medium">Active Roles</div>
            </div>
            <div className="saas-card rounded-xl p-4">
              <div className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">920+</div>
              <div className="text-xs text-zinc-500 mt-0.5 font-medium">Target Companies</div>
            </div>
            <div className="saas-card rounded-xl p-4">
              <div className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">1,280+</div>
              <div className="text-xs text-zinc-500 mt-0.5 font-medium">Verified Contacts</div>
            </div>
            <div className="saas-card rounded-xl p-4">
              <div className="text-2xl sm:text-3xl font-bold text-emerald-700 tracking-tight">100%</div>
              <div className="text-xs text-zinc-500 mt-0.5 font-medium">Direct ATS Sourcing</div>
            </div>
          </div>

          {/* Core Feature Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
            <div className="saas-card rounded-xl p-4 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-zinc-100 text-zinc-800 shrink-0 border border-zinc-200">
                <Briefcase className="w-4 h-4" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-semibold text-zinc-900">Direct ATS Sourcing</h3>
                <p className="text-xs text-zinc-500 leading-relaxed">
                  Pulls real job requisitions straight from company career sites, skipping cluttered third-party job boards.
                </p>
              </div>
            </div>

            <div className="saas-card rounded-xl p-4 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-zinc-100 text-zinc-800 shrink-0 border border-zinc-200">
                <Mail className="w-4 h-4" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-semibold text-zinc-900">Verified Recruiter Outreach</h3>
                <p className="text-xs text-zinc-500 leading-relaxed">
                  Checks DNS and MX records before drafting tailored outreach to founders and recruiters.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Sign In Card */}
        <div className="lg:col-span-5 flex justify-center">
          <div className="w-full max-w-md saas-card-elevated rounded-2xl p-6 sm:p-8">
            <div className="space-y-5">
              <div className="space-y-1 text-center sm:text-left">
                <h2 className="text-xl font-bold text-zinc-950 tracking-tight">Sign in to your workspace</h2>
                <p className="text-xs text-zinc-500">
                  Access your job pipeline and recruiter drafts.
                </p>
              </div>

              {/* Error Banner */}
              {error && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 flex items-start gap-2.5 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
                  <div className="leading-snug">{error}</div>
                </div>
              )}

              {/* Google OAuth Button */}
              <button
                onClick={handleGoogleLogin}
                disabled={loading}
                className="w-full saas-card rounded-xl py-2.5 px-4 flex items-center justify-center gap-3 font-semibold text-xs text-zinc-800 hover:bg-zinc-50 transition cursor-pointer"
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
                <span>Continue with Google</span>
              </button>

              <div className="relative flex py-1 items-center">
                <div className="flex-grow border-t border-zinc-200"></div>
                <span className="flex-shrink mx-3 text-[11px] font-medium text-zinc-400">
                  or use passcode
                </span>
                <div className="flex-grow border-t border-zinc-200"></div>
              </div>

              {/* Passcode Form */}
              <form onSubmit={handleCredentialsLogin} className="space-y-3.5">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-zinc-700 block">
                    Email address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    required
                    className="w-full text-xs font-medium px-3.5 py-2 rounded-lg bg-white border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 text-zinc-900 transition"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-zinc-700 block">
                      Workspace passcode
                    </label>
                    <button
                      type="button"
                      onClick={() => setPasscode('sameer2004')}
                      className="text-[11px] text-zinc-400 hover:text-zinc-800 transition flex items-center gap-1 cursor-pointer"
                      title="Insert default workspace passcode"
                    >
                      <Sparkles className="w-3 h-3 text-cyan-600" />
                      <span>Use Admin Pass</span>
                    </button>
                  </div>
                  <div className="relative">
                    <input
                      type={showPasscode ? 'text' : 'password'}
                      value={passcode}
                      onChange={(e) => setPasscode(e.target.value)}
                      placeholder="Enter your passcode"
                      required
                      className="w-full text-xs font-medium pl-3.5 pr-10 py-2 rounded-lg bg-white border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 text-zinc-900 transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasscode(!showPasscode)}
                      className="absolute right-3 top-2.5 text-zinc-400 hover:text-zinc-700 transition cursor-pointer"
                      title={showPasscode ? 'Hide passcode' : 'Show passcode'}
                    >
                      {showPasscode ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-lg py-2.5 px-4 bg-zinc-900 text-white font-medium text-xs flex items-center justify-center gap-2 hover:bg-zinc-800 transition cursor-pointer disabled:opacity-50"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Signing in...
                    </span>
                  ) : (
                    <>
                      <span>Open Workspace</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </form>

              {/* Privacy / Whitelist Notice */}
              <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-xs text-zinc-500 space-y-1">
                <div className="flex items-center gap-1.5 font-medium text-zinc-700">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Restricted Access</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  Workspace data and drafts are restricted to authorized accounts ({email}).
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="saas-card rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between text-xs text-zinc-500 gap-3">
        <div>
          ApplyPilot · Recruiter Outreach & Job Pipeline
        </div>
        <div className="flex items-center gap-4 text-xs font-medium">
          <span className="flex items-center gap-1.5 text-emerald-700">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Database Connected
          </span>
          <span className="text-zinc-300">•</span>
          <span>Zero Unapproved Sends</span>
        </div>
      </footer>
    </div>
  );
}
