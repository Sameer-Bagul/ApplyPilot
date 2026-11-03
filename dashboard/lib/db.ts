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

  query += ` ORDER BY cw.is_vip DESC, open_roles_count DESC, leads_count DESC, cw.company_name ASC LIMIT ? OFFSET ?`;
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

  // Anchor root node (Master Brain)
  liveNodes.push({
    id: 'root-orchestrator',
    lane: 0,
    text: 'Autonomous Pipeline Engine',
    desc: 'Master brain coordinating Omni-Harvester, Deep Looper, 11-ATS Radar, and Dual-Attack Apply',
    category: 'system',
    status: 'done',
    time: 'Running',
    command: 'applypilot run-daily --autonomous',
    agent: 'applypilot-brain',
    route: 'DUAL_ATTACK',
    inputs: { watchlist_monitored: watchlistStats.total, target_locations: ['Bengaluru', 'Remote'] },
    outputs: { active_lanes: 5, status: 'operational' },
  });

  // Add ATS Radar nodes from latest jobs
  latestJobs.slice(0, 4).forEach((j, idx) => {
    liveNodes.push({
      id: `ats-job-${idx}`,
      lane: 3,
      forkFromLane: 0,
      text: `Captured ${j.title.slice(0, 32)}...`,
      desc: `Real-time role launch detected at ${j.company} (${j.location || 'Bengaluru'})`,
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

  // Add Deep Looper email nodes from latest leads
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
      command: `enrich_company_deep('${l.company_name}', domain='${l.contact_email.split('@')[1] || ''}')`,
      agent: 'web_and_social_looper',
      route: l.execution_route || 'DUAL_ATTACK',
      inputs: { company: l.company_name, source: l.source_platform },
      outputs: { verified_email: l.contact_email, role: l.role_title, type: l.contact_type },
    });
  });

  // Add parallel worker nodes from apply_traces if any exist, or active worker templates
  if (traces.length > 0) {
    traces.slice(0, 3).forEach((t, idx) => {
      liveNodes.push({
        id: `trace-apply-${idx}`,
        lane: 4,
        forkFromLane: 3,
        text: `Playwright ${t.action} on ${t.ats_type}`,
        desc: `CDP Worker 0 interacted with selector: ${t.selector || 'field'} (${t.duration_ms || 120}ms)`,
        category: 'apply_worker',
        status: t.status === 'success' ? 'done' : 'running',
        time: t.created_at ? new Date(t.created_at).toLocaleTimeString() : 'Active',
        command: `fill_field('${t.selector}', value=profile['candidate'])`,
        agent: 'playwright_cdp_worker_0',
        route: 'DUAL_ATTACK',
        inputs: { ats: t.ats_type, step: t.step_index, job_url: t.job_url },
        outputs: { result: t.status, duration_ms: t.duration_ms },
      });
    });
  } else {
    liveNodes.push({
      id: 'worker-cdp-0',
      lane: 4,
      forkFromLane: 3,
      text: 'Parallel Apply Worker 0 (Port 9222)',
      desc: 'Isolated Chrome CDP session executing zero-token Tier 0 autofill and Playwright forms',
      category: 'apply_worker',
      status: 'done',
      time: 'Standby / Ready',
      command: 'applypilot apply --workers 2',
      agent: 'playwright_cdp_worker_0',
      route: 'DUAL_ATTACK',
      inputs: { cdp_port: 9222, profile: 'Sameer Bagul', status: 'ready' },
      outputs: { workers_online: 2, cdp_sessions: ['9222', '9223'] },
    });
  }

  // Dual-Attack Outreach node
  liveNodes.push({
    id: 'outreach-hitl-sync',
    lane: 5,
    forkFromLane: 2,
    text: 'Dual-Attack Outreach & HITL Sync',
    desc: 'Simultaneous cold recruiter outreach + asynchronous Gmail 2FA/screening listener',
    category: 'outreach',
    status: 'done',
    time: 'Listening',
    command: 'applypilot track --poll-hitl --interval 60',
    agent: 'dual_attack_hitl_agent',
    route: 'DUAL_ATTACK',
    inputs: { outreach_mode: 'draft', poll_interval_sec: 60 },
    outputs: { verified_leads_ready: latestLeads.length, status: 'synced' },
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
