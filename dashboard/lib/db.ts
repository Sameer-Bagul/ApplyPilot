import { DatabaseSync } from 'node:sqlite';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';

let _db: DatabaseSync | null = null;

export function getApplypilotBin(): string {
  if (process.env.VIRTUAL_ENV && fs.existsSync(path.join(process.env.VIRTUAL_ENV, 'bin', 'applypilot'))) {
    return path.join(process.env.VIRTUAL_ENV, 'bin', 'applypilot');
  }
  const rootVenv = path.resolve(process.cwd(), '.venv/bin/applypilot');
  if (fs.existsSync(rootVenv)) return rootVenv;
  const parentVenv = path.resolve(process.cwd(), '../.venv/bin/applypilot');
  if (fs.existsSync(parentVenv)) return parentVenv;
  return 'applypilot';
}

export function getProjectRoot(): string {
  if (process.env.APPLYPILOT_PROJECT_ROOT && fs.existsSync(process.env.APPLYPILOT_PROJECT_ROOT)) {
    return process.env.APPLYPILOT_PROJECT_ROOT;
  }
  const cwd = process.cwd();
  if (fs.existsSync(path.join(cwd, 'src', 'applypilot'))) {
    return cwd;
  }
  const parent = path.resolve(cwd, '..');
  if (fs.existsSync(path.join(parent, 'src', 'applypilot'))) {
    return parent;
  }
  return cwd;
}

export function getPythonBin(): string {
  if (process.env.VIRTUAL_ENV && fs.existsSync(path.join(process.env.VIRTUAL_ENV, 'bin', 'python'))) {
    return path.join(process.env.VIRTUAL_ENV, 'bin', 'python');
  }
  const rootDir = getProjectRoot();
  const venvPython = path.join(rootDir, '.venv', 'bin', 'python');
  if (fs.existsSync(venvPython)) return venvPython;
  const rootVenv = path.resolve(process.cwd(), '.venv/bin/python');
  if (fs.existsSync(rootVenv)) return rootVenv;
  const parentVenv = path.resolve(process.cwd(), '../.venv/bin/python');
  if (fs.existsSync(parentVenv)) return parentVenv;
  return 'python';
}

export function getTransportStatus(): {
  mode: 'gmail_oauth' | 'smtp' | 'dev_mock';
  label: string;
  ready: boolean;
  user: string;
  details: string;
} {
  const gmailCredsPath = path.join(os.homedir(), '.gmail-mcp', 'credentials.json');
  const hasGmailOauth = fs.existsSync(gmailCredsPath);

  const smtpUser = process.env.SMTP_USER || process.env.APPLYPILOT_USER_EMAIL || '';
  const smtpPass = process.env.SMTP_PASS || '';
  const hasSmtp = Boolean(smtpUser && smtpPass);

  if (hasGmailOauth) {
    return {
      mode: 'gmail_oauth',
      label: 'Gmail API (OAuth)',
      ready: true,
      user: 'Authenticated via ~/.gmail-mcp/credentials.json',
      details: 'Direct integration with your Gmail Drafts & REST API sending.',
    };
  }

  if (hasSmtp) {
    return {
      mode: 'smtp',
      label: 'SMTP (App Password)',
      ready: true,
      user: smtpUser,
      details: `Connecting via ${process.env.SMTP_HOST || 'smtp.gmail.com'}:${process.env.SMTP_PORT || '587'} with TLS.`,
    };
  }

  return {
    mode: 'dev_mock',
    label: 'Ready (Local / Mock Mode)',
    ready: true,
    user: smtpUser || 'No credentials configured',
    details: 'You can test generating drafts & reading emails now. Configure SMTP_USER/SMTP_PASS or Gmail OAuth to dispatch real emails.',
  };
}

export function getDb(): DatabaseSync {
  if (_db) return _db;

  const dbPath = process.env.APPLYPILOT_DB_PATH || path.join(os.homedir(), '.applypilot', 'applypilot.db');
  
  try {
    const dbDir = path.dirname(dbPath);
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }
    // Open in read-write mode to support interactive CRUD operations
    _db = new DatabaseSync(dbPath);
    try {
      _db.exec(`
        CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
        CREATE INDEX IF NOT EXISTS idx_leads_company_name ON recruiter_leads(company_name);
        CREATE INDEX IF NOT EXISTS idx_watchlist_tier ON career_watchlist(priority_tier);
        CREATE INDEX IF NOT EXISTS idx_watchlist_vip ON career_watchlist(is_vip);
        CREATE INDEX IF NOT EXISTS idx_watchlist_name ON career_watchlist(company_name);
        CREATE INDEX IF NOT EXISTS idx_watchlist_area ON career_watchlist(area);
        CREATE INDEX IF NOT EXISTS idx_watchlist_stage ON career_watchlist(stage);
      `);
    } catch {}
    return _db;
  } catch (err) {
    throw new Error(`ApplyPilot database could not be opened at ${dbPath}: ${err}`);
  }
}

export interface StatsData {
  totalJobs: number;
  totalCompanies: number;
  totalLeads: number;
  vipCompanies: number;
  routes: {
    dualAttack: number;
    portalOnly: number;
    emailOnly: number;
  };
  topAts: Array<{ provider: string; count: number }>;
  topSectors: Array<{ sector: string; count: number }>;
  recentJobs: any[];
  recentLeads: any[];
  hitlCount: number;
  pendingReviewsCount: number;
  appliedCount: number;
}

