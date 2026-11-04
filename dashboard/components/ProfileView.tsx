'use client';

import React, { useState, useEffect } from 'react';
import {
  User,
  Mail,
  Phone,
  MapPin,
  Building2,
  Briefcase,
  Globe,
  FileText,
  Upload,
  Check,
  Save,
  Plus,
  Trash2,
  HelpCircle,
  ShieldCheck,
  DollarSign,
  Sparkles,
  ExternalLink,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Search,
} from 'lucide-react';

export function ProfileView() {
  const [activeSubTab, setActiveSubTab] = useState<
    'identity' | 'auth' | 'compensation' | 'resume' | 'qa' | 'settings'
  >('identity');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  // Profile fields state
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [currentTitle, setCurrentTitle] = useState('');
  const [currentCompany, setCurrentCompany] = useState('');
  const [yearsExperience, setYearsExperience] = useState<number>(3);
  const [noticePeriod, setNoticePeriod] = useState('Immediate');

  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [country, setCountry] = useState('India');
  const [postalCode, setPostalCode] = useState('');

  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [portfolioUrl, setPortfolioUrl] = useState('');

  const [citizenship, setCitizenship] = useState('India');
  const [authorizedInTarget, setAuthorizedInTarget] = useState('Yes');
  const [requiresSponsorship, setRequiresSponsorship] = useState('No');
  const [securityClearance, setSecurityClearance] = useState('None');

  const [gender, setGender] = useState('Male');
  const [veteranStatus, setVeteranStatus] = useState('I am not a protected veteran');
  const [disabilityStatus, setDisabilityStatus] = useState('No, I do not have a disability');

  const [targetSalary, setTargetSalary] = useState('');
  const [minSalary, setMinSalary] = useState('');
  const [currency, setCurrency] = useState('INR');
  const [remotePreference, setRemotePreference] = useState('Remote / Hybrid');
  const [willingToRelocate, setWillingToRelocate] = useState('Yes');

  const [defaultApplyMode, setDefaultApplyMode] = useState<'headless' | 'headed'>('headless');
  const [autoSubmit, setAutoSubmit] = useState(false);

  const [summary, setSummary] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkillInput, setNewSkillInput] = useState('');

  const [hasResumeFile, setHasResumeFile] = useState(false);
  const [resumeFilename, setResumeFilename] = useState<string | null>(null);
  const [uploadingResume, setUploadingResume] = useState(false);

  // Q&A Knowledge Base State
  const [qaList, setQaList] = useState<any[]>([]);
  const [qaSearch, setQaSearch] = useState('');
  const [newQuestion, setNewQuestion] = useState('');
  const [newAnswer, setNewAnswer] = useState('');
  const [addingQa, setAddingQa] = useState(false);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/profile');
      const data = await res.json();
      if (data.success && data.profile) {
        const p = data.profile;
        setFirstName(p.first_name || '');
        setLastName(p.last_name || '');
        setEmail(p.email || '');
        setPhone(p.phone || '');
        setCurrentTitle(p.current_title || '');
        setCurrentCompany(p.current_company || '');
        setYearsExperience(p.years_of_experience || 3);
        setNoticePeriod(p.notice_period || 'Immediate');

        if (p.location) {
          setCity(p.location.city || '');
          setState(p.location.state || '');
          setCountry(p.location.country || 'India');
          setPostalCode(p.location.postal_code || '');
        }

        if (p.urls) {
          setLinkedinUrl(p.urls.linkedin || '');
          setGithubUrl(p.urls.github || '');
          setPortfolioUrl(p.urls.portfolio || '');
        }

        if (p.work_authorization) {
          setCitizenship(p.work_authorization.citizenship || 'India');
          setAuthorizedInTarget(p.work_authorization.authorized_in_target || 'Yes');
          setRequiresSponsorship(p.work_authorization.requires_sponsorship || 'No');
          setSecurityClearance(p.work_authorization.security_clearance || 'None');
        }

        if (p.eeo) {
          setGender(p.eeo.gender || 'Male');
          setVeteranStatus(p.eeo.veteran_status || 'I am not a protected veteran');
          setDisabilityStatus(p.eeo.disability_status || 'No, I do not have a disability');
        }

        if (p.compensation) {
          setTargetSalary(p.compensation.target_salary || '');
          setMinSalary(p.compensation.min_salary || '');
          setCurrency(p.compensation.currency || 'INR');
        }

        if (p.preferences) {
          setRemotePreference(p.preferences.remote_preference || 'Remote / Hybrid');
          setWillingToRelocate(p.preferences.willing_to_relocate || 'Yes');
          setDefaultApplyMode(p.preferences.default_apply_mode || 'headless');
          setAutoSubmit(p.preferences.auto_submit ?? false);
        }

        setSummary(p.summary || '');
        setResumeText(p.resume_text || '');
        setSkills(p.skills || []);

        setHasResumeFile(data.hasResume || false);
        setResumeFilename(data.resumePath ? data.resumePath.split('/').pop() : null);
      }
    } catch (err) {
      console.error('Failed to load candidate profile', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchQa = async () => {
    try {
      const res = await fetch('/api/profile/qa');
      const data = await res.json();
      if (data.success) {
        setQaList(data.list || []);
      }
    } catch (err) {
      console.error('Failed to load Q&A list', err);
    }
  };

  useEffect(() => {
    fetchProfile();
    fetchQa();
  }, []);

  const handleSaveProfile = async () => {
    setSaving(true);
    setSaveMessage(null);

    const payload = {
      first_name: firstName,
      last_name: lastName,
      name: `${firstName} ${lastName}`.trim(),
      email,
      phone,
      current_title: currentTitle,
      current_company: currentCompany,
      years_of_experience: yearsExperience,
      notice_period: noticePeriod,
      location: {
        city,
        state,
        country,
        postal_code: postalCode,
      },
      urls: {
        linkedin: linkedinUrl,
        github: githubUrl,
        portfolio: portfolioUrl,
      },
      work_authorization: {
        citizenship,
        authorized_in_target: authorizedInTarget,
        requires_sponsorship: requiresSponsorship,
        security_clearance: securityClearance,
      },
      eeo: {
        gender,
        veteran_status: veteranStatus,
        disability_status: disabilityStatus,
      },
      compensation: {
        target_salary: targetSalary,
        min_salary: minSalary,
        currency,
      },
      preferences: {
        remote_preference: remotePreference,
        willing_to_relocate: willingToRelocate,
        default_apply_mode: defaultApplyMode,
        auto_submit: autoSubmit,
      },
      summary,
      resume_text: resumeText,
      skills,
    };

    try {
      const res = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        setSaveMessage('Profile saved and synced for autonomous application form filling!');
        setTimeout(() => setSaveMessage(null), 3500);
      } else {
        setSaveMessage(`Save failed: ${data.error}`);
      }
    } catch (err: any) {
      setSaveMessage(`Save error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleResumeFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingResume(true);
    const fd = new FormData();
    fd.append('resume', file);

    try {
      const res = await fetch('/api/profile/resume', {
        method: 'POST',
        body: fd,
      });
      const data = await res.json();
      if (data.success) {
        setHasResumeFile(true);
        setResumeFilename(data.filename);
        setSaveMessage(`Resume uploaded and attached: ${data.filename}`);
        setTimeout(() => setSaveMessage(null), 3000);
      } else {
        alert(data.error || 'Failed to upload resume');
      }
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setUploadingResume(false);
    }
  };

  const handleAddSkill = () => {
    const s = newSkillInput.trim();
    if (s && !skills.includes(s)) {
      setSkills([...skills, s]);
      setNewSkillInput('');
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkills(skills.filter((s) => s !== skillToRemove));
  };

  const handleAddQa = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQuestion.trim() || !newAnswer.trim()) return;

    setAddingQa(true);
    try {
      const res = await fetch('/api/profile/qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_text: newQuestion.trim(),
          answer_text: newAnswer.trim(),
        }),
      });
      const data = await res.json();
      if (data.success) {
        setNewQuestion('');
        setNewAnswer('');
        fetchQa();
      }
    } catch (err) {
      console.error('Failed to add Q&A', err);
    } finally {
      setAddingQa(false);
    }
  };

  const handleDeleteQa = async (id: number) => {
    try {
      const res = await fetch(`/api/profile/qa?id=${id}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        setQaList(qaList.filter((item) => item.id !== id));
      }
    } catch (err) {
      console.error('Failed to delete Q&A', err);
    }
  };

  const filteredQaList = qaList.filter(
    (q) =>
      q.question_text?.toLowerCase().includes(qaSearch.toLowerCase()) ||
      q.answer_text?.toLowerCase().includes(qaSearch.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Hero Banner */}
      <div className="liquid-glass-elevated rounded-3xl p-6 sm:p-8 border border-white/95 shadow-md relative overflow-hidden bg-white/80">
        <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
        <div className="absolute -top-12 -right-12 w-80 h-80 bg-gradient-to-br from-purple-200/30 via-indigo-200/20 to-transparent rounded-full blur-2xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold liquid-pill border border-white/95 text-zinc-800 shadow-xs">
              <Sparkles className="w-3.5 h-3.5 text-purple-600" />
              Candidate Profile & Form-Filling Credentials
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-zinc-900 tracking-tight">
              Autonomous Application Persona
            </h1>
            <p className="text-xs sm:text-sm text-zinc-600 leading-relaxed">
              Feed your personal identity, contact links, resume document, and verified answers to custom screening questions.
              This single source of truth powers both <strong>Headless background applications</strong> and <strong>Headed interactive browser sessions</strong>.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={handleSaveProfile}
              disabled={saving}
              className="liquid-pill-dark px-5 py-2.5 rounded-2xl text-xs font-semibold flex items-center gap-2 cursor-pointer shadow-md"
            >
              <Save className="w-4 h-4 text-emerald-400" />
              <span>{saving ? 'Saving...' : 'Save Profile'}</span>
            </button>
          </div>
        </div>

        {saveMessage && (
          <div className="mt-4 p-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 font-semibold shadow-2xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{saveMessage}</span>
          </div>
        )}
      </div>

      {/* Sub-Tabs Navigation Bar */}
      <div className="liquid-glass rounded-3xl p-2 sm:p-2.5 border border-white/90 shadow-xs flex items-center gap-1.5 overflow-x-auto">
        <button
          onClick={() => setActiveSubTab('identity')}
          className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all cursor-pointer whitespace-nowrap flex items-center gap-2 ${
            activeSubTab === 'identity'
              ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
              : 'text-zinc-600 hover:text-zinc-950'
          }`}
        >
          <User className="w-3.5 h-3.5 text-blue-600" />
          <span>Identity & Links</span>
        </button>

        <button
          onClick={() => setActiveSubTab('auth')}
          className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all cursor-pointer whitespace-nowrap flex items-center gap-2 ${
            activeSubTab === 'auth'
              ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
              : 'text-zinc-600 hover:text-zinc-950'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Work Authorization & EEO</span>
        </button>

        <button
          onClick={() => setActiveSubTab('compensation')}
          className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all cursor-pointer whitespace-nowrap flex items-center gap-2 ${
            activeSubTab === 'compensation'
              ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
              : 'text-zinc-600 hover:text-zinc-950'
          }`}
        >
          <DollarSign className="w-3.5 h-3.5 text-amber-600" />
          <span>Compensation & Preferences</span>
        </button>

        <button
          onClick={() => setActiveSubTab('resume')}
          className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all cursor-pointer whitespace-nowrap flex items-center gap-2 ${
            activeSubTab === 'resume'
              ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
              : 'text-zinc-600 hover:text-zinc-950'
          }`}
        >
          <FileText className="w-3.5 h-3.5 text-purple-600" />
          <span>Resume & Skills</span>
        </button>

        <button
          onClick={() => setActiveSubTab('qa')}
          className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all cursor-pointer whitespace-nowrap flex items-center gap-2 ${
            activeSubTab === 'qa'
              ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
              : 'text-zinc-600 hover:text-zinc-950'
          }`}
        >
          <HelpCircle className="w-3.5 h-3.5 text-rose-600" />
          <span>Screening Q&A Knowledge ({qaList.length})</span>
        </button>

        <button
          onClick={() => setActiveSubTab('settings')}
          className={`px-4 py-2 rounded-2xl text-xs font-semibold transition-all cursor-pointer whitespace-nowrap flex items-center gap-2 ${
            activeSubTab === 'settings'
              ? 'liquid-pill bg-white text-zinc-950 font-bold shadow-xs'
              : 'text-zinc-600 hover:text-zinc-950'
          }`}
        >
          <Sliders className="w-3.5 h-3.5 text-cyan-600" />
          <span>Automation Settings</span>
        </button>
      </div>

      {/* ───────────────── SUB-TAB 1: IDENTITY & CONTACT ───────────────── */}
      {activeSubTab === 'identity' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Personal Details */}
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
              <User className="w-4 h-4 text-blue-600" />
              <span>Personal Identity</span>
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">First Name</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Sameer"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Last Name</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Bagul"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="sameer@example.com"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 font-mono shadow-2xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Phone Number</label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 98765 43210"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Current Title</label>
                <input
                  type="text"
                  value={currentTitle}
                  onChange={(e) => setCurrentTitle(e.target.value)}
                  placeholder="Senior AI Engineer"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Current Company</label>
                <input
                  type="text"
                  value={currentCompany}
                  onChange={(e) => setCurrentCompany(e.target.value)}
                  placeholder="Independent / Stealth"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Years of Experience</label>
                <input
                  type="number"
                  min="0"
                  max="40"
                  value={yearsExperience}
                  onChange={(e) => setYearsExperience(Number(e.target.value))}
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Notice Period</label>
                <select
                  value={noticePeriod}
                  onChange={(e) => setNoticePeriod(e.target.value)}
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                >
                  <option value="Immediate">Immediate / Serving Notice</option>
                  <option value="15 Days">15 Days</option>
                  <option value="30 Days">30 Days (1 Month)</option>
                  <option value="60 Days">60 Days (2 Months)</option>
                  <option value="90 Days">90 Days (3 Months)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Location & Social Footprint */}
          <div className="space-y-5">
            <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                <MapPin className="w-4 h-4 text-emerald-600" />
                <span>Geographic Location</span>
              </h3>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-zinc-700 block mb-1">City</label>
                  <input
                    type="text"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="Bengaluru"
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-zinc-700 block mb-1">State / Province</label>
                  <input
                    type="text"
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    placeholder="Karnataka"
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-zinc-700 block mb-1">Country</label>
                  <input
                    type="text"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    placeholder="India"
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-zinc-700 block mb-1">Postal / ZIP Code</label>
                  <input
                    type="text"
                    value={postalCode}
                    onChange={(e) => setPostalCode(e.target.value)}
                    placeholder="560001"
                    className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                  />
                </div>
              </div>
            </div>

            <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                <Globe className="w-4 h-4 text-purple-600" />
                <span>Professional Links & Portfolios</span>
              </h3>

              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">LinkedIn Profile</label>
                <input
                  type="url"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  placeholder="https://www.linkedin.com/in/username"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 font-mono shadow-2xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">GitHub Profile</label>
                <input
                  type="url"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/username"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 font-mono shadow-2xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Personal Portfolio / Website</label>
                <input
                  type="url"
                  value={portfolioUrl}
                  onChange={(e) => setPortfolioUrl(e.target.value)}
                  placeholder="https://portfolio.dev"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 font-mono shadow-2xs"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ───────────────── SUB-TAB 2: WORK AUTH & EEO ───────────────── */}
      {activeSubTab === 'auth' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Legal Work Authorization & Visas</span>
            </h3>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Primary Citizenship</label>
              <input
                type="text"
                value={citizenship}
                onChange={(e) => setCitizenship(e.target.value)}
                placeholder="India"
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">
                Are you legally authorized to work in the country of the job role?
              </label>
              <select
                value={authorizedInTarget}
                onChange={(e) => setAuthorizedInTarget(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="Yes">Yes — Legally Authorized without restrictions</option>
                <option value="No">No — Not authorized without employment visa</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">
                Will you now or in the future require visa sponsorship?
              </label>
              <select
                value={requiresSponsorship}
                onChange={(e) => setRequiresSponsorship(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="No">No — Do not require sponsorship</option>
                <option value="Yes">Yes — Require sponsorship (H-1B, Tier 2, etc.)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Security Clearance</label>
              <select
                value={securityClearance}
                onChange={(e) => setSecurityClearance(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="None">None / Not Applicable</option>
                <option value="Confidential">Confidential</option>
                <option value="Secret">Secret</option>
                <option value="Top Secret">Top Secret (TS/SCI)</option>
              </select>
            </div>
          </div>

          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-purple-600" />
              <span>Voluntary Equal Opportunity (EEO) Disclosures</span>
            </h3>
            <p className="text-xs text-zinc-500">
              Standard US/Global voluntary self-identification disclosures. Automatically fills voluntary demographic drop-downs on Greenhouse, Workday, and Lever.
            </p>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Gender</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Non-Binary">Non-Binary</option>
                <option value="Decline to Self-Identify">I choose not to disclose</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Veteran Status</label>
              <select
                value={veteranStatus}
                onChange={(e) => setVeteranStatus(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="I am not a protected veteran">I am not a protected veteran</option>
                <option value="I identify as one or more of the classifications of protected veteran">
                  I identify as a protected veteran
                </option>
                <option value="I choose not to disclose">I choose not to disclose</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Disability Status</label>
              <select
                value={disabilityStatus}
                onChange={(e) => setDisabilityStatus(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="No, I do not have a disability">No, I do not have a disability</option>
                <option value="Yes, I have a disability (or previously had a disability)">
                  Yes, I have a disability
                </option>
                <option value="I choose not to disclose">I choose not to disclose</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* ───────────────── SUB-TAB 3: COMPENSATION & PREFERENCES ───────────────── */}
      {activeSubTab === 'compensation' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
              <DollarSign className="w-4 h-4 text-amber-600" />
              <span>Target Compensation</span>
            </h3>

            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Target Base Salary</label>
                <input
                  type="text"
                  value={targetSalary}
                  onChange={(e) => setTargetSalary(e.target.value)}
                  placeholder="35,00,000 - 50,00,000"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Currency</label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Minimum Acceptable Salary</label>
              <input
                type="text"
                value={minSalary}
                onChange={(e) => setMinSalary(e.target.value)}
                placeholder="30,00,000"
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              />
            </div>
          </div>

          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-cyan-600" />
              <span>Location & Workplace Culture</span>
            </h3>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Remote Working Preference</label>
              <select
                value={remotePreference}
                onChange={(e) => setRemotePreference(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="100% Remote">100% Remote Only</option>
                <option value="Remote / Hybrid">Remote or Hybrid</option>
                <option value="Hybrid / On-site">Hybrid or On-site</option>
                <option value="Any">Flexible to Any Arrangement</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Willingness to Relocate</label>
              <select
                value={willingToRelocate}
                onChange={(e) => setWillingToRelocate(e.target.value)}
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              >
                <option value="Yes">Yes — Willing to relocate for the right role</option>
                <option value="No">No — Prefer to remain in current location</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* ───────────────── SUB-TAB 4: RESUME & SKILLS ───────────────── */}
      {activeSubTab === 'resume' && (
        <div className="space-y-5">
          {/* Resume File Upload Widget */}
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                  <Upload className="w-4 h-4 text-purple-600" />
                  <span>Resume Document (`resume.pdf` / `resume.docx`)</span>
                </h3>
                <p className="text-xs text-zinc-500 mt-0.5">
                  The primary file automatically attached to ATS file-upload inputs during application runs.
                </p>
              </div>

              {hasResumeFile && (
                <div className="px-3 py-1.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-semibold flex items-center gap-1.5 shadow-2xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Attached: {resumeFilename}</span>
                </div>
              )}
            </div>

            <div className="p-6 rounded-2xl border-2 border-dashed border-zinc-200 bg-white/60 hover:bg-white/90 transition text-center space-y-3">
              <Upload className="w-8 h-8 text-zinc-400 mx-auto" />
              <div className="text-xs text-zinc-600">
                <label className="font-semibold text-purple-700 hover:text-purple-800 cursor-pointer underline">
                  Click to select file
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={handleResumeFileUpload}
                    className="hidden"
                  />
                </label>
                <span className="text-zinc-500"> or drag and drop your updated PDF or DOCX resume</span>
              </div>
              <p className="text-[10.5px] text-zinc-400">Supported formats: PDF, DOCX, TXT (Max 10MB)</p>
            </div>
          </div>

          {/* Technical Skills Matrix */}
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-cyan-600" />
              <span>Core Technical Skills Matrix</span>
            </h3>

            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="liquid-pill px-3 py-1 rounded-full text-xs font-semibold text-zinc-800 flex items-center gap-1.5 shadow-2xs group"
                >
                  <span>{skill}</span>
                  <button
                    onClick={() => handleRemoveSkill(skill)}
                    className="p-0.5 hover:text-rose-600 text-zinc-400 transition"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 max-w-md pt-2">
              <input
                type="text"
                value={newSkillInput}
                onChange={(e) => setNewSkillInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
                placeholder="Add skill (e.g. Next.js, LangChain, Rust)..."
                className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
              />
              <button
                type="button"
                onClick={handleAddSkill}
                className="liquid-pill px-3 py-2 rounded-xl text-xs font-semibold cursor-pointer shadow-2xs"
              >
                Add
              </button>
            </div>
          </div>

          {/* Bio / Summary & Plaintext Resume */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Candidate Summary / Pitch
              </h3>
              <textarea
                rows={8}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="Brief professional elevator pitch..."
                className="w-full bg-white/80 border border-zinc-200/90 rounded-2xl p-3.5 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs leading-relaxed"
              />
            </div>

            <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Extracted Resume Text (`resume.txt`)
              </h3>
              <textarea
                rows={8}
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="Plaintext version of your resume used for deterministic 4-factor scoring..."
                className="w-full bg-white/80 border border-zinc-200/90 rounded-2xl p-3.5 text-xs text-zinc-900 font-mono focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs leading-relaxed"
              />
            </div>
          </div>
        </div>
      )}

      {/* ───────────────── SUB-TAB 5: SCREENING Q&A KNOWLEDGE BASE ───────────────── */}
      {activeSubTab === 'qa' && (
        <div className="space-y-5">
          {/* Add Q&A Form */}
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
              <Plus className="w-4 h-4 text-purple-600" />
              <span>Add Custom Screening Question & Answer (Tier 1 Semantic QA)</span>
            </h3>

            <form onSubmit={handleAddQa} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">
                  Question Text / Prompt
                </label>
                <input
                  type="text"
                  required
                  value={newQuestion}
                  onChange={(e) => setNewQuestion(e.target.value)}
                  placeholder="e.g. How many years of experience do you have with TypeScript & Next.js?"
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">
                  Verified Answer (Text or Value)
                </label>
                <textarea
                  rows={2}
                  required
                  value={newAnswer}
                  onChange={(e) => setNewAnswer(e.target.value)}
                  placeholder="e.g. 4 years of deep production experience building high-scale fullstack web applications."
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl px-3 py-2 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={addingQa}
                  className="liquid-pill-dark px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <Plus className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{addingQa ? 'Adding...' : 'Save to Knowledge Base'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Search & List of Known Questions */}
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-zinc-900 tracking-tight">
                  Pre-Answered Screening Knowledge Base
                </h3>
                <p className="text-xs text-zinc-500">
                  When forms present these questions, ApplyPilot matches them with zero external LLM token cost
                </p>
              </div>

              <div className="relative w-full sm:w-64">
                <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={qaSearch}
                  onChange={(e) => setQaSearch(e.target.value)}
                  placeholder="Search questions or answers..."
                  className="w-full bg-white/80 border border-zinc-200/90 rounded-xl pl-9 pr-3 py-1.5 text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 shadow-2xs"
                />
              </div>
            </div>

            {filteredQaList.length === 0 ? (
              <div className="py-12 text-center text-xs text-zinc-500 liquid-glass rounded-2xl p-6">
                No matching questions found in knowledge base. Add your common answers above!
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {filteredQaList.map((q) => (
                  <div
                    key={q.id}
                    className="liquid-row rounded-2xl p-3.5 flex items-start justify-between gap-3"
                  >
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-zinc-900">{q.question_text}</span>
                        {q.use_count > 0 && (
                          <span className="text-[10px] px-2 py-0.2 rounded-full font-mono bg-purple-50 text-purple-700 border border-purple-200">
                            Used {q.use_count}x
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-600 bg-white/70 p-2 rounded-xl border border-zinc-200/60 leading-relaxed">
                        {q.answer_text}
                      </p>
                    </div>

                    <button
                      onClick={() => handleDeleteQa(q.id)}
                      className="p-1.5 rounded-lg text-zinc-400 hover:text-rose-600 hover:bg-rose-50 transition cursor-pointer shrink-0"
                      title="Delete question from knowledge base"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ───────────────── SUB-TAB 6: AUTOMATION SETTINGS ───────────────── */}
      {activeSubTab === 'settings' && (
        <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
            <Sliders className="w-4 h-4 text-cyan-600" />
            <span>Autonomous Application Execution Modes</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="p-5 rounded-2xl bg-white/70 border border-white/90 shadow-2xs space-y-3">
              <span className="text-xs font-bold text-zinc-900 block">Default Automation Mode</span>
              <div className="space-y-2">
                <label className="flex items-center gap-3 p-3 rounded-xl border border-zinc-200/70 bg-white cursor-pointer hover:border-purple-400 transition">
                  <input
                    type="radio"
                    name="apply_mode"
                    value="headless"
                    checked={defaultApplyMode === 'headless'}
                    onChange={() => setDefaultApplyMode('headless')}
                    className="text-purple-600 focus:ring-purple-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-zinc-900 block">Headless Mode (Default)</span>
                    <span className="text-[11px] text-zinc-500">
                      Runs invisibly in the background with zero desktop interruption.
                    </span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 rounded-xl border border-zinc-200/70 bg-white cursor-pointer hover:border-purple-400 transition">
                  <input
                    type="radio"
                    name="apply_mode"
                    value="headed"
                    checked={defaultApplyMode === 'headed'}
                    onChange={() => setDefaultApplyMode('headed')}
                    className="text-purple-600 focus:ring-purple-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-zinc-900 block">Headed Mode (Interactive Window)</span>
                    <span className="text-[11px] text-zinc-500">
                      Opens visible browser window so you can watch form filling live.
                    </span>
                  </div>
                </label>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-white/70 border border-white/90 shadow-2xs space-y-3">
              <span className="text-xs font-bold text-zinc-900 block">Submission Confirmation Safety Gate</span>
              <label className="flex items-start gap-3 p-3 rounded-xl border border-zinc-200/70 bg-white cursor-pointer hover:border-purple-400 transition">
                <input
                  type="checkbox"
                  checked={autoSubmit}
                  onChange={(e) => setAutoSubmit(e.target.checked)}
                  className="mt-0.5 rounded text-purple-600 focus:ring-purple-500"
                />
                <div>
                  <span className="text-xs font-semibold text-zinc-900 block">
                    Auto-Submit Form Once Completed
                  </span>
                  <span className="text-[11px] text-zinc-500 leading-tight block mt-0.5">
                    When disabled, the runner fills all fields and pauses on the review screen for confirmation.
                  </span>
                </div>
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

