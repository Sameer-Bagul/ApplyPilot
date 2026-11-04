import { createClient } from '@libsql/client';
import { DatabaseSync } from 'node:sqlite';
import path from 'node:path';
import os from 'node:os';

const TURSO_URL = process.env.TURSO_DATABASE_URL || 'libsql://applypilot-sameerbagul.aws-ap-south-1.turso.io';
const TURSO_TOKEN = process.env.TURSO_AUTH_TOKEN || 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTM4MDkzMDUsImlkIjoiMDFhMWE3NWQtN2EwMS03NTk5LTg5OGYtOTg4MWY1N2FlMjRhIiwia2lkIjoiZmtnelNtNjktVnVWdGFTR2NRMDdoOE1BY3hFdHdlejY1bUFYLUVQN2QxQSIsInJpZCI6ImFmMmNkNWQwLTZkNjktNDc1OS05MDBkLWI4NDE5MDdjOGNhNyJ9.yDxxHO64H7nit7LdfJRLYMgGwgSs-lMoGMyD-eYkqzW0CbGHut-svUfaW3VMjtMFDF-DS3BtVN4FXx8o30UjAA';

const localDbPath = '/home/sameer/Projects/ApplyPilot/applypilot.db';
console.log('Connecting to local SQLite:', localDbPath);
const localDb = new DatabaseSync(localDbPath);

console.log('Connecting to Turso Cloud:', TURSO_URL);
const turso = createClient({
  url: TURSO_URL,
  authToken: TURSO_TOKEN,
});

async function main() {
  await turso.execute('PRAGMA foreign_keys = OFF;');

  // 1. Order tables so parent tables come first
  const tables = localDb.prepare(`
    SELECT name, sql FROM sqlite_master 
    WHERE type='table' 
      AND name NOT LIKE 'sqlite_%' 
      AND name NOT LIKE '_litestream_%'
      AND name NOT LIKE 'qa_fts%'
    ORDER BY CASE 
      WHEN name = 'jobs' THEN 1
      WHEN name = 'career_watchlist' THEN 2
      WHEN name = 'recruiter_leads' THEN 3
      WHEN name = 'qa_knowledge' THEN 4
      ELSE 5
    END, name
  `).all();

  console.log(`Found ${tables.length} tables in local database.`);

  for (const t of tables) {
    console.log(`\n--- Creating table ${t.name} on Turso ---`);
    try {
      await turso.execute(t.sql);
    } catch (err) {
      if (!err.message?.includes('already exists')) {
        console.warn(`Table create warning for ${t.name}:`, err.message);
      }
    }

    // Get rows from local DB
    try {
      const rows = localDb.prepare(`SELECT * FROM "${t.name}"`).all();
      console.log(`Migrating ${rows.length} rows for table ${t.name}...`);
      if (rows.length === 0) continue;

      // Batch insert
      const BATCH_SIZE = 50;
      for (let i = 0; i < rows.length; i += BATCH_SIZE) {
        const batch = rows.slice(i, i + BATCH_SIZE);
        const statements = batch.map(row => {
          const cols = Object.keys(row);
          const placeholders = cols.map(() => '?').join(', ');
          const colNames = cols.map(c => `"${c}"`).join(', ');
          const args = Object.values(row).map(val => val === null ? null : val);
          return {
            sql: `INSERT OR REPLACE INTO "${t.name}" (${colNames}) VALUES (${placeholders})`,
            args,
          };
        });

        await turso.batch(statements, 'write');
        process.stdout.write(`  Migrated ${Math.min(i + BATCH_SIZE, rows.length)}/${rows.length} rows...\r`);
      }
      console.log(`\n  Done migrating ${rows.length} rows for ${t.name}.`);
    } catch (err) {
      console.warn(`Row migration notice for ${t.name}:`, err.message);
    }
  }

  // Verify counts
  console.log('\n=============================================');
  console.log('VERIFYING REMOTE TURSO DATA:');
  const jobCount = await turso.execute('SELECT COUNT(*) as cnt FROM jobs');
  const compCount = await turso.execute('SELECT COUNT(*) as cnt FROM career_watchlist');
  const leadCount = await turso.execute('SELECT COUNT(*) as cnt FROM recruiter_leads');

  console.log(`Remote Turso Jobs: ${jobCount.rows[0].cnt}`);
  console.log(`Remote Turso Watchlist Companies: ${compCount.rows[0].cnt}`);
  console.log(`Remote Turso Recruiter Leads: ${leadCount.rows[0].cnt}`);
  console.log('=============================================');
}

main().catch(err => {
  console.error('Migration failed:', err);
  process.exit(1);
});
