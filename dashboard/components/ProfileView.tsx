'use client';

import React, { useState, useEffect } from 'react';
import {
  Save,
  CheckCircle2,
  FileText,
  Upload,
  User,
  ShieldCheck,
  DollarSign,
  HelpCircle,
  Settings,
  Plus,
  Trash2,
  Copy,
  Check,
  ExternalLink,
  Briefcase,
  Building2,
  Code,
  Sparkles,
  Award,
  GraduationCap,
  Terminal,
  Zap,
  Flame,
  Search,
  AlertCircle,
  Clock,
  MapPin,
  Globe,
  FolderCheck,
  RefreshCw,
  Folder,
} from 'lucide-react';

export function ProfileView() {
  const [activeSubTab, setActiveSubTab] = useState<
    'identity' | 'experience' | 'projects' | 'compensation' | 'auth' | 'qa' | 'resume' | 'eeo' | 'settings'
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
  const [yearsExperience, setYearsExperience] = useState<number>(2.5);
  const [noticePeriod, setNoticePeriod] = useState('Immediate to 15 Days');

  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [country, setCountry] = useState('India');
  const [postalCode, setPostalCode] = useState('');

  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [portfolioUrl, setPortfolioUrl] = useState('');

  const [citizenship, setCitizenship] = useState('India');
  const [authorizedInTarget, setAuthorizedInTarget] = useState('Yes (India / Remote Contractor worldwide)');
  const [requiresSponsorship, setRequiresSponsorship] = useState('No for remote/India; Yes for international onsite');
  const [securityClearance, setSecurityClearance] = useState('None');

  const [gender, setGender] = useState('Male');
  const [race, setRace] = useState('Asian (Indian)');
  const [veteranStatus, setVeteranStatus] = useState('I am not a protected veteran');
  const [disabilityStatus, setDisabilityStatus] = useState('No, I do not have a disability');

  const [currentCtc, setCurrentCtc] = useState('₹7,00,000 (7 LPA)');
  const [joiningBonus, setJoiningBonus] = useState('₹1,00,000 (1 Lakh)');
  const [targetSalary, setTargetSalary] = useState('₹7,00,000 - ₹10,00,000');
  const [minSalary, setMinSalary] = useState('₹5,00,000 - ₹6,00,000');
  const [targetSalaryUsd, setTargetSalaryUsd] = useState('$70,000 - $110,000');
  const [hourlyRateUsd, setHourlyRateUsd] = useState('$35 - $60 / hr');
  const [currency, setCurrency] = useState('INR');
  const [equityOpen, setEquityOpen] = useState(true);
  const [negotiable, setNegotiable] = useState(true);
  const [negotiationPolicy, setNegotiationPolicy] = useState(
    'Flexible: If company indicates budget > 8-9 LPA, accept full company budget. If company budget is 5-6 LPA, submit form at their budget and negotiate after interview.'
  );
  const [remotePreference, setRemotePreference] = useState('Remote / Hybrid');
  const [willingToRelocate, setWillingToRelocate] = useState('Yes');

  const [defaultApplyMode, setDefaultApplyMode] = useState<'headless' | 'headed'>('headed');
  const [autoSubmit, setAutoSubmit] = useState(false);

  const [summary, setSummary] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkillInput, setNewSkillInput] = useState('');

  // Experience & Education & Projects State
  const [experiences, setExperiences] = useState<any[]>([]);
  const [education, setEducation] = useState<any[]>([]);
  const [achievements, setAchievements] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [storyMatrix, setStoryMatrix] = useState<any>({ rules: [] });
  const [resumeFiles, setResumeFiles] = useState<any>(null);

  // Story Generator State
  const [storyQuery, setStoryQuery] = useState('');
  const [generatingStory, setGeneratingStory] = useState(false);
  const [storyResult, setStoryResult] = useState<any>(null);
  const [copiedStory, setCopiedStory] = useState(false);
  const [copiedQuick, setCopiedQuick] = useState(false);

  const [hasResumeFile, setHasResumeFile] = useState(false);
  const [resumeFilename, setResumeFilename] = useState<string | null>(null);
  const [uploadingResume, setUploadingResume] = useState(false);

  // Q&A Knowledge Base State
  const [qaList, setQaList] = useState<any[]>([]);
  const [qaSearch, setQaSearch] = useState('');
  const [qaCategoryFilter, setQaCategoryFilter] = useState('ALL');
  const [newQuestion, setNewQuestion] = useState('');
  const [newAnswer, setNewAnswer] = useState('');
  const [newQaCategory, setNewQaCategory] = useState('general');
  const [addingQa, setAddingQa] = useState(false);
  const [copiedQaId, setCopiedQaId] = useState<string | number | null>(null);

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
        setYearsExperience(p.years_of_experience || 2.5);
        setNoticePeriod(p.notice_period || 'Immediate to 15 Days');

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
          setAuthorizedInTarget(p.work_authorization.authorized_in_target || 'Yes (India / Remote Contractor worldwide)');
          setRequiresSponsorship(p.work_authorization.requires_sponsorship || 'No for remote/India; Yes for international onsite');
          setSecurityClearance(p.work_authorization.security_clearance || 'None');
        }

        if (p.eeo) {
          setGender(p.eeo.gender || 'Male');
          setRace(p.eeo.race || 'Asian (Indian)');
          setVeteranStatus(p.eeo.veteran_status || 'I am not a protected veteran');
          setDisabilityStatus(p.eeo.disability_status || 'No, I do not have a disability');
        }

        if (p.compensation) {
          setCurrentCtc(p.compensation.current_ctc || '₹7,00,000 (7 LPA)');
          setJoiningBonus(p.compensation.joining_bonus || '₹1,00,000 (1 Lakh)');
          setTargetSalary(p.compensation.target_salary || '₹7,00,000 - ₹10,00,000');
          setMinSalary(p.compensation.min_salary || '₹5,00,000 - ₹6,00,000');
          setTargetSalaryUsd(p.compensation.target_salary_usd || '$70,000 - $110,000');
          setHourlyRateUsd(p.compensation.hourly_rate_usd || '$35 - $60 / hr');
          setCurrency(p.compensation.currency || 'INR');
          setEquityOpen(p.compensation.equity_open ?? true);
          setNegotiable(p.compensation.negotiable ?? true);
          setNegotiationPolicy(p.compensation.negotiation_policy || '');
        }

        if (p.preferences) {
          setRemotePreference(p.preferences.remote_preference || 'Remote / Hybrid');
          setWillingToRelocate(p.preferences.willing_to_relocate || 'Yes');
          setDefaultApplyMode(p.preferences.default_apply_mode || 'headed');
          setAutoSubmit(p.preferences.auto_submit ?? false);
        }

        setSummary(p.summary || '');
        setResumeText(p.resume_text || '');
        setSkills(p.skills || []);

        // Rich structured sections
        setExperiences(p.experiences || []);
        setEducation(p.education || []);
        setAchievements(p.achievements || []);
        setProjects(p.projects || []);
        setStoryMatrix(p.story_matrix || { rules: [] });
        setResumeFiles(p.resume_files || null);

        // Fallback QAs from profile
        if (p.qa_knowledge && Array.isArray(p.qa_knowledge)) {
          setQaList(p.qa_knowledge);
        }

        setHasResumeFile(data.hasResume || false);
        setResumeFilename(data.resumePath ? data.resumePath.split('/').pop() : 'resume.pdf');
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
      if (data.success && data.list && data.list.length > 0) {
        setQaList(data.list);
      }
    } catch (err) {
      console.error('Failed to load Q&A list from database', err);
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
        race,
        veteran_status: veteranStatus,
        disability_status: disabilityStatus,
      },
      compensation: {
        current_ctc: currentCtc,
        joining_bonus: joiningBonus,
        target_salary: targetSalary,
        min_salary: minSalary,
        target_salary_usd: targetSalaryUsd,
        hourly_rate_usd: hourlyRateUsd,
        currency,
        equity_open: equityOpen,
        negotiable,
        negotiation_policy: negotiationPolicy,
      },
      preferences: {
        remote_preference: remotePreference,
        willing_to_relocate: willingToRelocate,
        default_apply_mode: defaultApplyMode,
        auto_submit: autoSubmit,
      },
      summary,
      skills,
      resume_text: resumeText,
      experiences,
      education,
      achievements,
      projects,
      story_matrix: storyMatrix,
      qa_knowledge: qaList,
      resume_files: resumeFiles,
    };

    try {
      const res = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        setSaveMessage('Candidate profile, experiences, and vault saved successfully!');
        setTimeout(() => setSaveMessage(null), 4000);
      } else {
        setSaveMessage(`Save failed: ${data.error}`);
      }
    } catch (err: any) {
      setSaveMessage(`Error saving profile: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateStory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!storyQuery.trim()) return;

    setGeneratingStory(true);
    setStoryResult(null);
    setCopiedStory(false);
    setCopiedQuick(false);

    try {
      const res = await fetch('/api/profile/story', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: storyQuery }),
      });
      const data = await res.json();
      if (data.success) {
        setStoryResult(data);
      } else {
        setStoryResult({ story: `Unable to generate story: ${data.error}` });
      }
    } catch (err: any) {
      setStoryResult({ story: `Generation error: ${err.message}` });
    } finally {
      setGeneratingStory(false);
    }
  };

  const handleAddSkill = () => {
    if (newSkillInput.trim() && !skills.includes(newSkillInput.trim())) {
      setSkills([...skills, newSkillInput.trim()]);
      setNewSkillInput('');
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkills(skills.filter((s) => s !== skillToRemove));
  };

  const handleAddExperienceHighlight = (expId: string) => {
    setExperiences(
      experiences.map((exp) => {
        if (exp.id === expId) {
          return {
            ...exp,
            highlights: [...(exp.highlights || []), 'New key engineering achievement or architecture contribution...'],
          };
        }
        return exp;
      })
    );
  };

  const handleUpdateExperienceHighlight = (expId: string, idx: number, val: string) => {
    setExperiences(
      experiences.map((exp) => {
        if (exp.id === expId) {
          const updated = [...(exp.highlights || [])];
          updated[idx] = val;
          return { ...exp, highlights: updated };
        }
        return exp;
      })
    );
  };

  const handleRemoveExperienceHighlight = (expId: string, idx: number) => {
    setExperiences(
      experiences.map((exp) => {
        if (exp.id === expId) {
          const updated = [...(exp.highlights || [])];
          updated.splice(idx, 1);
          return { ...exp, highlights: updated };
        }
        return exp;
      })
    );
  };

  const handleAddQaItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQuestion.trim() || !newAnswer.trim()) return;

    setAddingQa(true);
    const newEntry = {
      q: newQuestion.trim(),
      a: newAnswer.trim(),
      question_text: newQuestion.trim(),
      answer_text: newAnswer.trim(),
      cat: newQaCategory,
      category: newQaCategory,
      use_count: 0,
    };

    setQaList([newEntry, ...qaList]);
    setNewQuestion('');
    setNewAnswer('');
    setAddingQa(false);

    try {
      await fetch('/api/profile/qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_text: newEntry.question_text,
          answer_text: newEntry.answer_text,
          category: newQaCategory,
        }),
      });
    } catch {}
  };

  const handleCopyText = (text: string, type: 'story' | 'quick' | 'qa', id?: string | number) => {
    navigator.clipboard.writeText(text);
    if (type === 'story') {
      setCopiedStory(true);
      setTimeout(() => setCopiedStory(false), 2000);
    } else if (type === 'quick') {
      setCopiedQuick(true);
      setTimeout(() => setCopiedQuick(false), 2000);
    } else if (type === 'qa' && id != null) {
      setCopiedQaId(id);
      setTimeout(() => setCopiedQaId(null), 2000);
    }
  };

  const filteredQa = qaList.filter((item) => {
    const qText = (item.q || item.question_text || '').toLowerCase();
    const aText = (item.a || item.answer_text || '').toLowerCase();
    const cat = (item.cat || item.category || 'general').toLowerCase();

    const matchesSearch = !qaSearch || qText.includes(qaSearch.toLowerCase()) || aText.includes(qaSearch.toLowerCase());
    const matchesCat = qaCategoryFilter === 'ALL' || cat === qaCategoryFilter.toLowerCase();
    return matchesSearch && matchesCat;
  });

  const subTabs = [
    { id: 'identity', label: 'Identity & Bio', icon: User },
    { id: 'experience', label: 'Work History', icon: Briefcase, badge: experiences.length.toString() },
    { id: 'projects', label: 'Projects & Story Bridge', icon: Code, badge: projects.length.toString() },
    { id: 'compensation', label: 'Compensation', icon: DollarSign },
    { id: 'auth', label: 'Work Auth & Visas', icon: ShieldCheck },
    { id: 'qa', label: 'Screening QA Vault', icon: HelpCircle, badge: qaList.length.toString() },
    { id: 'resume', label: 'Resume Files', icon: FileText, badge: 'PDF' },
    { id: 'eeo', label: 'EEO Legal', icon: Globe },
    { id: 'settings', label: 'Automation', icon: Settings },
  ];

  if (loading) {
    return (
      <div className="liquid-glass rounded-3xl p-12 text-center text-xs text-zinc-500 space-y-3">
        <div className="w-8 h-8 rounded-full border-2 border-zinc-950/20 border-t-zinc-950 animate-spin mx-auto" />
        <p className="font-semibold">Loading Candidate Knowledge Vault & Experience Graph...</p>
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-in fade-in duration-200">
      {/* Top Header Card */}
      <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-xl sm:text-2xl font-black text-zinc-950 tracking-tight">
              Candidate Knowledge Graph
            </h2>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
              Auto-Fill Synced
            </span>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-800 border border-cyan-200 font-mono">
              ~/.applypilot/profile.json
            </span>
          </div>
          <p className="text-xs text-zinc-500">
            Comprehensive candidate intelligence vault powering autonomous form auto-fill, headed Playwright dispatch, and smart interview story synthesis.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          {saveMessage && (
            <span
              className={`text-xs font-semibold px-3 py-1.5 rounded-xl border animate-in fade-in ${
                saveMessage.includes('failed') || saveMessage.includes('Error')
                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                  : 'bg-emerald-50 text-emerald-800 border-emerald-200'
              }`}
            >
              {saveMessage}
            </span>
          )}

          <button
            onClick={handleSaveProfile}
            disabled={saving}
            className="liquid-pill px-4 py-2 rounded-2xl bg-zinc-950 text-white font-bold text-xs flex items-center justify-center gap-2 hover:bg-zinc-800 transition cursor-pointer shadow-md disabled:opacity-50 shrink-0 w-full md:w-auto"
          >
            {saving ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Saving Vault...</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>Save All Changes</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Subtab Navigation Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {subTabs.map((st) => {
          const IconComp = st.icon;
          const isActive = activeSubTab === st.id;
          return (
            <button
              key={st.id}
              onClick={() => setActiveSubTab(st.id as any)}
              className={`liquid-pill rounded-2xl px-3.5 py-2 flex items-center gap-2 text-xs font-bold transition-all cursor-pointer whitespace-nowrap shadow-2xs shrink-0 ${
                isActive
                  ? 'bg-white text-zinc-950 shadow-xs border-zinc-300 scale-[1.02]'
                  : 'text-zinc-600 hover:text-zinc-900 hover:bg-white/80'
              }`}
            >
              <IconComp className={`w-3.5 h-3.5 ${isActive ? 'text-zinc-950' : 'text-zinc-400'}`} />
              <span>{st.label}</span>
              {st.badge && (
                <span
                  className={`text-[9px] font-mono px-1.5 py-0.2 rounded-full border ${
                    isActive ? 'bg-zinc-950 text-white border-zinc-950' : 'bg-zinc-100 text-zinc-600 border-zinc-200'
                  }`}
                >
                  {st.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ===================== TAB 1: IDENTITY & CORE BIO ===================== */}
      {activeSubTab === 'identity' && (
        <div className="space-y-4 animate-in fade-in duration-150">
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-5">
            <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
              <User className="w-4 h-4 text-purple-600" />
              <span>Personal Identity & Contact Information</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">First Name</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Last Name</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Phone Number</label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Current / Target Title</label>
                <input
                  type="text"
                  value={currentTitle}
                  onChange={(e) => setCurrentTitle(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Current Company</label>
                <input
                  type="text"
                  value={currentCompany}
                  onChange={(e) => setCurrentCompany(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
                />
              </div>
            </div>

            {/* Location & Social URLs */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 pt-2 border-t border-zinc-200/60">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">City</label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">State / Region</label>
                <input
                  type="text"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Country</label>
                <input
                  type="text"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Postal Code</label>
                <input
                  type="text"
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-zinc-200/60">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">LinkedIn URL</label>
                <input
                  type="text"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 font-mono"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">GitHub Profile URL</label>
                <input
                  type="text"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 font-mono"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Portfolio / Website</label>
                <input
                  type="text"
                  value={portfolioUrl}
                  onChange={(e) => setPortfolioUrl(e.target.value)}
                  className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 font-mono"
                />
              </div>
            </div>

            {/* Professional Summary */}
            <div className="space-y-1 pt-2 border-t border-zinc-200/60">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Professional Bio & Executive Summary</label>
              <textarea
                rows={4}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                className="w-full text-xs font-medium p-3.5 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900 leading-relaxed focus:outline-none focus:ring-1 focus:ring-zinc-900"
              />
            </div>

            {/* Core Skills Chips */}
            <div className="space-y-2 pt-2 border-t border-zinc-200/60">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">
                Technical Skills Portfolio ({skills.length} skills)
              </label>
              <div className="flex flex-wrap gap-1.5 items-center">
                {skills.map((skill) => (
                  <span
                    key={skill}
                    className="liquid-pill px-2.5 py-1 rounded-xl text-xs font-semibold text-zinc-800 flex items-center gap-1.5 group shadow-2xs"
                  >
                    <span>{skill}</span>
                    <button
                      onClick={() => handleRemoveSkill(skill)}
                      className="text-zinc-400 hover:text-rose-600 transition cursor-pointer"
                    >
                      ×
                    </button>
                  </span>
                ))}
                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    value={newSkillInput}
                    onChange={(e) => setNewSkillInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
                    placeholder="Add skill + Enter"
                    className="text-xs px-2.5 py-1 rounded-xl bg-white/80 border border-zinc-200 text-zinc-900 w-32 focus:outline-none focus:ring-1 focus:ring-zinc-900"
                  />
                  <button
                    onClick={handleAddSkill}
                    className="liquid-pill px-2 py-1 rounded-xl text-xs font-bold text-zinc-700 hover:text-zinc-950 cursor-pointer shadow-2xs"
                  >
                    Add
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================== TAB 2: WORK EXPERIENCE & HISTORY ===================== */}
      {activeSubTab === 'experience' && (
        <div className="space-y-5 animate-in fade-in duration-150">
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60">
              <div>
                <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-blue-600" />
                  <span>Work Experience & Employment Timeline ({experiences.length} Positions)</span>
                </h3>
                <p className="text-xs text-zinc-500">
                  Cleaned and parsed directly from your verified experience file. Stored in config and used by Playwright application agents to answer job application experience prompts.
                </p>
              </div>
            </div>

            {/* Experience Cards */}
            <div className="space-y-4">
              {experiences.map((exp, expIdx) => (
                <div
                  key={exp.id || expIdx}
                  className="liquid-glass rounded-2xl p-5 border border-white/90 shadow-2xs space-y-3.5 relative"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-zinc-200/50">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-extrabold text-sm text-zinc-950">{exp.role}</span>
                        <span className="text-xs font-bold text-zinc-700">@ {exp.company}</span>
                        {exp.is_current ? (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                            Current Role
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-600 border border-zinc-200">
                            {exp.employment_type || 'Full-time'}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-zinc-500 flex items-center gap-2 font-medium">
                        <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                        <span>{exp.location}</span>
                        <span>•</span>
                        <Clock className="w-3.5 h-3.5 text-zinc-400" />
                        <span>
                          {exp.start_date} – {exp.end_date}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 self-start sm:self-center">
                      <button
                        onClick={() => handleAddExperienceHighlight(exp.id)}
                        className="liquid-pill px-2.5 py-1 rounded-xl text-[11px] font-bold text-zinc-700 hover:text-zinc-950 flex items-center gap-1 cursor-pointer shadow-2xs"
                      >
                        <Plus className="w-3 h-3" />
                        <span>Add Bullet</span>
                      </button>
                    </div>
                  </div>

                  {/* Role Summary */}
                  <p className="text-xs text-zinc-600 leading-relaxed font-normal">{exp.summary}</p>

                  {/* Highlights / Bullets */}
                  <div className="space-y-2">
                    <span className="text-[10.5px] font-bold text-zinc-500 uppercase tracking-wider block">
                      Key Engineering Accomplishments & Responsibilities ({exp.highlights?.length || 0})
                    </span>
                    <div className="space-y-1.5">
                      {(exp.highlights || []).map((highlight: string, hIdx: number) => (
                        <div key={hIdx} className="flex items-start gap-2 group">
                          <span className="text-zinc-400 font-bold text-xs mt-1">•</span>
                          <textarea
                            rows={2}
                            value={highlight}
                            onChange={(e) => handleUpdateExperienceHighlight(exp.id, hIdx, e.target.value)}
                            className="flex-1 text-xs font-normal p-2 rounded-xl bg-white/60 border border-zinc-200/70 text-zinc-800 leading-relaxed focus:bg-white focus:outline-none focus:ring-1 focus:ring-zinc-900 transition"
                          />
                          <button
                            onClick={() => handleRemoveExperienceHighlight(exp.id, hIdx)}
                            className="opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-rose-600 p-1 transition cursor-pointer"
                            title="Delete bullet point"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Skills Tags for this role */}
                  {exp.skills && exp.skills.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap pt-1">
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mr-1">Stack:</span>
                      {exp.skills.map((sk: string) => (
                        <span
                          key={sk}
                          className="text-[10px] font-semibold px-2 py-0.5 rounded-lg bg-zinc-50 text-zinc-700 border border-zinc-200/60"
                        >
                          {sk}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Education & Achievements Split Card */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Education */}
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-3">
              <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 pb-2 border-b border-zinc-200/60">
                <GraduationCap className="w-4 h-4 text-indigo-600" />
                <span>Verified Education</span>
              </h3>
              {education.map((edu, idx) => (
                <div key={idx} className="space-y-1.5 text-xs">
                  <div className="font-bold text-zinc-900">{edu.degree}</div>
                  <div className="text-zinc-600 font-medium">
                    {edu.institution} ({edu.start_year} – {edu.end_year})
                  </div>
                  <div className="flex items-center gap-3 text-zinc-500 font-mono text-[11px]">
                    <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                      CGPA: {edu.cgpa}
                    </span>
                    <span>MHT-CET: {edu.percentile}</span>
                  </div>
                  {edu.coursework && (
                    <div className="text-[11px] text-zinc-500 pt-1 leading-snug">
                      <span className="font-semibold text-zinc-700">Coursework: </span>
                      {edu.coursework.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Achievements & Hackathons */}
            <div className="liquid-glass rounded-3xl p-5 border border-white/90 shadow-xs space-y-3">
              <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 pb-2 border-b border-zinc-200/60">
                <Award className="w-4 h-4 text-amber-600" />
                <span>National Hackathons & Leadership</span>
              </h3>
              <div className="space-y-2.5">
                {achievements.map((ach, idx) => (
                  <div key={idx} className="text-xs space-y-0.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-zinc-900">{ach.title}</span>
                      <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                        {ach.role}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-500 leading-snug">{ach.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================== TAB 3: FLAGSHIP PROJECTS & STORY BRIDGE ===================== */}
      {activeSubTab === 'projects' && (
        <div className="space-y-5 animate-in fade-in duration-150">
          {/* Smart Story Bridge Generator Tool */}
          <div className="liquid-glass-elevated rounded-3xl p-6 border border-white/95 shadow-md space-y-4 relative overflow-hidden">
            <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent pointer-events-none" />

            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cyan-50 text-cyan-800 border border-cyan-200 text-[10px] font-bold uppercase tracking-wider">
                <Sparkles className="w-3 h-3 text-cyan-600" />
                <span>Instant Form-Answer Synthesizer</span>
              </div>
              <h3 className="text-base font-extrabold text-zinc-950 tracking-tight">
                Smart Story Bridge Generator (Answer Any Tech Prompt XYZ)
              </h3>
              <p className="text-xs text-zinc-600 leading-relaxed max-w-3xl">
                When application forms ask: <em>&quot;Describe a project where you built XYZ&quot;</em> or <em>&quot;Have you worked with Kubernetes / Go / Rust / GraphQL / Kafka?&quot;</em>, type the technology below to instantly generate a battle-tested, high-credibility engineering answer ready to copy-paste.
              </p>
            </div>

            <form onSubmit={handleGenerateStory} className="flex flex-col sm:flex-row gap-2 max-w-2xl">
              <div className="relative flex-1">
                <Terminal className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={storyQuery}
                  onChange={(e) => setStoryQuery(e.target.value)}
                  placeholder="e.g. Kubernetes, Kafka, Golang, GraphQL, Rust, Microservices..."
                  className="w-full text-xs font-medium pl-9 pr-4 py-2.5 rounded-xl bg-white border border-zinc-200 text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-950/20"
                />
              </div>
              <button
                type="submit"
                disabled={generatingStory || !storyQuery.trim()}
                className="liquid-pill px-5 py-2.5 rounded-xl bg-zinc-950 text-white font-bold text-xs flex items-center justify-center gap-2 hover:bg-zinc-800 transition cursor-pointer shadow-sm disabled:opacity-50 shrink-0"
              >
                {generatingStory ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Synthesizing...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                    <span>Generate Story</span>
                  </>
                )}
              </button>
            </form>

            {/* Generated Story Display */}
            {storyResult && (
              <div className="p-4 rounded-2xl bg-white/90 border border-zinc-200 shadow-2xs space-y-3 animate-in fade-in">
                <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-zinc-100">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-zinc-900">Result for &quot;{storyResult.query}&quot;</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        storyResult.is_bridge
                          ? 'bg-amber-50 text-amber-800 border-amber-200'
                          : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      }`}
                    >
                      {storyResult.is_bridge ? 'Bridge Architecture Story' : 'Direct Project Match'}
                    </span>
                    <span className="text-[11px] font-mono text-zinc-500">[{storyResult.matched_project}]</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleCopyText(storyResult.quick_answer, 'quick')}
                      className="liquid-pill px-2.5 py-1 rounded-xl text-[11px] font-bold text-zinc-700 hover:text-zinc-950 flex items-center gap-1 cursor-pointer shadow-2xs"
                    >
                      {copiedQuick ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      <span>Copy 1-Liner</span>
                    </button>
                    <button
                      onClick={() => handleCopyText(storyResult.story, 'story')}
                      className="liquid-pill px-2.5 py-1 rounded-xl text-[11px] font-bold text-zinc-700 hover:text-zinc-950 flex items-center gap-1 cursor-pointer shadow-2xs"
                    >
                      {copiedStory ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      <span>Copy Full Paragraph</span>
                    </button>
                  </div>
                </div>

                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-0.5">
                      Quick Dropdown / Short Form Answer:
                    </span>
                    <p className="font-medium text-zinc-900 bg-zinc-50 p-2.5 rounded-xl border border-zinc-200/60 select-all">
                      {storyResult.quick_answer}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-0.5">
                      Complete Technical Story / Application Form Text Area:
                    </span>
                    <p className="font-normal text-zinc-800 leading-relaxed bg-zinc-50 p-3 rounded-xl border border-zinc-200/60 select-all whitespace-pre-wrap">
                      {storyResult.story}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Curated Flagship Projects Showcase */}
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60">
              <div>
                <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
                  <Code className="w-4 h-4 text-purple-600" />
                  <span>Curated High-Tech Flagship Projects ({projects.length} Showcased)</span>
                </h3>
                <p className="text-xs text-zinc-500">
                  Filtered from 86 total projects to highlight only high-complexity production software (agentic AI, RAG, Playwright automation, 3D desktop engines, and distributed architectures).
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {projects.map((proj, pIdx) => (
                <div
                  key={proj.id || pIdx}
                  className="liquid-glass rounded-2xl p-4 sm:p-5 border border-white/90 shadow-2xs space-y-3 flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <span className="font-bold text-xs text-zinc-950 block">{proj.title}</span>
                        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
                          {proj.category}
                        </span>
                      </div>
                      {proj.featured && (
                        <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-800 border border-purple-200 shrink-0">
                          Flagship
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-zinc-600 leading-relaxed line-clamp-3">
                      {proj.shortDescription}
                    </p>

                    {/* Highlights bullets */}
                    {proj.highlights && proj.highlights.length > 0 && (
                      <div className="space-y-1 text-[11px] text-zinc-500 pt-1">
                        {proj.highlights.slice(0, 2).map((h: string, hIdx: number) => (
                          <div key={hIdx} className="flex items-start gap-1.5">
                            <span className="text-zinc-400 font-bold">•</span>
                            <span className="line-clamp-2">{h}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="space-y-2 pt-2 border-t border-zinc-100">
                    {/* Metrics badge */}
                    {proj.metrics && (
                      <div className="text-[10.5px] font-semibold text-emerald-800 bg-emerald-50/70 px-2 py-1 rounded-lg border border-emerald-200/60 truncate">
                        ⚡ {proj.metrics}
                      </div>
                    )}

                    {/* Tech Stack pills */}
                    <div className="flex items-center gap-1 flex-wrap">
                      {(proj.techStack || []).slice(0, 6).map((tech: string) => (
                        <span
                          key={tech}
                          className="text-[9.5px] font-semibold px-1.5 py-0.2 rounded-md bg-white border border-zinc-200 text-zinc-700"
                        >
                          {tech}
                        </span>
                      ))}
                      {(proj.techStack || []).length > 6 && (
                        <span className="text-[9px] text-zinc-400 font-bold">
                          +{proj.techStack.length - 6} more
                        </span>
                      )}
                    </div>

                    {/* Links */}
                    <div className="flex items-center gap-3 pt-1 text-xs font-semibold">
                      {proj.githubUrl && (
                        <a
                          href={proj.githubUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-zinc-700 hover:text-zinc-950 flex items-center gap-1 transition"
                        >
                          <span>Repository</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                      {proj.liveUrl && (
                        <a
                          href={proj.liveUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-cyan-700 hover:text-cyan-900 flex items-center gap-1 transition"
                        >
                          <span>Live Site</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                      <button
                        onClick={() => {
                          setStoryQuery(proj.title);
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                        className="text-zinc-500 hover:text-zinc-900 ml-auto flex items-center gap-1 cursor-pointer"
                      >
                        <Sparkles className="w-3 h-3 text-amber-500" />
                        <span>Form Story</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ===================== TAB 4: COMPENSATION & RATES ===================== */}
      {activeSubTab === 'compensation' && (
        <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-5 animate-in fade-in duration-150">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-emerald-600" />
                <span>Compensation, Current CTC & Auto-Fill Negotiation Strategy</span>
              </h3>
              <p className="text-xs text-zinc-500">
                Configured to adapt dynamically to ATS budgets during headed and headless application submissions.
              </p>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
              Active Strategy: 7–10 LPA Adaptive
            </span>
          </div>

          {/* Strategy & Negotiation Directive Card */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-50/70 to-cyan-50/70 border border-emerald-200/80 shadow-2xs space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-900">
              <Sparkles className="w-4 h-4 text-emerald-600" />
              <span>Smart Form-Fill Policy (Always Submit & Adapt to Budget)</span>
            </div>
            <ul className="text-xs text-zinc-700 space-y-1 list-disc pl-4 leading-relaxed font-normal">
              <li>
                <strong>Current CTC:</strong> Fixed CTC is <strong>₹7,00,000 (7 LPA)</strong> + <strong>₹1,00,000 joining bonus</strong> (Total: ₹8,00,000).
              </li>
              <li>
                <strong>Target Range:</strong> Targeting <strong>7 to 10 LPA</strong>.
              </li>
              <li>
                <strong>Higher Budget Adaptation:</strong> If the employer indicates a budget above 8 or 9 LPA (e.g. 10 LPA, 12 LPA, 15 LPA), the auto-apply agent will <em>not</em> anchor low at 7 LPA—it accepts and requests their full advertised budget.
              </li>
              <li>
                <strong>Lower Budget Acceptance:</strong> If the company specifies 5 LPA or 6 LPA, the agent submits the form using their budget so you enter the process, leaving room to negotiate post-interview.
              </li>
              <li>
                <strong>Negotiable Flag:</strong> Always marked as <strong>Yes (Negotiable & Flexible)</strong> in dropdowns and prompts.
              </li>
            </ul>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Current Fixed CTC</label>
              <input
                type="text"
                value={currentCtc}
                onChange={(e) => setCurrentCtc(e.target.value)}
                placeholder="₹7,00,000 (7 LPA)"
                className="w-full text-xs font-semibold px-3.5 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Joining / Sign-on Bonus</label>
              <input
                type="text"
                value={joiningBonus}
                onChange={(e) => setJoiningBonus(e.target.value)}
                placeholder="₹1,00,000 (1 Lakh)"
                className="w-full text-xs font-semibold px-3.5 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Target Expected CTC (INR)</label>
              <input
                type="text"
                value={targetSalary}
                onChange={(e) => setTargetSalary(e.target.value)}
                placeholder="₹7,00,000 - ₹10,00,000"
                className="w-full text-xs font-bold text-emerald-800 px-3.5 py-2 rounded-xl bg-white border border-zinc-200"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Minimum Acceptable (INR)</label>
              <input
                type="text"
                value={minSalary}
                onChange={(e) => setMinSalary(e.target.value)}
                placeholder="₹5,00,000 - ₹6,00,000"
                className="w-full text-xs font-semibold px-3.5 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Target Annual USD (Remote)</label>
              <input
                type="text"
                value={targetSalaryUsd}
                onChange={(e) => setTargetSalaryUsd(e.target.value)}
                placeholder="$70,000 - $110,000"
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Hourly Contractor Rate (USD)</label>
              <input
                type="text"
                value={hourlyRateUsd}
                onChange={(e) => setHourlyRateUsd(e.target.value)}
                placeholder="$35 - $60 / hr"
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Notice Period</label>
              <input
                type="text"
                value={noticePeriod}
                onChange={(e) => setNoticePeriod(e.target.value)}
                placeholder="Immediate to 15 Days"
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Remote / Workplace Preference</label>
              <select
                value={remotePreference}
                onChange={(e) => setRemotePreference(e.target.value)}
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              >
                <option value="Remote / Hybrid">Remote / Hybrid</option>
                <option value="Remote Only">Remote Only</option>
                <option value="Hybrid Only">Hybrid Only</option>
                <option value="Onsite Only">Onsite Only</option>
                <option value="Open to All">Open to All</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* ===================== TAB 5: WORK AUTH & VISAS ===================== */}
      {activeSubTab === 'auth' && (
        <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-5 animate-in fade-in duration-150">
          <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Work Authorization & Global Visa Eligibility</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Primary Citizenship</label>
              <input
                type="text"
                value={citizenship}
                onChange={(e) => setCitizenship(e.target.value)}
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Target Country Work Authorization</label>
              <input
                type="text"
                value={authorizedInTarget}
                onChange={(e) => setAuthorizedInTarget(e.target.value)}
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Requires Visa Sponsorship</label>
              <input
                type="text"
                value={requiresSponsorship}
                onChange={(e) => setRequiresSponsorship(e.target.value)}
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Security Clearance</label>
              <input
                type="text"
                value={securityClearance}
                onChange={(e) => setSecurityClearance(e.target.value)}
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>
          </div>
        </div>
      )}

      {/* ===================== TAB 6: SCREENING QA VAULT ===================== */}
      {activeSubTab === 'qa' && (
        <div className="space-y-4 animate-in fade-in duration-150">
          <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-200/60">
              <div>
                <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-indigo-600" />
                  <span>Candidate Screening QA Knowledge Vault ({filteredQa.length} Entries)</span>
                </h3>
                <p className="text-xs text-zinc-500">
                  Pre-configured answers to all repetitive screening questions across Greenhouse, Lever, Ashby, and Workday forms.
                </p>
              </div>

              {/* Category Filter Pills */}
              <div className="flex items-center gap-1 overflow-x-auto pb-1">
                {['ALL', 'work_authorization', 'availability', 'location', 'compensation', 'tech_yoe', 'behavioral'].map(
                  (cat) => (
                    <button
                      key={cat}
                      onClick={() => setQaCategoryFilter(cat)}
                      className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-xl transition cursor-pointer shrink-0 ${
                        qaCategoryFilter === cat
                          ? 'bg-zinc-950 text-white shadow-2xs'
                          : 'liquid-pill text-zinc-600 hover:text-zinc-900'
                      }`}
                    >
                      {cat.replace('_', ' ')}
                    </button>
                  )
                )}
              </div>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={qaSearch}
                onChange={(e) => setQaSearch(e.target.value)}
                placeholder="Search screening questions or answers..."
                className="w-full text-xs font-medium pl-9 pr-4 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
              />
            </div>

            {/* QA Items List */}
            <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
              {filteredQa.map((item, idx) => {
                const qText = item.q || item.question_text || '';
                const aText = item.a || item.answer_text || '';
                const cat = item.cat || item.category || 'general';
                const id = item.id || idx;

                return (
                  <div
                    key={id}
                    className="liquid-glass rounded-2xl p-3.5 border border-white/90 shadow-2xs space-y-1.5 group hover:bg-white transition"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-bold text-xs text-zinc-900 leading-snug">{qText}</span>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-zinc-100 text-zinc-500 border border-zinc-200">
                          {cat}
                        </span>
                        <button
                          onClick={() => handleCopyText(aText, 'qa', id)}
                          className="liquid-pill p-1 rounded-lg text-zinc-500 hover:text-zinc-950 transition cursor-pointer shadow-2xs"
                          title="Copy Answer"
                        >
                          {copiedQaId === id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-zinc-700 font-medium leading-relaxed bg-zinc-50/70 p-2 rounded-xl border border-zinc-100 select-all">
                      {aText}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Add New QA Pair */}
            <form onSubmit={handleAddQaItem} className="p-4 rounded-2xl bg-white/70 border border-zinc-200 space-y-3">
              <span className="text-xs font-bold text-zinc-900 uppercase tracking-wider block">Add Custom Screening Question</span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <input
                  type="text"
                  value={newQuestion}
                  onChange={(e) => setNewQuestion(e.target.value)}
                  placeholder="Question text (e.g. Years of experience with Rust?)"
                  className="sm:col-span-2 text-xs px-3 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900"
                />
                <select
                  value={newQaCategory}
                  onChange={(e) => setNewQaCategory(e.target.value)}
                  className="text-xs px-3 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900 font-semibold"
                >
                  <option value="work_authorization">Work Auth</option>
                  <option value="availability">Availability</option>
                  <option value="compensation">Compensation</option>
                  <option value="location">Location</option>
                  <option value="tech_yoe">Tech Experience</option>
                  <option value="behavioral">Behavioral</option>
                  <option value="general">General</option>
                </select>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newAnswer}
                  onChange={(e) => setNewAnswer(e.target.value)}
                  placeholder="Answer text (e.g. 2+ years building microservices)"
                  className="flex-1 text-xs px-3 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900"
                />
                <button
                  type="submit"
                  disabled={addingQa || !newQuestion.trim() || !newAnswer.trim()}
                  className="liquid-pill px-4 py-2 rounded-xl bg-zinc-950 text-white font-bold text-xs hover:bg-zinc-800 cursor-pointer shadow-sm disabled:opacity-40"
                >
                  Add Pair
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================== TAB 7: RESUME & STORAGE PATHS ===================== */}
      {activeSubTab === 'resume' && (
        <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-5 animate-in fade-in duration-150">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-rose-600" />
                <span>Verified System Resume Documents & Active File Paths</span>
              </h3>
              <p className="text-xs text-zinc-500">
                Playwright application workers and API uploaders attach this exact PDF file to job application portals.
              </p>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
              <FolderCheck className="w-3 h-3 text-emerald-600" />
              <span>Verified & Active</span>
            </span>
          </div>

          {/* Active File Path Indicators */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3.5 rounded-2xl bg-white border border-zinc-200 shadow-2xs space-y-1">
              <span className="text-[10.5px] font-bold text-zinc-400 uppercase tracking-wider block">
                Primary PDF Upload Path
              </span>
              <div className="font-mono text-xs font-bold text-zinc-900 select-all break-all">
                {resumeFiles?.pdf_path || '/home/sameer/.applypilot/resume.pdf'}
              </div>
              <div className="text-[11px] text-zinc-500">Auto-attached during Playwright form filling</div>
            </div>

            <div className="p-3.5 rounded-2xl bg-white border border-zinc-200 shadow-2xs space-y-1">
              <span className="text-[10.5px] font-bold text-zinc-400 uppercase tracking-wider block">
                Repository Source Backup
              </span>
              <div className="font-mono text-xs font-bold text-zinc-900 select-all break-all">
                ./sameer-bagul-CV.pdf
              </div>
              <div className="text-[11px] text-zinc-500">Root folder synchronization copy (173.8 KB)</div>
            </div>
          </div>

          {/* Resume Raw Text Content */}
          <div className="space-y-1 pt-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">
                Full Resume Content Text (Parsed from my-experience.txt)
              </label>
              <button
                onClick={() => handleCopyText(resumeText, 'story')}
                className="liquid-pill px-2.5 py-1 rounded-xl text-[11px] font-bold text-zinc-700 hover:text-zinc-950 flex items-center gap-1 cursor-pointer shadow-2xs"
              >
                {copiedStory ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>Copy Full Resume Text</span>
              </button>
            </div>
            <textarea
              rows={12}
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              className="w-full text-xs font-mono p-3 rounded-xl bg-white/70 border border-zinc-200 text-zinc-800 leading-relaxed focus:bg-white"
            />
          </div>
        </div>
      )}

      {/* ===================== TAB 8: EEO LEGAL ===================== */}
      {activeSubTab === 'eeo' && (
        <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-5 animate-in fade-in duration-150">
          <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
            <Globe className="w-4 h-4 text-blue-600" />
            <span>Equal Employment Opportunity (EEO) Disclosures</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Gender</label>
              <input
                type="text"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Race / Ethnicity</label>
              <input
                type="text"
                value={race}
                onChange={(e) => setRace(e.target.value)}
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Veteran Status</label>
              <input
                type="text"
                value={veteranStatus}
                onChange={(e) => setVeteranStatus(e.target.value)}
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-600 uppercase tracking-wider">Disability Status</label>
              <input
                type="text"
                value={disabilityStatus}
                onChange={(e) => setDisabilityStatus(e.target.value)}
                className="w-full text-xs font-medium px-3.5 py-2 rounded-xl bg-white/70 border border-zinc-200 text-zinc-900"
              />
            </div>
          </div>
        </div>
      )}

      {/* ===================== TAB 9: AUTOMATION SETTINGS ===================== */}
      {activeSubTab === 'settings' && (
        <div className="liquid-glass rounded-3xl p-6 border border-white/90 shadow-xs space-y-5 animate-in fade-in duration-150">
          <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
            <Settings className="w-4 h-4 text-zinc-700" />
            <span>Playwright Engine & Autonomous Dispatch Settings</span>
          </h3>

          <div className="space-y-4 max-w-xl">
            <div className="flex items-center justify-between p-3.5 rounded-2xl bg-white border border-zinc-200">
              <div className="space-y-0.5">
                <span className="text-xs font-bold text-zinc-900 block">Browser Execution Mode</span>
                <span className="text-[11px] text-zinc-500">
                  Headed mode opens real visible Chrome browser windows; Headless runs silently in background.
                </span>
              </div>
              <div className="flex items-center gap-1">
                {(['headed', 'headless'] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setDefaultApplyMode(mode)}
                    className={`text-xs font-bold px-3 py-1.5 rounded-xl uppercase transition cursor-pointer ${
                      defaultApplyMode === mode
                        ? 'bg-zinc-950 text-white shadow-2xs'
                        : 'liquid-pill text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-2xl bg-white border border-zinc-200">
              <div className="space-y-0.5">
                <span className="text-xs font-bold text-zinc-900 block">Automatic Final Submission</span>
                <span className="text-[11px] text-zinc-500">
                  When disabled, the agent fills all form fields and pauses at the final review button for confirmation.
                </span>
              </div>
              <button
                onClick={() => setAutoSubmit(!autoSubmit)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer ${
                  autoSubmit ? 'bg-emerald-600' : 'bg-zinc-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    autoSubmit ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
