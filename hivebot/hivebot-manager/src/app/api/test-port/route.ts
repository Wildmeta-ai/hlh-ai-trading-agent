import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';

// Check if a port is actually in use by checking running processes
async function isPortInUse(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const netstatProcess = spawn('netstat', ['-tln'], {});

    let output = '';
    netstatProcess.stdout?.on('data', (data) => {
      output += data.toString();
    });

    netstatProcess.on('close', (code) => {
      if (code !== 0) {
        // If netstat fails, assume port is in use for safety
        resolve(true);
        return;
      }

      // Check if port is listening - be more flexible with the pattern
      const portPattern = new RegExp(`:${port}\\s`);
      const isListening = portPattern.test(output);
      resolve(isListening);
    });

    netstatProcess.on('error', () => {
      // If error, assume port is in use for safety
      resolve(true);
    });
  });
}

// GET /api/test-port?port=8100 - Test port usage detection
export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const portParam = url.searchParams.get('port');

    if (!portParam) {
      return NextResponse.json({
        error: 'Port parameter is required'
      }, { status: 400 });
    }

    const port = parseInt(portParam);
    if (isNaN(port) || port < 1 || port > 65535) {
      return NextResponse.json({
        error: 'Invalid port number'
      }, { status: 400 });
    }

    // Get raw netstat output
    const netstatOutput = await new Promise<string>((resolve) => {
      const netstatProcess = spawn('netstat', ['-tln'], {});
      let output = '';

      netstatProcess.stdout?.on('data', (data) => {
        output += data.toString();
      });

      netstatProcess.on('close', () => {
        resolve(output);
      });

      netstatProcess.on('error', () => {
        resolve('ERROR: Failed to run netstat');
      });
    });

    // Test our port detection logic
    const isInUse = await isPortInUse(port);

    // Find lines containing the port
    const lines = netstatOutput.split('\n');
    const portLines = lines.filter(line => line.includes(`:${port}`));

    // Test different regex patterns
    const patterns = {
      current: new RegExp(`:${port}\\s`),
      exact: new RegExp(`:${port} `),
      tab: new RegExp(`:${port}\\t`),
      flexible: new RegExp(`:${port}[\\s\\t]`),
      wordBoundary: new RegExp(`:${port}\\b`)
    };

    const patternResults = {};
    Object.entries(patterns).forEach(([name, pattern]) => {
      patternResults[name] = pattern.test(netstatOutput);
    });

    return NextResponse.json({
      port,
      isInUse,
      debug: {
        netstatLines: portLines,
        fullNetstatOutput: netstatOutput.split('\n').slice(0, 20), // First 20 lines
        patternResults,
        rawOutputLength: netstatOutput.length
      }
    });

  } catch (error) {
    return NextResponse.json({
      error: 'Internal server error',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}