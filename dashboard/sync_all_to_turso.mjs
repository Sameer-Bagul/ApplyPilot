import { createClient } from '@libsql/client';
import { DatabaseSync } from 'node:sqlite';
import path from 'node:path';
import os from 'node:os';

const TURSO_URL = process.env.TURSO_DATABASE_URL || 'libsql://applypilot-sameerbagul.aws-ap-south-1.turso.io';
const TURSO_TOKEN = process.env.TURSO_AUTH_TOKEN || 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTM4MDkzMDUsImlkIjoiMDFhMWE3NWQtN2EwMS03NTk5LTg5OGYtOTg4MWY1N2FlMjRhIiwia2lkIjoiZmtnelNtNjktVnVWdGFTR2NRMDdoOE1BY3hFdHdlejY1bUFYLUVQN2QxQSIsInJpZCI6ImFmMmNkNWQwLTZkNjktNDc1OS05MDBkLWI4NDE5MDdjOGNhNyJ9.yDxxHO64H7nit7LdfJRLYMgGwgSs-lMoGMyD-eYkqzW0CbGHut-svUfaW3VMjtMFDF-DS3BtVN4FXx8o30UjAA';

const localDbPath = process.env.LOCAL_DB_PATH || path.join(os.homedir(), '.applypilot', 'applypilot.db');
console.log('Connecting to local SQLite:', localDbPath);
const localDb = new DatabaseSync(localDbPath);

console.log('Connecting to Turso Cloud:', TURSO_URL);
const turso = createClient({
  url: TURSO_URL,
  authToken: TURSO_TOKEN,
});

async function ensureTableExists(tableName) {
  const localTable = localDb.prepare(
    `SELECT sql FROM sqlite_master WHERE type='table' AND name = ?`
  ).get(tableName);
  if (!localTable || !localTable.sql) return;
  try {
    const createSql = localTable.sql.replace(/^CREATE TABLE\s+/i, 'CREATE TABLE IF NOT EXISTS ');
    await turso.execute(createSql);
  } catch (e) {
    if (!e.message?.includes('already exists')) {
      console.warn(`Table ensure notice for ${tableName}:`, e.message);
    }
  }
}

async function syncTableColumns(tableName) {
  await ensureTableExists(tableName);
  const localCols = localDb.prepare(`PRAGMA table_info("${tableName}")`).all();
  const remoteColsRes = await turso.execute(`PRAGMA table_info("${tableName}")`);
  const remoteColNames = new Set(remoteColsRes.rows.map(r => r.name));

  for (const col of localCols) {
    if (!remoteColNames.has(col.name)) {
      console.log(`Adding missing column "${col.name}" (${col.type}) to Turso table "${tableName}"...`);
      try {
        await turso.execute(`ALTER TABLE "${tableName}" ADD COLUMN "${col.name}" ${col.type || 'TEXT'}`);
      } catch (e) {
        console.warn(`Could not add column ${col.name}:`, e.message);
      }
    }
  }
}

async function reconcileRemotePrimaryKeys(tableName, pkCol, localRows) {
  const localPkSet = new Set(localRows.map(r => r[pkCol]).filter(v => v !== null && v !== undefined));
  const remoteRes = await turso.execute(`SELECT "${pkCol}" AS pk FROM "${tableName}"`);
  const stalePks = remoteRes.rows
    .map(r => r.pk)
    .filter(pk => pk === null || pk === undefined || !localPkSet.has(pk));

  if (stalePks.length === 0) {
    console.log(`  [${tableName}] PK reconciliation: 0 stale remote rows.`);
    return 0;
  }

  console.log(`  [${tableName}] PK reconciliation: deleting ${stalePks.length} stale/duplicate remote rows...`);
  const nonNullStale = stalePks.filter(pk => pk !== null && pk !== undefined);
  const BATCH_SIZE = 100;
  for (let i = 0; i < nonNullStale.length; i += BATCH_SIZE) {
    const batch = nonNullStale.slice(i, i + BATCH_SIZE);
    const statements = batch.map(pk => ({
      sql: `DELETE FROM "${tableName}" WHERE "${pkCol}" = ?`,
      args: [pk],
    }));
    await turso.batch(statements, 'write');
  }
  if (stalePks.length > nonNullStale.length) {
    await turso.execute(`DELETE FROM "${tableName}" WHERE "${pkCol}" IS NULL`);
  }
  return stalePks.length;
}