export function getDashboardStats(): StatsData {
  const db = getDb();

  const totalJobs = (db.prepare('SELECT COUNT(*) as c FROM jobs').get() as any)?.c || 0;
  const totalCompanies = (db.prepare('SELECT COUNT(*) as c FROM career_watchlist').get() as any)?.c || 0;
  const totalLeads = (db.prepare('SELECT COUNT(*) as c FROM recruiter_leads').get() as any)?.c || 0;
  const vipCompanies = (db.prepare('SELECT COUNT(*) as c FROM career_watchlist WHERE is_vip = 1').get() as any)?.c || 0;
  const appliedCount = (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE (state = 'applied' OR apply_status = 'applied') AND state != 'ready_to_apply'").get() as any)?.c || 0;

  const dualAttack = (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE execution_route = 'DUAL_ATTACK'").get() as any)?.c || 0;
  const portalOnly = (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE execution_route = 'PORTAL_ONLY'").get() as any)?.c || 0;
  const emailOnly = (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE execution_route = 'EMAIL_ONLY'").get() as any)?.c || 0;

  const hitlCount = (db.prepare("SELECT COUNT(*) as c FROM hitl_tickets WHERE status != 'resolved'").get() as any)?.c || 0;
  const pendingReviewsCount = (db.prepare("SELECT COUNT(*) as c FROM recruiter_leads WHERE outreach_status IN ('pending_review', 'queued', 'drafted')").get() as any)?.c || 0;

  const topAts = db.prepare(`
    SELECT COALESCE(ats_provider, 'custom') as provider, COUNT(*) as count 
    FROM career_watchlist 
    WHERE ats_provider IS NOT NULL 
    GROUP BY ats_provider 
    ORDER BY count DESC 
    LIMIT 6
  `).all() as Array<{ provider: string; count: number }>;

  const topSectors = db.prepare(`
    SELECT COALESCE(sector, 'Technology') as sector, COUNT(*) as count 
    FROM career_watchlist 
    WHERE sector IS NOT NULL AND sector != '$undefined'
    GROUP BY sector 
    ORDER BY count DESC 
    LIMIT 6
  `).all() as Array<{ sector: string; count: number }>;

  const recentJobs = db.prepare(`
    SELECT url, title, company, location, site, execution_route, fit_score, discovered_at, state
    FROM jobs 
    ORDER BY discovered_at DESC NULLS LAST 
    LIMIT 8
  `).all();

  const recentLeads = db.prepare(`
    SELECT lead_id, company_name, contact_name, contact_email, role_title, contact_type, 
           contact_linkedin_url, linkedin_connection_note, outreach_status, created_at,
           email_draft_subject, email_draft_body, approved_at, approved_by
    FROM recruiter_leads 
    ORDER BY created_at DESC 
    LIMIT 8
  `).all();

  return {
    totalJobs,
    totalCompanies,
    totalLeads,
    vipCompanies,
    routes: {
      dualAttack,
      portalOnly,
      emailOnly,
    },
    topAts,
    topSectors,
    recentJobs,
    recentLeads,
    hitlCount,
    pendingReviewsCount,
    appliedCount,
  };
}

export function getJobs(params: {
  search?: string;
  route?: string;
  state?: string;
  minScore?: number;
  ats?: string;
  location?: string;
  workplace?: string;
  category?: string;
  sort?: string;
  page?: number;
  limit?: number;
}) {
  const db = getDb();
  const page = Math.max(1, params.page || 1);
  const limit = Math.min(100, Math.max(1, params.limit || 20));
  const offset = (page - 1) * limit;

  let query = `
    SELECT url, application_url, title, company, location, site, execution_route, fit_score, 
           discovered_at, applied_at, state, description, salary, score_reasoning,
           proof_video_path, proof_screenshot_path, proof_log_path, apply_status, metadata_json
    FROM jobs 
    WHERE 1=1
  `;
  const queryParams: any[] = [];

  if (params.search) {
    query += ` AND (title LIKE ? OR company LIKE ? OR description LIKE ? OR location LIKE ?)`;
    const s = `%${params.search}%`;
    queryParams.push(s, s, s, s);
  }

  if (params.route && params.route !== 'ALL') {
    query += ` AND execution_route = ?`;
    queryParams.push(params.route);
  }

  if (params.state && params.state !== 'ALL') {
    query += ` AND state = ?`;
    queryParams.push(params.state);
  }

  if (params.minScore !== undefined && !isNaN(params.minScore)) {
    query += ` AND fit_score >= ?`;
    queryParams.push(params.minScore);
  }

  if (params.location) {
    query += ` AND location LIKE ?`;
    queryParams.push(`%${params.location}%`);
  }

  if (params.workplace && params.workplace !== 'ALL') {
    const wp = params.workplace.toUpperCase();
    if (wp === 'REMOTE') {
      query += ` AND (metadata_json LIKE '%"workplace_type": "Remote"%' OR location LIKE '%Remote%' OR location LIKE '%Worldwide%' OR location LIKE '%Anywhere%')`;
    } else if (wp === 'HYBRID') {
      query += ` AND (metadata_json LIKE '%"workplace_type": "Hybrid"%' OR location LIKE '%Hybrid%')`;
    } else if (wp === 'ONSITE') {
      query += ` AND (metadata_json LIKE '%"workplace_type": "Onsite"%' OR (location NOT LIKE '%Remote%' AND location NOT LIKE '%Anywhere%'))`;
    }
  }

  if (params.category && params.category !== 'ALL') {
    const cat = params.category.toUpperCase();
    query += ` AND (metadata_json LIKE ? OR title LIKE ?)`;
    queryParams.push(`%"role_category": "${cat}"%`, `%${cat.replace('_', ' ')}%`);
  }

  if (params.ats && params.ats !== 'ALL') {
    if (params.ats === 'workday') {
      query += ` AND site LIKE '%workday%'`;
    } else if (params.ats === 'linkedin') {
      query += ` AND site LIKE '%linkedin%'`;
    } else if (params.ats === 'greenhouse') {
      query += ` AND site LIKE '%greenhouse%'`;
    } else if (params.ats === 'ashby') {
      query += ` AND site LIKE '%ashby%'`;
    } else if (params.ats === 'lever') {
      query += ` AND site LIKE '%lever%'`;
    } else if (params.ats === 'hackernews') {
      query += ` AND (site LIKE '%hackernews%' OR site LIKE '%ycombinator%')`;
    } else if (params.ats === 'smartrecruiters') {
      query += ` AND site LIKE '%smartrecruiters%'`;
    } else if (params.ats === 'naukri') {
      query += ` AND site LIKE '%naukri%'`;
    } else if (params.ats === 'internet_search') {
      query += ` AND (site LIKE '%google%' OR site LIKE '%company_careers%' OR site LIKE '%search%' OR site LIKE '%topstartups%')`;
    } else {
      query += ` AND site LIKE ?`;
      queryParams.push(`%${params.ats}%`);
    }
  }

  // Count total matching
  const countQuery = `SELECT COUNT(*) as c FROM (${query})`;
  const total = (db.prepare(countQuery).get(...queryParams) as any)?.c || 0;

  // Sorting / Ranking
  const sortMode = params.sort || 'ranked';
  if (sortMode === 'ranked' || sortMode === 'score') {
    query += ` ORDER BY fit_score DESC NULLS LAST, discovered_at DESC NULLS LAST LIMIT ? OFFSET ?`;
  } else if (sortMode === 'newest') {
    query += ` ORDER BY discovered_at DESC NULLS LAST LIMIT ? OFFSET ?`;
  } else if (sortMode === 'company') {
    query += ` ORDER BY company ASC, fit_score DESC NULLS LAST LIMIT ? OFFSET ?`;
  } else {
    query += ` ORDER BY fit_score DESC NULLS LAST, discovered_at DESC NULLS LAST LIMIT ? OFFSET ?`;
  }
  queryParams.push(limit, offset);

  const rawJobs = db.prepare(query).all(...queryParams) as any[];

  // Parse metadata_json safely for client UX
  const jobs = rawJobs.map((j) => {
    let parsedMetadata = null;
    if (j.metadata_json) {
      try {
        parsedMetadata = JSON.parse(j.metadata_json);
      } catch {}
    }
    return {
      ...j,
      metadata: parsedMetadata,
    };
  });

  return {
    jobs,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  };
}

export function getAppliedJobs(params: {
  search?: string;
  page?: number;
  limit?: number;
}) {
  const db = getDb();
  const page = Math.max(1, params.page || 1);
  const limit = Math.min(100, Math.max(1, params.limit || 20));
  const offset = (page - 1) * limit;

  let query = `
    SELECT url, application_url, title, company, location, site, execution_route, fit_score,
           discovered_at, applied_at, state, description, salary, score_reasoning,
           proof_video_path, proof_screenshot_path, proof_log_path, apply_status, apply_duration_ms
    FROM jobs
    WHERE (state = 'applied' OR apply_status = 'applied') AND state != 'ready_to_apply'
  `;
  const queryParams: any[] = [];

  if (params.search) {
    query += ` AND (title LIKE ? OR company LIKE ? OR location LIKE ?)`;
    const s = `%${params.search}%`;
    queryParams.push(s, s, s);
  }

  const countQuery = `SELECT COUNT(*) as c FROM (${query})`;
  const total = (db.prepare(countQuery).get(...queryParams) as any)?.c || 0;

  query += ` ORDER BY COALESCE(applied_at, discovered_at) DESC LIMIT ? OFFSET ?`;
  queryParams.push(limit, offset);

  const jobs = db.prepare(query).all(...queryParams);

  return {
    jobs,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  };
}

export function getJobDetail(url: string) {
  const db = getDb();
  const job: any = db.prepare('SELECT * FROM jobs WHERE url = ?').get(url);
  if (!job) return null;

  // Get state transitions
  let transitions: any[] = [];
  try {
    transitions = db.prepare(`
      SELECT from_state, to_state, at, reason, metadata 
      FROM job_state_transitions 
      WHERE job_url = ? 
      ORDER BY at DESC
    `).all(url);
  } catch {}

  // Get recruiter leads associated with this company or job
  let leads: any[] = [];
  try {
    leads = db.prepare(`
      SELECT lead_id, company_name, contact_name, contact_email, role_title, contact_type, 
             contact_linkedin_url, outreach_status, email_draft_subject, email_draft_body, created_at
      FROM recruiter_leads 
      WHERE (job_id = ? OR company_name = ?)
      ORDER BY created_at DESC
    `).all(url, job.company);
  } catch {}

  // Get company watchlist info if available
  let companyInfo: any = null;
  if (job.company) {
    try {
      companyInfo = db.prepare('SELECT * FROM career_watchlist WHERE company_name = ?').get(job.company);
    } catch {}
  }

  return {
    job,
    transitions,
    leads,
    companyInfo,
  };
}

export function createJob(data: {
  url: string;
  title: string;
  company: string;
  location?: string;
  salary?: string;
  description?: string;
  full_description?: string;
  execution_route?: string;
  fit_score?: number;
  score_reasoning?: string;
  state?: string;
  site?: string;
}) {
  const db = getDb();
  const now = new Date().toISOString();
  const route = data.execution_route || 'PORTAL_ONLY';
  const state = data.state || 'discovered';

  db.prepare(`
    INSERT OR REPLACE INTO jobs (
      url, title, company, location, salary, description, full_description,
      execution_route, fit_score, score_reasoning, state, site, discovered_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    data.url,
    data.title,
    data.company,
    data.location || 'Remote',
    data.salary || null,
    data.description || data.full_description || '',
    data.full_description || data.description || '',
    route,
    data.fit_score ?? null,
    data.score_reasoning ?? null,
    state,
    data.site || 'direct',
    now
  );

  return getJobDetail(data.url);
}

export function updateJob(url: string, updates: Partial<{
  title: string;
  company: string;
  location: string;
  salary: string;
  state: string;
  fit_score: number;
  score_reasoning: string;
  execution_route: string;
  full_description: string;
}>) {
  const db = getDb();
  const fields: string[] = [];
  const params: any[] = [];

  for (const [key, value] of Object.entries(updates)) {
    fields.push(`${key} = ?`);
    params.push(value);
  }

  if (fields.length === 0) return getJobDetail(url);

  params.push(url);
  db.prepare(`UPDATE jobs SET ${fields.join(', ')} WHERE url = ?`).run(...params);

  return getJobDetail(url);
}

export function deleteJob(url: string) {
  const db = getDb();
  return db.prepare('DELETE FROM jobs WHERE url = ?').run(url);
}

export function derivePuneCluster(area?: string | null, location?: string | null): string {
  const combined = `${area || ''} ${location || ''}`.toLowerCase();
  if (combined.includes('hinjawadi') || combined.includes('rgip')) return 'Hinjawadi';
  if (combined.includes('magarpatta') || combined.includes('hadapsar')) return 'Magarpatta';
  if (combined.includes('baner') || combined.includes('balewadi') || combined.includes('aundh')) return 'Baner';
  if (combined.includes('kharadi') || combined.includes('eon') || combined.includes('wtc')) return 'Kharadi';
  if (combined.includes('yerawada') || combined.includes('commerzone')) return 'Yerawada';
  if (combined.includes('viman') || combined.includes('kalyani')) return 'Viman Nagar';
  if (combined.includes('talawade') || combined.includes('pimpri') || combined.includes('chinchwad')) return 'PCMC';
  if (combined.includes('pune')) return 'Pune (Other)';
  if (/bengaluru|bangalore|hsr|koramangala|indiranagar|whitefield|manyata/.test(combined)) return 'Bengaluru';
  if (combined.includes('remote') || combined.includes('distributed')) return 'Remote';
  if (/us|usa|united states|san francisco|new york|seattle|california|london|uk/.test(combined)) return 'US / Global';
  return 'Global Tech';
}

function parseTechStack(techRadarJson?: string | null, intelStackJson?: string | null, intelTagsJson?: string | null): string[] {
  const set = new Set<string>();
  if (techRadarJson) {
    try {
      const parsed = JSON.parse(techRadarJson);
      if (Array.isArray(parsed)) {
        parsed.forEach((t) => typeof t === 'string' && set.add(t));
      } else if (parsed && typeof parsed === 'object') {
        if (Array.isArray(parsed.languages)) parsed.languages.forEach((t: any) => typeof t === 'string' && set.add(t));
        if (Array.isArray(parsed.frameworks)) parsed.frameworks.forEach((t: any) => typeof t === 'string' && set.add(t));
        if (Array.isArray(parsed.tools)) parsed.tools.forEach((t: any) => typeof t === 'string' && set.add(t));
      }
    } catch {}
  }
  if (intelStackJson) {
    try {
      const parsed = JSON.parse(intelStackJson);
      if (Array.isArray(parsed)) {
        parsed.forEach((t) => typeof t === 'string' && set.add(t));
      }
    } catch {}
  }
  if (intelTagsJson) {
    try {
      const parsed = JSON.parse(intelTagsJson);
      if (Array.isArray(parsed)) {
        parsed.forEach((t) => typeof t === 'string' && set.add(t));
      }
    } catch {}
  }
  return Array.from(set).slice(0, 6);
}

export interface GetCompaniesParams {
  search?: string;
  tier?: string; // 'all' | 'vip' | 'p1' | 'p2' | 'p3' | 'gtm_excluded'
  cluster?: string; // 'all' | 'pune' | 'magarpatta' | 'baner' | 'hinjawadi' | 'kharadi' | 'yerawada' | 'viman' | 'bangalore' | 'remote' | 'us'
  sector?: string;
  stage?: string;
  vipOnly?: boolean;
  hasContacts?: boolean | string;
  hasJobs?: boolean | string;
  ats?: string;
  sort?: string; // 'priority' | 'jobs_count' | 'leads_count' | 'name' | 'created_at'
  page?: number;
  limit?: number;
}

export function getCompanies(params: GetCompaniesParams) {
  const db = getDb();

  // Sync any newly discovered companies from jobs into the companies catalog
  try {
    db.prepare(`
      INSERT OR IGNORE INTO career_watchlist (company_name, priority_tier, is_vip, open_roles_count, last_checked_at)
      SELECT company, 2, 0, count(*), CURRENT_TIMESTAMP
      FROM jobs
      WHERE company IS NOT NULL AND trim(company) != '' AND company NOT IN (SELECT company_name FROM career_watchlist)
      GROUP BY company
    `).run();
  } catch {}

  const page = Math.max(1, params.page || 1);
  const limit = Math.min(100, Math.max(1, params.limit || 25));
  const offset = (page - 1) * limit;

  let where = 'WHERE 1=1';
  const queryParams: any[] = [];

  // Search filter (company name, domain, area, sector, location)
  if (params.search && params.search.trim()) {
    where += ` AND (cw.company_name LIKE ? OR cw.official_domain LIKE ? OR cw.area LIKE ? OR cw.sector LIKE ? OR cw.location LIKE ?)`;
    const s = `%${params.search.trim()}%`;
    queryParams.push(s, s, s, s, s);
  }

  // Tier filter: all, vip (Tier 1), p1, p2, p3, gtm_excluded
  if (params.tier === 'vip' || params.tier === 'p1' || params.vipOnly) {
    where += ` AND (cw.is_vip = 1 OR cw.priority_tier = 1) AND (cw.stage IS NULL OR cw.stage != 'gtm_excluded')`;
  } else if (params.tier === 'p2') {
    where += ` AND cw.priority_tier = 2 AND (cw.is_vip = 0 OR cw.is_vip IS NULL) AND (cw.stage IS NULL OR cw.stage != 'gtm_excluded')`;
  } else if (params.tier === 'p3') {
    where += ` AND cw.priority_tier = 3 AND (cw.stage IS NULL OR cw.stage != 'gtm_excluded')`;
  } else if (params.tier === 'gtm_excluded') {
    where += ` AND cw.stage = 'gtm_excluded'`;
  }

  // Cluster filter (Pune corridor or general location)
  if (params.cluster && params.cluster !== 'all') {
    const cl = params.cluster.toLowerCase();
    if (cl === 'pune' || cl === 'all_pune') {
      where += ` AND ((cw.area LIKE '%pune%' OR cw.area LIKE '%hinjawadi%' OR cw.area LIKE '%baner%' OR cw.area LIKE '%magarpatta%' OR cw.area LIKE '%kharadi%' OR cw.area LIKE '%yerawada%' OR cw.area LIKE '%viman%' OR cw.area LIKE '%talawade%' OR cw.area LIKE '%hadapsar%' OR cw.area LIKE '%aundh%' OR cw.area LIKE '%balewadi%') OR cw.location LIKE '%pune%')`;
    } else if (cl === 'magarpatta') {
      where += ` AND (cw.area LIKE '%magarpatta%' OR cw.area LIKE '%hadapsar%' OR cw.location LIKE '%magarpatta%')`;
    } else if (cl === 'baner') {
      where += ` AND (cw.area LIKE '%baner%' OR cw.area LIKE '%balewadi%' OR cw.area LIKE '%aundh%' OR cw.location LIKE '%baner%')`;
    } else if (cl === 'hinjawadi') {
      where += ` AND (cw.area LIKE '%hinjawadi%' OR cw.area LIKE '%rgip%' OR cw.location LIKE '%hinjawadi%')`;
    } else if (cl === 'kharadi') {
      where += ` AND (cw.area LIKE '%kharadi%' OR cw.area LIKE '%eon%' OR cw.area LIKE '%wtc%' OR cw.location LIKE '%kharadi%')`;
    } else if (cl === 'yerawada') {
      where += ` AND (cw.area LIKE '%yerawada%' OR cw.area LIKE '%commerzone%' OR cw.location LIKE '%yerawada%')`;
    } else if (cl === 'viman') {
      where += ` AND (cw.area LIKE '%viman%' OR cw.area LIKE '%kalyani%' OR cw.location LIKE '%viman%')`;
    } else if (cl === 'bangalore' || cl === 'bengaluru') {
      where += ` AND (cw.area LIKE '%bangalore%' OR cw.area LIKE '%bengaluru%' OR cw.area LIKE '%hsr%' OR cw.area LIKE '%koramangala%' OR cw.area LIKE '%indiranagar%' OR cw.area LIKE '%whitefield%' OR cw.location LIKE '%bangalore%' OR cw.location LIKE '%bengaluru%')`;
    } else if (cl === 'remote') {
      where += ` AND (cw.location LIKE '%remote%' OR cw.location LIKE '%distributed%' OR cw.area LIKE '%remote%')`;
    } else if (cl === 'us' || cl === 'global') {
      where += ` AND (cw.location LIKE '%us%' OR cw.location LIKE '%usa%' OR cw.location LIKE '%united states%' OR cw.location LIKE '%san francisco%' OR cw.location LIKE '%new york%' OR cw.location LIKE '%seattle%' OR cw.location LIKE '%california%')`;
    }
  }

  // Sector filter
  if (params.sector && params.sector !== 'ALL') {
    where += ` AND cw.sector LIKE ?`;
    queryParams.push(`%${params.sector}%`);
  }

  // Stage filter
  if (params.stage && params.stage !== 'ALL') {
    where += ` AND cw.stage LIKE ?`;
    queryParams.push(`%${params.stage}%`);
  }

  // Has Contacts filter
  if (params.hasContacts === true || params.hasContacts === 'true') {
    where += ` AND (EXISTS (SELECT 1 FROM recruiter_leads rl WHERE rl.company_name = cw.company_name) OR (cw.hr_contacts_json IS NOT NULL AND cw.hr_contacts_json != '[]'))`;
  } else if (params.hasContacts === false || params.hasContacts === 'false') {
    where += ` AND (NOT EXISTS (SELECT 1 FROM recruiter_leads rl WHERE rl.company_name = cw.company_name) AND (cw.hr_contacts_json IS NULL OR cw.hr_contacts_json = '[]'))`;
  }

  // Has Jobs filter
  if (params.hasJobs === true || params.hasJobs === 'true') {
    where += ` AND (cw.open_roles_count > 0 OR EXISTS (SELECT 1 FROM jobs j WHERE j.company = cw.company_name))`;
  } else if (params.hasJobs === false || params.hasJobs === 'false') {
    where += ` AND (COALESCE(cw.open_roles_count, 0) = 0 AND NOT EXISTS (SELECT 1 FROM jobs j WHERE j.company = cw.company_name))`;
  }

  // ATS Provider filter
  if (params.ats && params.ats !== 'ALL' && params.ats !== 'all') {
    const a = params.ats.toLowerCase();
    if (a === 'greenhouse') {
      where += ` AND (cw.ats_provider LIKE '%greenhouse%' OR cw.careers_page_url LIKE '%greenhouse%')`;
    } else if (a === 'lever') {
      where += ` AND (cw.ats_provider LIKE '%lever%' OR cw.careers_page_url LIKE '%lever%')`;
    } else if (a === 'ashby') {
      where += ` AND (cw.ats_provider LIKE '%ashby%' OR cw.careers_page_url LIKE '%ashby%')`;
    } else if (a === 'workday') {
      where += ` AND (cw.ats_provider LIKE '%workday%' OR cw.careers_page_url LIKE '%workday%')`;
    } else if (a === 'custom') {
      where += ` AND (cw.ats_provider = 'custom' OR (cw.ats_provider NOT IN ('greenhouse', 'lever', 'ashby', 'workday', 'ashbyhq', 'myworkdayjobs') AND cw.ats_provider IS NOT NULL))`;
    } else {
      where += ` AND (cw.ats_provider LIKE ? OR cw.careers_page_url LIKE ?)`;
      queryParams.push(`%${a}%`, `%${a}%`);
    }
  }

  // Count total matching records
  const countQuery = `SELECT COUNT(*) as c FROM career_watchlist cw ${where}`;
  const total = (db.prepare(countQuery).get(...queryParams) as any)?.c || 0;

  // Sorting
  let orderBy = 'ORDER BY cw.is_vip DESC, cw.priority_tier ASC, jobs_count DESC, leads_count DESC, cw.company_name ASC';
  if (params.sort === 'jobs_count') {
    orderBy = 'ORDER BY jobs_count DESC, cw.is_vip DESC, cw.company_name ASC';
  } else if (params.sort === 'leads_count') {
    orderBy = 'ORDER BY leads_count DESC, cw.is_vip DESC, cw.company_name ASC';
  } else if (params.sort === 'name') {
    orderBy = 'ORDER BY cw.company_name ASC';
  } else if (params.sort === 'created_at') {
    orderBy = 'ORDER BY cw.last_checked_at DESC NULLS LAST, cw.company_name ASC';
  }

  const query = `
    SELECT cw.company_id, cw.company_name, cw.official_domain, cw.careers_page_url, 
           cw.ats_provider, cw.priority_tier, cw.is_vip, cw.stage, cw.sector, cw.area, 
           cw.location, cw.team_size, cw.total_funding, cw.founders_json, 
           cw.hr_contacts_json, cw.tech_radar_json, cw.referral_available,
           cw.referrer_name, cw.referrer_linkedin, cw.wikipedia_summary,
           COALESCE((SELECT COUNT(*) FROM jobs j WHERE j.company = cw.company_name), cw.open_roles_count, 0) as jobs_count,
           (SELECT COUNT(*) FROM recruiter_leads rl WHERE rl.company_name = cw.company_name) as leads_count,
           cw.last_checked_at
    FROM career_watchlist cw
    ${where}
    ${orderBy}
    LIMIT ? OFFSET ?
  `;
  queryParams.push(limit, offset);

  const rawCompanies = db.prepare(query).all(...queryParams) as any[];

  // Batch fetch associated recruiter leads and tech intel for returned companies
  const companyNames = rawCompanies.map((c) => c.company_name).filter(Boolean);
  const officialDomains = rawCompanies.map((c) => c.official_domain).filter(Boolean);

  const leadsByCompany: Record<string, any[]> = {};
  if (companyNames.length > 0) {
    try {
      const placeholders = companyNames.map(() => '?').join(',');
      const leadRows = db.prepare(`
        SELECT company_name, contact_name, role_title, contact_email, personal_email,
               contact_linkedin_url, persona, contact_type, priority_score, outreach_status
        FROM recruiter_leads
        WHERE company_name IN (${placeholders})
        ORDER BY priority_score DESC, contact_email IS NOT NULL DESC
      `).all(...companyNames) as any[];

      for (const row of leadRows) {
        if (!leadsByCompany[row.company_name]) {
          leadsByCompany[row.company_name] = [];
        }
        if (leadsByCompany[row.company_name].length < 4) {
          leadsByCompany[row.company_name].push({
            name: row.contact_name || 'Hiring Lead',
            title: row.role_title || 'Recruiting Team',
            email: row.contact_email || row.personal_email || null,
            linkedin: row.contact_linkedin_url || null,
            persona: row.persona || row.contact_type || 'Recruiter',
            score: row.priority_score || 0,
            status: row.outreach_status || 'discovered',
          });
        }
      }
    } catch {}
  }

  const intelByCompany: Record<string, any> = {};
  if (officialDomains.length > 0 || companyNames.length > 0) {
    try {
      const dPlaceholders = officialDomains.map(() => '?').join(',');
      const nPlaceholders = companyNames.map(() => '?').join(',');
      const conditions: string[] = [];
      const intelParams: any[] = [];

      if (officialDomains.length > 0) {
        conditions.push(`official_domain IN (${dPlaceholders})`);
        intelParams.push(...officialDomains);
      }
      if (companyNames.length > 0) {
        conditions.push(`company_name IN (${nPlaceholders})`);
        intelParams.push(...companyNames);
      }

      if (conditions.length > 0) {
        const intelRows = db.prepare(`
          SELECT company_name, official_domain, tech_stack_json, ai_focus_tags,
                 detected_email_pattern, email_pattern_confidence, wikipedia_summary
          FROM company_intel
          WHERE ${conditions.join(' OR ')}
        `).all(...intelParams) as any[];

        for (const r of intelRows) {
          if (r.company_name) intelByCompany[r.company_name] = r;
          if (r.official_domain) intelByCompany[r.official_domain] = r;
        }
      }
    } catch {}
  }

  const companies = rawCompanies.map((c: any) => {
    let founders = [];
    let hrEmails = [];
    try {
      if (c.founders_json) founders = JSON.parse(c.founders_json);
    } catch {}
    try {
      if (c.hr_contacts_json) hrEmails = JSON.parse(c.hr_contacts_json);
    } catch {}

    const intel = intelByCompany[c.company_name] || intelByCompany[c.official_domain];
    const tech_stack = parseTechStack(c.tech_radar_json, intel?.tech_stack_json, intel?.ai_focus_tags);
    const pune_cluster = derivePuneCluster(c.area, c.location);

    // Build persons preview (prioritizing recruiter_leads, falling back to parsed founders & HR emails)
    let persons = leadsByCompany[c.company_name] || [];
    if (persons.length === 0) {
      const fallbackPersons: any[] = [];
      if (Array.isArray(founders)) {
        for (const f of founders) {
          if (f && typeof f === 'object') {
            if (f.name && f.name !== 'null') {
              fallbackPersons.push({
                name: f.name,
                title: f.title || 'Founder / Leadership',
                email: f.email || null,
                linkedin: f.linkedin || (Array.isArray(f.linkedin_urls) ? f.linkedin_urls[0] : null),
                persona: 'Founder',
                score: 85,
              });
            } else if (f.names) {
              const split = String(f.names).split(',').map((s) => s.trim()).filter(Boolean);
              split.forEach((nm, idx) => {
                fallbackPersons.push({
                  name: nm,
                  title: 'Founder / Leadership',
                  email: null,
                  linkedin: Array.isArray(f.founder_links) ? f.founder_links[idx] : null,
                  persona: 'Founder',
                  score: 85,
                });
              });
            }
          }
        }
      }
      if (Array.isArray(hrEmails)) {
        for (const email of hrEmails) {
          if (typeof email === 'string' && email.includes('@')) {
            const prefix = email.split('@')[0].replace(/[._]/g, ' ');
            const formatted = prefix.charAt(0).toUpperCase() + prefix.slice(1);
            fallbackPersons.push({
              name: formatted || 'HR Lead',
              title: 'Talent Acquisition',
              email: email,
              linkedin: null,
              persona: 'Recruiter',
              score: 75,
            });
          }
        }
      }
      persons = fallbackPersons.slice(0, 4);
    }

    return {
      ...c,
      open_roles_count: c.jobs_count,
      pune_cluster,
      tech_stack,
      persons,
      founders,
      emails: hrEmails,
      detected_email_pattern: intel?.detected_email_pattern || null,
      email_pattern_confidence: intel?.email_pattern_confidence || null,
      wikipedia_summary: c.wikipedia_summary || intel?.wikipedia_summary || null,
      referral_available: Boolean(c.referral_available),
      referrer_name: c.referrer_name || null,
      referrer_linkedin: c.referrer_linkedin || null,
    };
  });

  return {
    companies,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  };
}

export function getCompanyDetail(params: { id?: string; name?: string }) {
  const db = getDb();
  let company: any = null;

  if (params.id) {
    company = db
      .prepare('SELECT * FROM career_watchlist WHERE company_id = ?')
      .get(params.id);
  } else if (params.name) {
    company = db
      .prepare('SELECT * FROM career_watchlist WHERE company_name = ?')
      .get(params.name);
  }

  if (!company) {
    return null;
  }

  let founders = [];
  let emails = [];
  let topProjects = [];
  let techRadar = null;
  try {
    if (company.founders_json) founders = JSON.parse(company.founders_json);
  } catch {}
  try {
    if (company.hr_contacts_json) emails = JSON.parse(company.hr_contacts_json);
  } catch {}
  try {
    if (company.top_projects_json) topProjects = JSON.parse(company.top_projects_json);
  } catch {}
  try {
    if (company.tech_radar_json) techRadar = JSON.parse(company.tech_radar_json);
  } catch {}

  // Fetch company intel if available
  let intel: any = null;
  try {
    intel = db.prepare(`
      SELECT wikipedia_summary, detected_email_pattern, email_pattern_confidence,
             tech_stack_json, ai_focus_tags, hiring_posts_json, key_people_json
      FROM company_intel
      WHERE domain_or_name = ? OR official_domain = ? OR company_name = ?
      LIMIT 1
    `).get(company.official_domain || '', company.official_domain || '', company.company_name);
  } catch {}

  const pune_cluster = derivePuneCluster(company.area, company.location);
  const tech_stack = parseTechStack(company.tech_radar_json, intel?.tech_stack_json, intel?.ai_focus_tags);

  // Fetch all leads for this company
  const leads = db
    .prepare(
      `SELECT lead_id, job_id, company_name, company_domain, role_title,
              contact_name, contact_email, personal_email, personal_email_source, preferred_channel,
              contact_type, contact_linkedin_url,
              linkedin_connection_note, source_platform, evidence_snippet,
              execution_route, outreach_status, created_at, persona, priority_score,
              email_draft_subject, email_draft_body, approved_at, approved_by,
              mx_provider, is_deliverable
       FROM recruiter_leads
       WHERE company_name = ?
       ORDER BY priority_score DESC, contact_type ASC, created_at DESC`
    )
    .all(company.company_name);

  // Fetch all open jobs for this company
  const jobs = db
    .prepare(
      `SELECT url, title, company, location, site, execution_route,
              fit_score, discovered_at, state, salary
       FROM jobs
       WHERE company = ?
       ORDER BY discovered_at DESC
       LIMIT 50`
    )
    .all(company.company_name);

  return {
    company: {
      ...company,
      pune_cluster,
      tech_stack,
      founders,
      emails,
      topProjects,
      techRadar,
      detected_email_pattern: intel?.detected_email_pattern || null,
      email_pattern_confidence: intel?.email_pattern_confidence || null,
      wikipedia_summary: company.wikipedia_summary || intel?.wikipedia_summary || null,
      referral_available: Boolean(company.referral_available),
      referrer_name: company.referrer_name || null,
      referrer_linkedin: company.referrer_linkedin || null,
    },
    leads,
    jobs,
    stats: {
      totalLeads: leads.length,
      totalJobs: jobs.length,
      verifiedEmails: leads.map((l: any) => l.contact_email).filter(Boolean),
      hasDualAttack: leads.length > 0 && (jobs.length > 0 || Boolean(company.careers_page_url)),
      puneCluster: pune_cluster,
      detectedEmailPattern: intel?.detected_email_pattern || null,
    },
  };
}

export function createCompany(data: {
  company_name: string;
  official_domain?: string;
  careers_page_url?: string;
  ats_provider?: string;
  sector?: string;
  stage?: string;
  location?: string;
  priority_tier?: number;
  is_vip?: number;
}) {
  const db = getDb();
  const company_id = `comp_${Math.random().toString(36).substring(2, 10)}`;
  const slug = data.company_name.toLowerCase().replace(/[^a-z0-9]+/g, '-');

  db.prepare(`
    INSERT INTO career_watchlist (
      company_id, company_name, slug, official_domain, careers_page_url,
      ats_provider, sector, stage, location, priority_tier, is_vip, open_roles_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
  `).run(
    company_id,
    data.company_name,
    slug,
    data.official_domain || null,
    data.careers_page_url || null,
    data.ats_provider || 'custom',
    data.sector || 'Technology',
    data.stage || 'Growth',
    data.location || 'Remote',
    data.priority_tier ?? 2,
    data.is_vip ?? 0
  );

  return getCompanyDetail({ id: company_id });
}

export function updateCompany(company_id: string, updates: Partial<{
  company_name: string;
  official_domain: string;
  careers_page_url: string;
  ats_provider: string;
  sector: string;
  stage: string;
  location: string;
  priority_tier: number;
  is_vip: number;
}>) {
  const db = getDb();
  const fields: string[] = [];
  const params: any[] = [];

  for (const [key, value] of Object.entries(updates)) {
    fields.push(`${key} = ?`);
    params.push(value);
  }

  if (fields.length === 0) return getCompanyDetail({ id: company_id });

  params.push(company_id);
  db.prepare(`UPDATE career_watchlist SET ${fields.join(', ')} WHERE company_id = ?`).run(...params);

  return getCompanyDetail({ id: company_id });
}

export function deleteCompany(company_id: string) {
  const db = getDb();
  return db.prepare('DELETE FROM career_watchlist WHERE company_id = ?').run(company_id);
}

export function getLeads(params: {
  search?: string;
  type?: string;
  status?: string;
  persona?: string;
  minScore?: number;
  sortBy?: string;
  page?: number;
  limit?: number;
}) {
  const db = getDb();
  const page = Math.max(1, params.page || 1);
  const limit = Math.min(100, Math.max(1, params.limit || 20));
  const offset = (page - 1) * limit;

  let query = `
    SELECT lead_id, job_id, company_name, company_domain, role_title, 
           contact_name, contact_email, personal_email, personal_email_source, preferred_channel,
           contact_type, contact_linkedin_url, 
           linkedin_connection_note, source_platform, evidence_snippet, 
           execution_route, outreach_status, created_at,
           COALESCE(email_subject, email_draft_subject) as email_subject,
           COALESCE(email_body_text, email_draft_body) as email_body_text,
           email_draft_subject, email_draft_body, email_body_html,
           persona, priority_score, gmail_draft_id, gmail_thread_id,
           approved_at, approved_by,
           mx_provider, is_deliverable, is_catch_all,
           matched_job_title, matched_job_url,
           followup_draft_subject, followup_draft_body, dual_attack_pair_id
    FROM recruiter_leads 
    WHERE 1=1
  `;
  const queryParams: any[] = [];

  if (params.search) {
    query += ` AND (company_name LIKE ? OR contact_name LIKE ? OR contact_email LIKE ? OR role_title LIKE ?)`;
    const s = `%${params.search}%`;
    queryParams.push(s, s, s, s);
  }

  if (params.type && params.type !== 'ALL') {
    query += ` AND contact_type = ?`;
    queryParams.push(params.type);
  }

  if (params.persona && params.persona !== 'ALL') {
    query += ` AND (persona = ? OR (persona IS NULL AND contact_type = ?))`;
    queryParams.push(params.persona, params.persona);
  }

  if (params.minScore !== undefined && !isNaN(params.minScore) && params.minScore > 0) {
    query += ` AND priority_score >= ?`;
    queryParams.push(params.minScore);
  }

  if (params.status && params.status !== 'ALL') {
    if (params.status === 'pending_review') {
      query += ` AND outreach_status IN ('pending_review', 'queued', 'drafted')`;
    } else {
      query += ` AND outreach_status = ?`;
      queryParams.push(params.status);
    }
  }

  const countQuery = `SELECT COUNT(*) as c FROM (${query})`;
  const total = (db.prepare(countQuery).get(...queryParams) as any)?.c || 0;

  if (params.sortBy === 'priority' || params.sortBy === 'score') {
    query += ` ORDER BY priority_score DESC, created_at DESC LIMIT ? OFFSET ?`;
  } else {
    query += ` ORDER BY created_at DESC LIMIT ? OFFSET ?`;
  }
  queryParams.push(limit, offset);

  const rawLeads: any[] = db.prepare(query).all(...queryParams);

  // Attach company intel summary & resume info
  const leads = rawLeads.map((lead) => {
    let intel: any = null;
    if (lead.company_domain || lead.company_name) {
      try {
        const row: any = db.prepare(`
          SELECT wikipedia_summary, tech_stack_json, ai_focus_tags, open_roles_json
          FROM company_intel
          WHERE official_domain = ? OR domain_or_name = ? OR company_name = ?
          LIMIT 1
        `).get(lead.company_domain || '', lead.company_domain || '', lead.company_name || '');
        if (row) {
          let techStack: string[] = [];
          let aiTags: string[] = [];
          let openRolesCount = 0;
          try { techStack = JSON.parse(row.tech_stack_json || '[]'); } catch {}
          try { aiTags = JSON.parse(row.ai_focus_tags || '[]'); } catch {}
          try { openRolesCount = (JSON.parse(row.open_roles_json || '[]') || []).length; } catch {}
          intel = {
            summary: row.wikipedia_summary ? row.wikipedia_summary.slice(0, 160) + '...' : null,
            tech_stack: techStack.slice(0, 6),
            ai_focus_tags: aiTags.slice(0, 4),
            open_roles_count: openRolesCount,
          };
        }
      } catch {}
    }

    return {
      ...lead,
      intel,
    };
  });

  return {
    leads,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  };
}

export function getLeadDetail(lead_id: string) {
  const db = getDb();
  const lead: any = db.prepare(`
    SELECT *,
           COALESCE(email_subject, email_draft_subject) as email_subject,
           COALESCE(email_body_text, email_draft_body) as email_body_text
    FROM recruiter_leads 
    WHERE lead_id = ? OR lead_id LIKE (? || '%')
  `).get(lead_id, lead_id);

  if (!lead) return null;

  // Linked company info from career_watchlist
  let companyInfo: any = null;
  if (lead.company_name) {
    try {
      companyInfo = db.prepare('SELECT * FROM career_watchlist WHERE company_name = ?').get(lead.company_name);
    } catch {}
  }

  // Linked company intel from 30-day cache table company_intel
  let companyIntel: any = null;
  if (lead.company_domain || lead.company_name) {
    try {
      const intelRow: any = db.prepare(`
        SELECT * FROM company_intel 
        WHERE official_domain = ? OR domain_or_name = ? OR company_name = ?
        LIMIT 1
      `).get(lead.company_domain || '', lead.company_domain || '', lead.company_name || '');
      if (intelRow) {
        let tech_stack: string[] = [];
        let open_roles: any[] = [];
        let ai_focus_tags: string[] = [];
        let key_people: any[] = [];
        let hiring_posts: any[] = [];
        try { tech_stack = JSON.parse(intelRow.tech_stack_json || '[]'); } catch {}
        try { open_roles = JSON.parse(intelRow.open_roles_json || '[]'); } catch {}
        try { ai_focus_tags = JSON.parse(intelRow.ai_focus_tags || '[]'); } catch {}
        try { key_people = JSON.parse(intelRow.key_people_json || '[]'); } catch {}
        try { hiring_posts = JSON.parse(intelRow.hiring_posts_json || '[]'); } catch {}
        companyIntel = {
          ...intelRow,
          tech_stack,
          open_roles,
          ai_focus_tags,
          key_people,
          hiring_posts,
        };
      }
    } catch {}
  }

  // Linked open jobs from jobs table
  let openJobs: any[] = [];
  if (lead.company_name) {
    try {
      openJobs = db.prepare('SELECT url, title, location, fit_score, site FROM jobs WHERE company = ? LIMIT 10').all(lead.company_name);
    } catch {}
  }

  // Resume check
  const tailoredDir = path.join(os.homedir(), '.applypilot', 'tailored_resumes');
  const baseResume = path.join(os.homedir(), '.applypilot', 'resume.pdf');
  let resumePath: string | null = null;
  let resumeExists = false;

  if (fs.existsSync(tailoredDir)) {
    try {
      const files = fs.readdirSync(tailoredDir);
      const match = files.find((f) => lead.company_name && f.toLowerCase().includes(lead.company_name.toLowerCase()) && f.endsWith('.pdf'));
      if (match) {
        resumePath = path.join(tailoredDir, match);
        resumeExists = true;
      } else if (files.length > 0 && files.some((f) => f.endsWith('.pdf'))) {
        const first = files.find((f) => f.endsWith('.pdf'))!;
        resumePath = path.join(tailoredDir, first);
        resumeExists = true;
      }
    } catch {}
  }
  if (!resumeExists && fs.existsSync(baseResume)) {
    resumePath = baseResume;
    resumeExists = true;
  }

  return {
    lead,
    companyInfo,
    companyIntel,
    openJobs,
    resume: {
      path: resumePath,
      exists: resumeExists,
      filename: resumePath ? path.basename(resumePath) : null,
    },
    transport: getTransportStatus(),
  };
}

export function createLead(data: {
  company_name: string;
  contact_email: string;
  contact_name?: string;
  role_title?: string;
  contact_type?: string;
  contact_linkedin_url?: string;
  company_domain?: string;
  execution_route?: string;
  email_draft_subject?: string;
  email_draft_body?: string;
  email_subject?: string;
  email_body_text?: string;
  persona?: string;
  priority_score?: number;
}) {
  const db = getDb();
  const lead_id = `lead_${Math.random().toString(36).substring(2, 12)}`;
  const now = new Date().toISOString();

  const subject = data.email_subject || data.email_draft_subject || `Application & Introduction: ${data.role_title || 'Software Engineer'}`;
  const bodyText = data.email_body_text || data.email_draft_body || `Hi ${data.contact_name || 'Hiring Team'},\n\nI noticed the open role at ${data.company_name} and wanted to reach out directly with my background in high-performance distributed systems and AI agents.`;

  db.prepare(`
    INSERT OR REPLACE INTO recruiter_leads (
      lead_id, company_name, contact_email, contact_name, role_title,
      contact_type, contact_linkedin_url, company_domain, execution_route,
      outreach_status, email_draft_subject, email_draft_body,
      email_subject, email_body_text, persona, priority_score, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review', ?, ?, ?, ?, ?, ?, ?)
  `).run(
    lead_id,
    data.company_name,
    data.contact_email,
    data.contact_name || 'Hiring Manager',
    data.role_title || 'Engineering Lead',
    data.contact_type || 'talent_partner',
    data.contact_linkedin_url || null,
    data.company_domain || (data.contact_email.split('@')[1] || null),
    data.execution_route || 'DUAL_ATTACK',
    subject,
    bodyText,
    subject,
    bodyText,
    data.persona || 'founder',
    data.priority_score || 0,
    now
  );

  return getLeadDetail(lead_id);
}

export function updateLead(lead_id: string, updates: Partial<{
  contact_name: string;
  contact_email: string;
  personal_email: string;
  personal_email_source: string;
  preferred_channel: string;
  role_title: string;
  contact_type: string;
  persona: string;
  priority_score: number;
  contact_linkedin_url: string;
  outreach_status: string;
  email_draft_subject: string;
  email_draft_body: string;
  email_subject: string;
  email_body_text: string;
  email_body_html: string;
  gmail_draft_id: string;
  approved_at: string;
  approved_by: string;
  mx_provider: string;
  is_deliverable: number;
  is_catch_all: number;
  matched_job_title: string;
  matched_job_url: string;
  followup_draft_subject: string;
  followup_draft_body: string;
  dual_attack_pair_id: string;
  execution_route: string;
}>) {
  const db = getDb();
  const fields: string[] = [];
  const params: any[] = [];

  // Ensure compatibility between email_subject / email_draft_subject
  const finalUpdates: any = { ...updates };
  if (finalUpdates.email_subject && !finalUpdates.email_draft_subject) {
    finalUpdates.email_draft_subject = finalUpdates.email_subject;
  } else if (finalUpdates.email_draft_subject && !finalUpdates.email_subject) {
    finalUpdates.email_subject = finalUpdates.email_draft_subject;
  }

  if (finalUpdates.email_body_text && !finalUpdates.email_draft_body) {
    finalUpdates.email_draft_body = finalUpdates.email_body_text;
  } else if (finalUpdates.email_draft_body && !finalUpdates.email_body_text) {
    finalUpdates.email_body_text = finalUpdates.email_draft_body;
  }

  const ALLOWED_LEAD_COLUMNS = new Set([
    'contact_name',
    'contact_email',
    'personal_email',
    'personal_email_source',
    'preferred_channel',
    'role_title',
    'contact_type',
    'contact_linkedin_url',
    'linkedin_connection_note',
    'company_name',
    'company_domain',
    'persona',
    'priority_score',
    'outreach_status',
    'email_draft_subject',
    'email_draft_body',
    'email_subject',
    'email_body_text',
    'email_body_html',
    'gmail_draft_id',
    'gmail_thread_id',
    'approved_at',
    'approved_by',
    'mx_provider',
    'is_deliverable',
    'is_catch_all',
    'matched_job_title',
    'matched_job_url',
    'followup_draft_subject',
    'followup_draft_body',
    'dual_attack_pair_id',
    'execution_route',
  ]);

  for (const [key, value] of Object.entries(finalUpdates)) {
    if (ALLOWED_LEAD_COLUMNS.has(key)) {
      fields.push(`${key} = ?`);
      params.push(value);
    }
  }

  if (fields.length === 0) return getLeadDetail(lead_id);

  params.push(lead_id, lead_id);
  db.prepare(`UPDATE recruiter_leads SET ${fields.join(', ')} WHERE lead_id = ? OR lead_id LIKE (? || '%')`).run(...params);

  return getLeadDetail(lead_id);
}

export function getTopPickStats() {
  const db = getDb();
  const totalLeads = (db.prepare('SELECT COUNT(*) as c FROM recruiter_leads').get() as any)?.c || 0;
  const topPicksCount = (db.prepare('SELECT COUNT(*) as c FROM recruiter_leads WHERE priority_score >= 60').get() as any)?.c || 0;
  const draftedCount = (db.prepare("SELECT COUNT(*) as c FROM recruiter_leads WHERE outreach_status = 'drafted'").get() as any)?.c || 0;
  const pendingReviewCount = (db.prepare("SELECT COUNT(*) as c FROM recruiter_leads WHERE outreach_status = 'pending_review'").get() as any)?.c || 0;
  const sentCount = (db.prepare("SELECT COUNT(*) as c FROM recruiter_leads WHERE outreach_status = 'sent'").get() as any)?.c || 0;
  const avgScore = (db.prepare('SELECT AVG(priority_score) as a FROM recruiter_leads WHERE priority_score > 0').get() as any)?.a || 0;

  return {
    totalLeads,
    topPicksCount,
    draftedCount,
    pendingReviewCount,
    sentCount,
    averageScore: Math.round(avgScore),
    transport: getTransportStatus(),
  };
}

export function approveLead(lead_id: string, approvedBy: string = 'admin') {
  const db = getDb();
  const now = new Date().toISOString();
  db.prepare(`
    UPDATE recruiter_leads 
    SET outreach_status = 'approved', approved_at = ?, approved_by = ?
    WHERE lead_id = ? OR lead_id LIKE (? || '%')
  `).run(now, approvedBy, lead_id, lead_id);

  return getLeadDetail(lead_id);
}

export function rejectLead(lead_id: string) {
  const db = getDb();
  db.prepare(`
    UPDATE recruiter_leads 
    SET outreach_status = 'rejected'
    WHERE lead_id = ? OR lead_id LIKE (? || '%')
  `).run(lead_id, lead_id);

  return getLeadDetail(lead_id);
}

export function deleteLead(lead_id: string) {
  const db = getDb();
  return db.prepare("DELETE FROM recruiter_leads WHERE lead_id = ? OR lead_id LIKE (? || '%')").run(lead_id, lead_id);
}

// HITL Tickets
export function getHitlTickets(params: { status?: string; blocker_type?: string; page?: number; limit?: number }) {
  const db = getDb();
  const page = Math.max(1, params.page || 1);
  const limit = Math.min(100, Math.max(1, params.limit || 20));
  const offset = (page - 1) * limit;

  let query = `
    SELECT ticket_id, job_url, lead_id, company, role_title, blocker_type, 
           status, unanswered_questions_json, created_at, resolved_at
    FROM hitl_tickets
    WHERE 1=1
  `;
  const queryParams: any[] = [];

  if (params.status && params.status !== 'ALL') {
    if (params.status === 'pending') {
      query += ` AND status IN ('pending', 'sent')`;
    } else {
      query += ` AND status = ?`;
      queryParams.push(params.status);
    }
  }

  if (params.blocker_type && params.blocker_type !== 'ALL') {
    if (params.blocker_type === 'captcha') {
      query += ` AND blocker_type = 'captcha'`;
    } else if (params.blocker_type === 'missing_info') {
      query += ` AND (blocker_type != 'captcha' OR blocker_type IS NULL)`;
    } else {
      query += ` AND blocker_type = ?`;
      queryParams.push(params.blocker_type);
    }
  }

  const countQuery = `SELECT COUNT(*) as c FROM (${query})`;
  const total = (db.prepare(countQuery).get(...queryParams) as any)?.c || 0;

  query += ` ORDER BY created_at DESC LIMIT ? OFFSET ?`;
  queryParams.push(limit, offset);

  const rawTickets = db.prepare(query).all(...queryParams);

  const tickets = rawTickets.map((t: any) => {
    let questions = [];
    try {
      if (t.unanswered_questions_json) questions = JSON.parse(t.unanswered_questions_json);
    } catch {}
    return {
      ...t,
      questions,
    };
  });

  const countsQuery = `
    SELECT 
      SUM(CASE WHEN status IN ('pending', 'sent') THEN 1 ELSE 0 END) as pending_total,
      SUM(CASE WHEN status IN ('pending', 'sent') AND blocker_type = 'captcha' THEN 1 ELSE 0 END) as pending_captcha,
      SUM(CASE WHEN status IN ('pending', 'sent') AND (blocker_type != 'captcha' OR blocker_type IS NULL) THEN 1 ELSE 0 END) as pending_missing,
      SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved_total
    FROM hitl_tickets
  `;
  const countsRow: any = db.prepare(countsQuery).get() || {};

  return {
    tickets,
    counts: {
      pending: Number(countsRow.pending_total || 0),
      captcha: Number(countsRow.pending_captcha || 0),
      missing: Number(countsRow.pending_missing || 0),
      resolved: Number(countsRow.resolved_total || 0),
    },
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  };
}

export function getHitlTicketDetail(ticket_id: number) {
  const db = getDb();
  const ticket: any = db.prepare('SELECT * FROM hitl_tickets WHERE ticket_id = ?').get(ticket_id);
  if (!ticket) return null;

  let questions = [];
  try {
    if (ticket.unanswered_questions_json) questions = JSON.parse(ticket.unanswered_questions_json);
  } catch {}

  return {
    ...ticket,
    questions,
  };
}

export function resolveHitlTicket(ticket_id: number, answers: any) {
  const db = getDb();
  const now = new Date().toISOString();
  db.prepare(`
    UPDATE hitl_tickets 
    SET status = 'resolved', resolved_at = ?
    WHERE ticket_id = ?
  `).run(now, ticket_id);

  return getHitlTicketDetail(ticket_id);
}

export function deleteHitlTicket(ticket_id: number) {
  const db = getDb();
  return db.prepare('DELETE FROM hitl_tickets WHERE ticket_id = ?').run(ticket_id);
}

export function getPipelineTelemetry() {
  const db = getDb();

  // 1. Check for traces from apply_traces
  let traces: any[] = [];
  try {
    traces = db
      .prepare(
        `SELECT trace_id, job_url, ats_type, step_index, action, selector, status, duration_ms, created_at
         FROM apply_traces
         ORDER BY created_at DESC
         LIMIT 20`
      )
      .all();
  } catch {}

  // 2. Fetch latest recruiter lead events (Looper & Discovery)
  let latestLeads: any[] = [];
  try {
    latestLeads = db
      .prepare(
        `SELECT lead_id, company_name, contact_name, contact_email, role_title, contact_type, source_platform, execution_route, created_at
         FROM recruiter_leads
         ORDER BY created_at DESC
         LIMIT 15`
      )
      .all();
  } catch {}

  // 3. Fetch latest jobs (ATS Radar & Launch Detector)
  let latestJobs: any[] = [];
  try {
    latestJobs = db
      .prepare(
        `SELECT url, title, company, location, site, execution_route, discovered_at, state
         FROM jobs
         ORDER BY discovered_at DESC
         LIMIT 15`
      )
      .all();
  } catch {}

  // 4. Fetch watchlist status
  let watchlistStats: any = { total: 0, vip: 0 };
  try {
    watchlistStats = {
      total: (db.prepare('SELECT COUNT(*) as c FROM career_watchlist').get() as any)?.c || 0,
      vip: (db.prepare('SELECT COUNT(*) as c FROM career_watchlist WHERE is_vip = 1').get() as any)?.c || 0,
    };
  } catch {}

  // Map real database events into DAG nodes
  const liveNodes: any[] = [];

  // Root orchestrator
  liveNodes.push({
    id: 'root-orchestrator',
    lane: 0,
    text: 'Autonomous Pipeline Engine',
    desc: 'Master brain coordinating FreeHire Direct ATS, Local Matcher, Marathon Looper, and HITL Mailer',
    category: 'system',
    status: 'done',
    time: 'Running',
    command: 'applypilot marathon --loop-minutes 60',
    agent: 'applypilot-brain',
    route: 'DUAL_ATTACK',
    inputs: { watchlist_monitored: watchlistStats.total, target_locations: ['Bengaluru', 'Remote', 'Global'] },
    outputs: { active_lanes: 5, status: 'operational' },
  });

  // Latest jobs
  latestJobs.slice(0, 4).forEach((j, idx) => {
    liveNodes.push({
      id: `ats-job-${idx}`,
      lane: 3,
      forkFromLane: 0,
      text: `Captured ${j.title.slice(0, 32)}...`,
      desc: `Direct ATS role launch detected at ${j.company} (${j.location || 'Remote'})`,
      category: 'ats_radar',
      status: 'done',
      time: j.discovered_at ? new Date(j.discovered_at).toLocaleTimeString() : 'Recent',
      command: `poll_board('${j.site || 'direct'}', company='${j.company}')`,
      agent: 'ats_stream_poller',
      route: j.execution_route || 'PORTAL_ONLY',
      inputs: { company: j.company, source: j.site, portal_url: j.url },
      outputs: { role: j.title, status: 'ingested', route: j.execution_route },
    });
  });

  // Latest leads
  latestLeads.slice(0, 5).forEach((l, idx) => {
    liveNodes.push({
      id: `lead-enrich-${idx}`,
      lane: 2,
      forkFromLane: 0,
      text: `Enriched ${l.contact_name || l.contact_email}`,
      desc: `Synthesized verified ${l.contact_type} contact for ${l.company_name}`,
      category: 'deep_looper',
      status: 'done',
      time: l.created_at ? new Date(l.created_at).toLocaleTimeString() : 'Recent',
      command: `harvest_company_emails_cascade('${l.company_name}', domain='${l.contact_email.split('@')[1] || ''}')`,
      agent: 'web_and_social_looper',
      route: l.execution_route || 'DUAL_ATTACK',
      inputs: { company: l.company_name, source: l.source_platform },
      outputs: { verified_email: l.contact_email, role: l.role_title, type: l.contact_type },
    });
  });

  // Parallel worker
  liveNodes.push({
    id: 'worker-cdp-0',
    lane: 4,
    forkFromLane: 3,
    text: 'Zero-Token Local Matcher & CDP Worker',
    desc: 'Local 4-factor scoring engine with universal job retention and sub-millisecond execution',
    category: 'apply_worker',
    status: 'done',
    time: 'Ready',
    command: 'applypilot match-jobs --re-score-all',
    agent: 'local_deterministic_matcher',
    route: 'DUAL_ATTACK',
    inputs: { candidate_profile: 'Sameer Bagul', status: 'ready' },
    outputs: { scoring_mode: 'zero_token_local', retention: 'universal' },
  });

  // Dual-Attack Outreach node
  liveNodes.push({
    id: 'outreach-hitl-sync',
    lane: 5,
    forkFromLane: 2,
    text: 'Dual-Attack Outreach & HITL Gate',
    desc: 'Strict Admin Safety Gate: emails staged in pending_review requiring explicit approval',
    category: 'outreach',
    status: 'done',
    time: 'Listening',
    command: 'applypilot outreach review',
    agent: 'dual_attack_hitl_agent',
    route: 'DUAL_ATTACK',
    inputs: { outreach_mode: 'draft', pending_reviews: latestLeads.length },
    outputs: { gate_status: 'enforced', safety: 'human_in_the_loop' },
  });

  return {
    nodes: liveNodes,
    stats: {
      totalJobs: latestJobs.length,
      totalLeads: latestLeads.length,
      watchlistCompanies: watchlistStats.total,
      tracesRecorded: traces.length,
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 👤 CANDIDATE PROFILE & Q&A KNOWLEDGE BASE (Phase 2)
// ─────────────────────────────────────────────────────────────────────────────

export function getProfileFilePath(): string {
  const customDir = process.env.APPLYPILOT_DIR;
  if (customDir) return path.join(customDir, 'profile.json');
  return path.join(os.homedir(), '.applypilot', 'profile.json');
}

export function getResumeFilePath(ext = 'pdf'): string {
  const fs = require('node:fs');
  const customDir = process.env.APPLYPILOT_DIR;
  const baseDir = customDir || path.join(os.homedir(), '.applypilot');
  const primaryPath = path.join(baseDir, `resume.${ext}`);
  if (fs.existsSync(primaryPath)) return primaryPath;

  // Fallback to root sameer-bagul-CV.pdf if checking pdf
  if (ext === 'pdf') {
    const rootCv = path.join(process.cwd(), 'sameer-bagul-CV.pdf');
    if (fs.existsSync(rootCv)) return rootCv;
    const parentRootCv = path.join(process.cwd(), '..', 'sameer-bagul-CV.pdf');
    if (fs.existsSync(parentRootCv)) return parentRootCv;
  }

  return primaryPath;
}

export function getCandidateProfile(): { profile: any; hasResume: boolean; resumePath: string | null } {
  const fs = require('node:fs');
  const profilePath = getProfileFilePath();
  const resumePdf = getResumeFilePath('pdf');
  const resumeTxt = getResumeFilePath('txt');
  const resumeDocx = getResumeFilePath('docx');

  let hasResume = false;
  let resumePath: string | null = null;
  if (fs.existsSync(resumePdf)) {
    hasResume = true;
    resumePath = resumePdf;
  } else if (fs.existsSync(resumeDocx)) {
    hasResume = true;
    resumePath = resumeDocx;
  } else if (fs.existsSync(resumeTxt)) {
    hasResume = true;
    resumePath = resumeTxt;
  }

  let resumeText = '';
  if (fs.existsSync(resumeTxt)) {
    try {
      resumeText = fs.readFileSync(resumeTxt, 'utf-8');
    } catch {}
  }

  let profileData: any = null;
  if (fs.existsSync(profilePath)) {
    try {
      profileData = JSON.parse(fs.readFileSync(profilePath, 'utf-8'));
    } catch {}
  }

  if (!profileData) {
    // Default template
    profileData = {
      name: 'Sameer Bagul',
      first_name: 'Sameer',
      last_name: 'Bagul',
      email: 'sameerbagul2004@gmail.com',
      phone: '+91 98765 43210',
      current_title: 'Full-Stack & Autonomous AI Systems Engineer',
      current_company: 'Independent / Open Source',
      years_of_experience: 3,
      notice_period: 'Immediate',
      location: {
        city: 'Bengaluru',
        state: 'Karnataka',
        country: 'India',
        postal_code: '560001',
      },
      urls: {
        linkedin: 'https://www.linkedin.com/in/sameer-bagul',
        github: 'https://github.com/Sameer-Bagul',
        portfolio: 'https://sameerbagul.dev',
      },
      work_authorization: {
        citizenship: 'India',
        authorized_in_target: 'Yes',
        requires_sponsorship: 'No',
        security_clearance: 'None',
      },
      compensation: {
        current_ctc: '₹7,00,000 (7 LPA)',
        joining_bonus: '₹1,00,000 (1 Lakh)',
        target_salary: '₹7,00,000 - ₹10,00,000',
        min_salary: '₹5,00,000 - ₹6,00,000',
        target_salary_usd: '$70,000 - $110,000',
        currency: 'INR',
        negotiable: true,
      },
      preferences: {
        remote_preference: 'Remote / Hybrid',
        willing_to_relocate: 'Yes',
        default_apply_mode: 'headless',
        auto_submit: false,
      },
      eeo: {
        gender: 'Male',
        veteran_status: 'I am not a protected veteran',
        disability_status: 'No, I do not have a disability',
      },
      summary:
        'Software Engineer specializing in autonomous multi-agent systems, Next.js, TypeScript, Python, and high-throughput scraping/CDP automation engines.',
      skills: [
        'Python',
        'TypeScript',
        'React',
        'Next.js',
        'FastAPI',
        'Playwright',
        'Docker',
        'SQLite',
        'PostgreSQL',
        'Tailwind CSS',
        'AI Agents',
      ],
      resume_text: resumeText,
    };
  }

  return {
    profile: profileData,
    hasResume,
    resumePath,
  };
}

export function saveCandidateProfile(data: any): { success: boolean; error?: string } {
  const fs = require('node:fs');
  const profilePath = getProfileFilePath();
  const dir = path.dirname(profilePath);

  try {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(profilePath, JSON.stringify(data, null, 2), 'utf-8');

    // Also mirror to project config/candidate_vault.json
    try {
      const mirrorPaths = [
        path.join(process.cwd(), 'config', 'candidate_vault.json'),
        path.join(process.cwd(), '..', 'config', 'candidate_vault.json'),
      ];
      for (const mp of mirrorPaths) {
        const mdir = path.dirname(mp);
        if (fs.existsSync(mdir)) {
          fs.writeFileSync(mp, JSON.stringify(data, null, 2), 'utf-8');
          break;
        }
      }
    } catch {}

    // If resume_text is supplied, write it to resume.txt as well
    if (data.resume_text) {
      const txtPath = getResumeFilePath('txt');
      fs.writeFileSync(txtPath, data.resume_text, 'utf-8');
    }

    return { success: true };
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export function getQaKnowledgeList(limit = 100): any[] {
  const db = getDb();
  try {
    const rows = db.prepare(
      `SELECT id, question_text, question_key, canonical_question, answer_text, answer_source, field_type, options_json, use_count, updated_at
       FROM qa_knowledge
       ORDER BY use_count DESC, id DESC
       LIMIT ?`
    ).all(limit);
    return rows;
  } catch (err) {
    return [];
  }
}

export function saveQaKnowledgeItem(item: {
  question_text: string;
  answer_text: string;
  question_key?: string;
  field_type?: string;
}): { success: boolean; id?: number; error?: string } {
  const db = getDb();
  const crypto = require('node:crypto');

  const questionKey =
    item.question_key ||
    item.question_text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .slice(0, 50);

  const qHash = crypto.createHash('sha256').update(item.question_text.trim().toLowerCase()).digest('hex');
  const now = new Date().toISOString();

  try {
    const stmt = db.prepare(`
      INSERT INTO qa_knowledge (question_text, question_key, canonical_question, question_hash, answer_text, answer_source, field_type, updated_at, created_at, use_count)
      VALUES (?, ?, ?, ?, ?, 'user_input', ?, ?, ?, 1)
      ON CONFLICT(question_key, answer_text) DO UPDATE SET
        question_text = excluded.question_text,
        updated_at = excluded.updated_at,
        use_count = qa_knowledge.use_count + 1
    `);
    const res = stmt.run(
      item.question_text,
      questionKey,
      item.question_text,
      qHash,
      item.answer_text,
      item.field_type || 'text',
      now,
      now
    );
    return { success: true, id: Number(res.lastInsertRowid) };
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export function deleteQaKnowledgeItem(id: number): { success: boolean; error?: string } {
  const db = getDb();
  try {
    db.prepare('DELETE FROM qa_knowledge WHERE id = ?').run(id);
    return { success: true };
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export interface SourceStatItem {
  id: string;
  name: string;
  badge: string;
  type: 'Enterprise ATS' | 'Social Network' | 'Search Engine / OSINT' | 'Community' | 'Global Board';
  total_jobs: number;
  avg_score: number | null;
  last_seen: string | null;
  top_companies: string[];
  status: 'ACTIVE' | 'CONNECTED';
  description: string;
}

export function getSourcesStats(): {
  sources: SourceStatItem[];
  totalJobs: number;
  totalPlatforms: number;
} {
  const db = getDb();

  const groups = [
    {
      id: 'linkedin',
      name: 'LinkedIn Jobs',
      badge: 'SOCIAL',
      type: 'Social Network' as const,
      pattern: "%linkedin%",
      description: 'Discovered via LinkedIn Guest APIs and recruiter direct feeds.',
    },
    {
      id: 'workday',
      name: 'Workday Enterprise',
      badge: 'ENTERPRISE',
      type: 'Enterprise ATS' as const,
      pattern: "%workday%",
      description: 'Fortune 500 banks, GCCs, and multinational corporate career portals (*.myworkdayjobs.com).',
    },
    {
      id: 'internet_search',
      name: 'Internet & Search Engine Crawler',
      badge: 'OSINT',
      type: 'Search Engine / OSINT' as const,
      pattern: "(site LIKE '%google%' OR site LIKE '%company_careers%' OR site LIKE '%search%' OR site LIKE '%topstartups%')",
      isCustomSql: true,
      description: 'URLs and career listings crawled directly from web search engines, Google, and sitemaps.',
    },
    {
      id: 'greenhouse',
      name: 'Greenhouse Board',
      badge: 'ATS',
      type: 'Enterprise ATS' as const,
      pattern: "%greenhouse%",
      description: 'Direct ATS boards from top-tier tech scaleups and unicorns.',
    },
    {
      id: 'ashby',
      name: 'Ashby HQ',
      badge: 'ATS',
      type: 'Enterprise ATS' as const,
      pattern: "%ashby%",
      description: 'AI startups and modern tech companies (OpenAI, Anthropic, Ramp).',
    },
    {
      id: 'lever',
      name: 'Lever ATS',
      badge: 'ATS',
      type: 'Enterprise ATS' as const,
      pattern: "%lever%",
      description: 'High-growth mid-market engineering companies.',
    },
    {
      id: 'hackernews',
      name: 'Hacker News (Who is Hiring)',
      badge: 'COMMUNITY',
      type: 'Community' as const,
      pattern: "(site LIKE '%hackernews%' OR site LIKE '%ycombinator%')",
      isCustomSql: true,
      description: 'Monthly direct founder and engineering hiring threads on Y Combinator.',
    },
    {
      id: 'smartrecruiters',
      name: 'SmartRecruiters',
      badge: 'ATS',
      type: 'Enterprise ATS' as const,
      pattern: "%smartrecruiters%",
      description: 'Global enterprise and fintech platforms (Visa, etc.).',
    },
    {
      id: 'naukri',
      name: 'Naukri Gulf & India',
      badge: 'DOMESTIC',
      type: 'Global Board' as const,
      pattern: "%naukri%",
      description: 'Premier domestic tech job postings in Bengaluru, Pune, Hyderabad, and NCR.',
    },
    {
      id: 'bangalorestartupmap',
      name: 'Bangalore Startup Map',
      badge: 'DIRECTORY',
      type: 'Global Board' as const,
      pattern: "%bangalorestartupmap%",
      description: 'Bengaluru ecosystem VC portfolio startups and stealth engineering teams.',
    },
    {
      id: 'oracle',
      name: 'Oracle Taleo / Cloud',
      badge: 'ENTERPRISE',
      type: 'Enterprise ATS' as const,
      pattern: "%oracle%",
      description: 'Oracle Cloud & Taleo corporate recruitment systems.',
    },
    {
      id: 'seek',
      name: 'Seek Global',
      badge: 'GLOBAL',
      type: 'Global Board' as const,
      pattern: "%seek%",
      description: 'APAC and international tech openings.',
    },
    {
      id: 'other_ats',
      name: 'Aggregated Global ATS',
      badge: 'AGGREGATED',
      type: 'Global Board' as const,
      pattern: "site LIKE 'freehire%'",
      isCustomSql: true,
      description: 'Adzuna, Himalayas, Wellfound, Eightfold, Phenom, and European tech portals.',
    },
  ];

  const sources: SourceStatItem[] = [];
  let grandTotal = 0;

  for (const g of groups) {
    let whereClause = '';
    const params: any[] = [];
    if (g.isCustomSql) {
      whereClause = `WHERE ${g.pattern}`;
    } else {
      whereClause = `WHERE site LIKE ?`;
      params.push(g.pattern);
    }

    const row = db.prepare(`
      SELECT 
        COUNT(*) as total_jobs,
        ROUND(AVG(CASE WHEN fit_score IS NOT NULL THEN fit_score END), 1) as avg_score,
        MAX(discovered_at) as last_seen
      FROM jobs
      ${whereClause}
    `).get(...params) as any;

    const total = row?.total_jobs || 0;
    if (total === 0) continue;

    grandTotal += total;

    // Get top 3 companies for this source
    const topComps = db.prepare(`
      SELECT company, COUNT(*) as c
      FROM jobs
      ${whereClause} AND company IS NOT NULL AND company != ''
      GROUP BY company
      ORDER BY c DESC
      LIMIT 3
    `).all(...params) as Array<{ company: string; c: number }>;

    sources.push({
      id: g.id,
      name: g.name,
      badge: g.badge,
      type: g.type,
      total_jobs: total,
      avg_score: row?.avg_score || null,
      last_seen: row?.last_seen || null,
      top_companies: topComps.map(tc => tc.company),
      status: 'ACTIVE',
      description: g.description,
    });
  }

  // Sort by total jobs descending
  sources.sort((a, b) => b.total_jobs - a.total_jobs);

  return {
    sources,
    totalJobs: grandTotal,
    totalPlatforms: sources.length,
  };
}


