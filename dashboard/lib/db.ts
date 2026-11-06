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

export function getDb(): DatabaseSync {
  if (_db) return _db;

  const dbPath = process.env.APPLYPILOT_DB_PATH || path.join(os.homedir(), '.applypilot', 'applypilot.db');
  
  try {
    // Open in read-write mode to support interactive CRUD operations
    _db = new DatabaseSync(dbPath);
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
  const appliedCount = (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE state = 'applied' OR apply_status = 'applied' OR proof_video_path IS NOT NULL").get() as any)?.c || 0;

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
           proof_video_path, proof_screenshot_path, proof_log_path, apply_status
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

  query += ` ORDER BY discovered_at DESC NULLS LAST LIMIT ? OFFSET ?`;
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
    WHERE (state = 'applied' OR apply_status = 'applied' OR proof_video_path IS NOT NULL OR proof_screenshot_path IS NOT NULL)
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

export function getCompanies(params: {
  search?: string;
  sector?: string;
  stage?: string;
  vipOnly?: boolean;
  page?: number;
  limit?: number;
}) {
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
  const limit = Math.min(100, Math.max(1, params.limit || 20));
  const offset = (page - 1) * limit;

  let query = `
    SELECT cw.company_id, cw.company_name, cw.official_domain, cw.careers_page_url, 
           cw.ats_provider, cw.priority_tier, cw.is_vip, cw.stage, cw.sector, cw.area, 
           cw.location, cw.team_size, cw.total_funding, cw.founders_json, 
           cw.hr_contacts_json,
           COALESCE((SELECT COUNT(*) FROM jobs j WHERE j.company = cw.company_name), cw.open_roles_count, 0) as open_roles_count,
           COALESCE((SELECT COUNT(*) FROM recruiter_leads rl WHERE rl.company_name = cw.company_name), 0) as leads_count,
           cw.last_checked_at
    FROM career_watchlist cw
    WHERE 1=1
  `;
  const queryParams: any[] = [];

  if (params.search) {
    query += ` AND (cw.company_name LIKE ? OR cw.official_domain LIKE ? OR cw.area LIKE ? OR cw.sector LIKE ?)`;
    const s = `%${params.search}%`;
    queryParams.push(s, s, s, s);
  }

  if (params.vipOnly) {
    query += ` AND cw.is_vip = 1`;
  }

  if (params.sector && params.sector !== 'ALL') {
    query += ` AND cw.sector LIKE ?`;
    queryParams.push(`%${params.sector}%`);
  }

  if (params.stage && params.stage !== 'ALL') {
    query += ` AND cw.stage LIKE ?`;
    queryParams.push(`%${params.stage}%`);
  }

  const countQuery = `SELECT COUNT(*) as c FROM (${query})`;
  const total = (db.prepare(countQuery).get(...queryParams) as any)?.c || 0;

  query += ` ORDER BY open_roles_count DESC, cw.is_vip DESC, leads_count DESC, cw.company_name ASC LIMIT ? OFFSET ?`;
  queryParams.push(limit, offset);

  const rawCompanies = db.prepare(query).all(...queryParams);

  const companies = rawCompanies.map((c: any) => {
    let founders = [];
    let emails = [];
    try {
      if (c.founders_json) founders = JSON.parse(c.founders_json);
    } catch {}
    try {
      if (c.hr_contacts_json) emails = JSON.parse(c.hr_contacts_json);
    } catch {}

    return {
      ...c,
      founders,
      emails,
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

  // Fetch all leads for this company
  const leads = db
    .prepare(
      `SELECT lead_id, job_id, company_name, company_domain, role_title,
              contact_name, contact_email, personal_email, personal_email_source, preferred_channel,
              contact_type, contact_linkedin_url,
              linkedin_connection_note, source_platform, evidence_snippet,
              execution_route, outreach_status, created_at,
              email_draft_subject, email_draft_body, approved_at, approved_by
       FROM recruiter_leads
       WHERE company_name = ?
       ORDER BY contact_type ASC, created_at DESC`
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
      founders,
      emails,
      topProjects,
      techRadar,
    },
    leads,
    jobs,
    stats: {
      totalLeads: leads.length,
      totalJobs: jobs.length,
      verifiedEmails: leads.map((l: any) => l.contact_email).filter(Boolean),
      hasDualAttack: leads.length > 0 && (jobs.length > 0 || Boolean(company.careers_page_url)),
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
           email_draft_subject, email_draft_body, approved_at, approved_by
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

  query += ` ORDER BY created_at DESC LIMIT ? OFFSET ?`;
  queryParams.push(limit, offset);

  const leads = db.prepare(query).all(...queryParams);

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
    SELECT * FROM recruiter_leads WHERE lead_id = ? OR lead_id LIKE (? || '%')
  `).get(lead_id, lead_id);

  if (!lead) return null;

  // Linked company info
  let companyInfo: any = null;
  if (lead.company_name) {
    try {
      companyInfo = db.prepare('SELECT * FROM career_watchlist WHERE company_name = ?').get(lead.company_name);
    } catch {}
  }

  // Linked open jobs
  let openJobs: any[] = [];
  if (lead.company_name) {
    try {
      openJobs = db.prepare('SELECT url, title, location, fit_score FROM jobs WHERE company = ? LIMIT 10').all(lead.company_name);
    } catch {}
  }

  return {
    lead,
    companyInfo,
    openJobs,
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
}) {
  const db = getDb();
  const lead_id = `lead_${Math.random().toString(36).substring(2, 12)}`;
  const now = new Date().toISOString();

  db.prepare(`
    INSERT OR REPLACE INTO recruiter_leads (
      lead_id, company_name, contact_email, contact_name, role_title,
      contact_type, contact_linkedin_url, company_domain, execution_route,
      outreach_status, email_draft_subject, email_draft_body, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review', ?, ?, ?)
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
    data.email_draft_subject || `Application & Introduction: ${data.role_title || 'Software Engineer'}`,
    data.email_draft_body || `Hi ${data.contact_name || 'Hiring Team'},\n\nI noticed the open role at ${data.company_name} and wanted to reach out directly with my background in high-performance distributed systems and AI agents.`,
    now
  );

  return getLeadDetail(lead_id);
}

export function updateLead(lead_id: string, updates: Partial<{
  contact_name: string;
  contact_email: string;
  role_title: string;
  contact_type: string;
  contact_linkedin_url: string;
  outreach_status: string;
  email_draft_subject: string;
  email_draft_body: string;
  approved_at: string;
  approved_by: string;
}>) {
  const db = getDb();
  const fields: string[] = [];
  const params: any[] = [];

  for (const [key, value] of Object.entries(updates)) {
    fields.push(`${key} = ?`);
    params.push(value);
  }

  if (fields.length === 0) return getLeadDetail(lead_id);

  params.push(lead_id, lead_id);
  db.prepare(`UPDATE recruiter_leads SET ${fields.join(', ')} WHERE lead_id = ? OR lead_id LIKE (? || '%')`).run(...params);

  return getLeadDetail(lead_id);
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