async function main() {
  await turso.execute('PRAGMA foreign_keys = OFF;');

  const tables = [
    'jobs',
    'career_watchlist',
    'recruiter_leads',
    'discovery_sources',
    'qa_knowledge',
    'company_intel',
    'ats_selector_cache',
    'ats_session_vault',
    'hitl_tickets'
  ];

  const reconciledPks = {
    jobs: 'url',
    career_watchlist: 'company_id',
    recruiter_leads: 'lead_id',
    discovery_sources: 'url',
  };

  for (const tableName of tables) {
    console.log(`\n=== Processing table: ${tableName} ===`);
    await syncTableColumns(tableName);

    const rows = localDb.prepare(`SELECT * FROM "${tableName}"`).all();
    console.log(`Local rows to sync: ${rows.length}`);

    if (reconciledPks[tableName]) {
      await reconcileRemotePrimaryKeys(tableName, reconciledPks[tableName], rows);
    }

    if (rows.length === 0) continue;

    const BATCH_SIZE = 100;
    for (let i = 0; i < rows.length; i += BATCH_SIZE) {
      const batch = rows.slice(i, i + BATCH_SIZE);
      const statements = batch.map(row => {
        const cols = Object.keys(row);
        const placeholders = cols.map(() => '?').join(', ');
        const colNames = cols.map(c => `"${c}"`).join(', ');
        const args = Object.values(row).map(val => val === null ? null : val);
        return {
          sql: `INSERT OR REPLACE INTO "${tableName}" (${colNames}) VALUES (${placeholders})`,
          args,
        };
      });

      await turso.batch(statements, 'write');
      process.stdout.write(`  [${tableName}] Migrated ${Math.min(i + BATCH_SIZE, rows.length)}/${rows.length} rows...\r`);
    }
    console.log(`\n✓ Successfully synced ${rows.length} rows for ${tableName}.`);
  }

  // Ensure partial unique indexes exist on Turso as well
  try {
    await turso.execute(`
      CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_unique_domain
        ON career_watchlist(LOWER(official_domain))
        WHERE official_domain IS NOT NULL AND official_domain != ''
    `);
    await turso.execute(`
      CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_unique_email
        ON recruiter_leads(LOWER(contact_email))
        WHERE contact_email IS NOT NULL AND contact_email != ''
    `);
  } catch (e) {
    console.warn('Partial unique index notice on Turso:', e.message);
  }

  console.log('\n=============================================');
  console.log('FINAL REMOTE TURSO VERIFICATION:');
  const jobCount = await turso.execute('SELECT COUNT(*) as cnt FROM jobs');
  const compCount = await turso.execute('SELECT COUNT(*) as cnt FROM career_watchlist');
  const leadCount = await turso.execute('SELECT COUNT(*) as cnt FROM recruiter_leads');
  const srcCount = await turso.execute('SELECT COUNT(*) as cnt FROM discovery_sources');

  console.log(`✓ Remote Turso Jobs: ${jobCount.rows[0].cnt}`);
  console.log(`✓ Remote Turso Watchlist Companies: ${compCount.rows[0].cnt}`);
  console.log(`✓ Remote Turso Recruiter Leads: ${leadCount.rows[0].cnt}`);
  console.log(`✓ Remote Turso Discovery Sources: ${srcCount.rows[0].cnt}`);
  console.log('=============================================');
}

main().catch(err => {
  console.error('Migration failed:', err);
  process.exit(1);
});
