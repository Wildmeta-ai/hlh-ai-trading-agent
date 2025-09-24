#!/usr/bin/env node

const { Pool } = require('pg');

const pool = new Pool({
  host: '15.235.212.36',
  port: 5432,
  database: 'hummingbot_api',
  user: 'hbot',
  password: 'hummingbot-api',
});

async function clearFakeActivities() {
  const client = await pool.connect();

  try {
    // Clear activities with fake order IDs or wrong hive_id
    const result = await client.query(`
      DELETE FROM hive_activities
      WHERE order_id LIKE '393712894%'
         OR order_id LIKE '705669%'
         OR order_id LIKE '712894%'
         OR hive_id = 'hive-solana-rpc-node-sg-2-8080'
    `);

    console.log(`Deleted ${result.rowCount} fake activity records`);

    // Show remaining activities
    const remaining = await client.query('SELECT COUNT(*) as count FROM hive_activities');
    console.log(`Remaining activities: ${remaining.rows[0].count}`);

  } finally {
    client.release();
    await pool.end();
  }
}

clearFakeActivities().catch(console.error);