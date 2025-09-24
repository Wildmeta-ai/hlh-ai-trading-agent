import { NextResponse } from 'next/server';
import { testDatabaseConnection } from '@/lib/database';

export async function GET() {
  try {
    const connectionStatus = await testDatabaseConnection();

    return NextResponse.json({
      ...connectionStatus,
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development'
    });

  } catch (error) {
    console.error('Database status check failed:', error);
    return NextResponse.json({
      connected: false,
      source: 'Error',
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development'
    }, { status: 500 });
  }
}
