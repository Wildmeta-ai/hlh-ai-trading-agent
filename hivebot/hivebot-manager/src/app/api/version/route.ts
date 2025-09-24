import { NextResponse } from 'next/server';

export async function GET() {
  const version = {
    version: '1.3.0',
    build: '2025-09-01T16:25:00.000Z',
    heartbeat_calculation: 'PostgreSQL SQL (no JavaScript timezone issues)',
    heartbeat_timeout: '2 minutes (120000ms)',
    features: [
      'PostgreSQL database connection',
      'SQL-based heartbeat status calculation',
      'Active strategies calculation fix',
      '2-minute heartbeat timeout',
      'Eliminated JavaScript timezone/timing issues'
    ]
  };

  return NextResponse.json(version);
}
