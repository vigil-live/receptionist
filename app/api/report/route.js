import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import os from 'os';

export async function POST(req) {
  const { call_id } = await req.json();

  if (!call_id) {
    return NextResponse.json({ error: 'call_id is required' }, { status: 400 });
  }

  const scriptPath = path.resolve(process.cwd(), 'DB_PDF/sqlreport.py');

  const pythonCmd =
    process.env.PYTHON_PATH ||
    (os.platform() === 'win32' ? 'python' : 'python3');

  const reportPath = await new Promise((resolve, reject) => {
    const py = spawn(pythonCmd, [scriptPath, call_id]);

    let stdout = '';
    let stderr = '';

    py.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    py.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    py.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `Python exited with code ${code}`));
      } else {
        const match = stdout.match(/Report generated:\s*(.+)/);
        if (match) {
          resolve(match[1].trim());
        } else {
          reject(new Error('Could not parse report path from script output'));
        }
      }
    });
  }).catch((err) => {
    return NextResponse.json({ error: err.message }, { status: 500 });
  });

  if (reportPath instanceof NextResponse) return reportPath;

  if (!fs.existsSync(reportPath)) {
    return NextResponse.json({ error: 'Report file not found after generation' }, { status: 500 });
  }

  const fileBuffer = fs.readFileSync(reportPath);

  return new NextResponse(fileBuffer, {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="report_${call_id}.pdf"`,
    },
  });
}