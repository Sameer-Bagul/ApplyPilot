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

async function syncTableColumns(tableName) {
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

async function main() {
  await turso.execute('PRAGMA foreign_keys = OFF;');

  const tables = [
    'jobs',
    'career_watchlist',
    'recruiter_leads',
    'qa_knowledge',
    'company_intel',
    'ats_selector_cache',
    'ats_session_vault',
    'hitl_tickets'
  ];

  for (const tableName of tables) {
    console.log(`\n=== Processing table: ${tableName} ===`);
    await syncTableColumns(tableName);

    const rows = localDb.prepare(`SELECT * FROM "${tableName}"`).all();
    console.log(`Local rows to sync: ${rows.length}`);
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

  console.log('\n=============================================');
  console.log('FINAL REMOTE TURSO VERIFICATION:');
  const jobCount = await turso.execute('SELECT COUNT(*) as cnt FROM jobs');
  const compCount = await turso.execute('SELECT COUNT(*) as cnt FROM career_watchlist');
  const leadCount = await turso.execute('SELECT COUNT(*) as cnt FROM recruiter_leads');

  console.log(`✓ Remote Turso Jobs: ${jobCount.rows[0].cnt}`);
  console.log(`✓ Remote Turso Watchlist Companies: ${compCount.rows[0].cnt}`);
  console.log(`✓ Remote Turso Recruiter Leads: ${leadCount.rows[0].cnt}`);
  console.log('=============================================');
}

main().catch(err => {
  console.error('Migration failed:', err);
  process.exit(1);
});
