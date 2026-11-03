import { DatabaseSync } from 'node:sqlite';
import os from 'node:os';
import path from 'node:path';

let _db: DatabaseSync | null = null;

export function getDb(): DatabaseSync {
  if (_db) return _db;

  const dbPath = process.env.APPLYPILOT_DB_PATH || path.join(os.homedir(), '.applypilot', 'applypilot.db');
  
  try {
    _db = new DatabaseSync(dbPath, { readOnly: true });
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
}

export function getDashboardStats(): StatsData {
  const db = getDb();

  const totalJobs = (db.prepare('SELECT COUNT(*) as c FROM jobs').get() as any)?.c || 0;
  const totalCompanies = (db.prepare('SELECT COUNT(*) as c FROM career_watchlist').get() as any)?.c || 0;
  const totalLeads = (db.prepare('SELECT COUNT(*) as c FROM recruiter_leads').get() as any)?.c || 0;
  const vipCompanies = (db.prepare('SELECT COUNT(*) as c FROM career_watchlist WHERE is_vip = 1').get() as any)?.c || 0;

  const dualAttack = (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE execution_route = 'DUAL_ATTACK'").get() as any)?.c || 0;
  const portalOnly = (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE execution_route = 'PORTAL_ONLY'").get() as any)?.c || 0;
  const emailOnly = (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE execution_route = 'EMAIL_ONLY'").get() as any)?.c || 0;

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
           contact_linkedin_url, linkedin_connection_note, outreach_status, created_at
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
  };
}

export function getJobs(params: {
  search?: string;
  route?: string;
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
    SELECT url, title, company, location, site, execution_route, fit_score, 
           discovered_at, state, description
    FROM jobs 
    WHERE 1=1
  `;
  const queryParams: any[] = [];

  if (params.search) {
    query += ` AND (title LIKE ? OR company LIKE ? OR description LIKE ?)`;
    const s = `%${params.search}%`;
    queryParams.push(s, s, s);
  }

  if (params.route && params.route !== 'ALL') {
    query += ` AND execution_route = ?`;
    queryParams.push(params.route);
  }

  if (params.location) {
    query += ` AND location LIKE ?`;
    queryParams.push(`%${params.location}%`);
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

export function getCompanies(params: {
  search?: string;
  sector?: string;
  stage?: string;
  vipOnly?: boolean;
  page?: number;
  limit?: number;
}) {
  const db = getDb();
  const page = Math.max(1, params.page || 1);
  const limit = Math.min(100, Math.max(1, params.limit || 20));
  const offset = (page - 1) * limit;

  let query = `
    SELECT company_id, company_name, official_domain, careers_page_url, 
           ats_provider, priority_tier, is_vip, stage, sector, area, 
           location, team_size, total_funding, founders_json, 
           hr_contacts_json, open_roles_count, last_checked_at
    FROM career_watchlist 
    WHERE 1=1
  `;
  const queryParams: any[] = [];

  if (params.search) {
    query += ` AND (company_name LIKE ? OR official_domain LIKE ? OR area LIKE ?)`;
    const s = `%${params.search}%`;
    queryParams.push(s, s, s);
  }

  if (params.vipOnly) {
    query += ` AND is_vip = 1`;
  }

  if (params.sector && params.sector !== 'ALL') {
    query += ` AND sector LIKE ?`;
    queryParams.push(`%${params.sector}%`);
  }

  if (params.stage && params.stage !== 'ALL') {
    query += ` AND stage LIKE ?`;
    queryParams.push(`%${params.stage}%`);
  }

  const countQuery = `SELECT COUNT(*) as c FROM (${query})`;
  const total = (db.prepare(countQuery).get(...queryParams) as any)?.c || 0;

  query += ` ORDER BY is_vip DESC, open_roles_count DESC, company_name ASC LIMIT ? OFFSET ?`;
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
           contact_name, contact_email, contact_type, contact_linkedin_url, 
           linkedin_connection_note, source_platform, evidence_snippet, 
           execution_route, outreach_status, created_at
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
    query += ` AND outreach_status = ?`;
    queryParams.push(params.status);
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
  try {
    if (company.founders_json) founders = JSON.parse(company.founders_json);
  } catch {}
  try {
    if (company.hr_contacts_json) emails = JSON.parse(company.hr_contacts_json);
  } catch {}

  // Fetch all leads for this company
  const leads = db
    .prepare(
      `SELECT lead_id, job_id, company_name, company_domain, role_title,
              contact_name, contact_email, contact_type, contact_linkedin_url,
              linkedin_connection_note, source_platform, evidence_snippet,
              execution_route, outreach_status, created_at
       FROM recruiter_leads
       WHERE company_name = ?
       ORDER BY contact_type ASC, created_at DESC`
    )
    .all(company.company_name);

  // Fetch all open jobs for this company
  const jobs = db
    .prepare(
      `SELECT url, title, company, location, site, execution_route,
              fit_score, discovered_at, state
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
