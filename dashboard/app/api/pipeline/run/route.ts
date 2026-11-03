import { NextResponse } from 'next/server';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

export interface PipelineRunNode {
  id: string;
  lane: number;
  forkFromLane?: number;
  text: string;
  desc?: string;
  category: string;
  status: 'done' | 'running' | 'failed' | 'pending';
  time?: string;
  command?: string;
  agent?: string;
  route?: string;
  inputs?: Record<string, any>;
  outputs?: Record<string, any>;
}

export interface PipelineRunState {
  status: 'idle' | 'running' | 'done' | 'error';
  mode: 'live' | 'dry_run';
  startedAt: string | null;
  completedAt: string | null;
  goalState: 'pending' | 'running' | 'done';
  goalText: string;
  activeAgent: string;
  nodes: PipelineRunNode[];
  logs: string[];
  summary: Record<string, any> | null;
  error: string | null;
}

// Global in-memory state shared across requests within the server process
declare global {
  // eslint-disable-next-line no-var
  var __applypilot_pipeline_run__: PipelineRunState | undefined;
  // eslint-disable-next-line no-var
  var __applypilot_process_running__: boolean | undefined;
}

function getInitialState(): PipelineRunState {
  return {
    status: 'idle',
    mode: 'live',
    startedAt: null,
    completedAt: null,
    goalState: 'pending',
    goalText: 'Ready to Run Phase 1 Job Discovery Pipeline',
    activeAgent: 'applypilot-brain',
    nodes: [],
    logs: [],
    summary: null,
    error: null,
  };
}

if (!global.__applypilot_pipeline_run__) {
  global.__applypilot_pipeline_run__ = getInitialState();
  global.__applypilot_process_running__ = false;
}

export async function GET() {
  return NextResponse.json({
    success: true,
    run: global.__applypilot_pipeline_run__,
    isRunning: global.__applypilot_process_running__,
  });
}

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const action = body.action || 'start';

    if (action === 'reset') {
      global.__applypilot_pipeline_run__ = getInitialState();
      global.__applypilot_process_running__ = false;
      return NextResponse.json({ success: true, run: global.__applypilot_pipeline_run__ });
    }

    if (global.__applypilot_process_running__) {
      return NextResponse.json({
        success: true,
        message: 'Pipeline is already running',
        run: global.__applypilot_pipeline_run__,
        isRunning: true,
      });
    }

    const mode: 'live' | 'dry_run' = body.mode === 'dry_run' ? 'dry_run' : 'live';
    const limit = typeof body.limit === 'number' ? body.limit : 20;

    // Reset state for new run
    global.__applypilot_process_running__ = true;
    global.__applypilot_pipeline_run__ = {
      status: 'running',
      mode,
      startedAt: new Date().toISOString(),
      completedAt: null,
      goalState: 'running',
      goalText: 'Phase 1: Autonomous Job & Lead Acquisition Pipeline',
      activeAgent: 'applypilot-brain',
      nodes: [],
      logs: [],
      summary: null,
      error: null,
    };

    // Locate repository root & python venv
    const repoRoot = path.resolve(process.cwd(), '..');
    const pythonBin = fs.existsSync(path.join(repoRoot, '.venv', 'bin', 'python'))
      ? path.join(repoRoot, '.venv', 'bin', 'python')
      : 'python3';

    const scriptPath = path.join(repoRoot, 'src', 'applypilot', 'pipeline_runner_api.py');

    const proc = spawn(
      pythonBin,
      [scriptPath, '--mode', mode, '--limit', String(limit)],
      {
        cwd: repoRoot,
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
      }
    );

    proc.stdout.on('data', (chunk: Buffer) => {
      const text = chunk.toString();
      const lines = text.split('\n');

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const evt = JSON.parse(line);
          const state = global.__applypilot_pipeline_run__;
          if (!state) continue;

          state.logs.push(line);

          if (evt.type === 'start') {
            state.goalText = evt.goalText || state.goalText;
            state.status = 'running';
            state.goalState = 'running';
          } else if (evt.type === 'node') {
            const newNode: PipelineRunNode = {
              id: evt.id,
              lane: evt.lane ?? 0,
              forkFromLane: evt.forkFromLane,
              text: evt.text || 'Processing...',
              desc: evt.desc,
              category: evt.category || 'system',
              status: evt.status || 'running',
              agent: evt.agent || 'applypilot-brain',
              time: evt.time,
              command: evt.command,
              route: evt.route,
              inputs: evt.inputs,
              outputs: evt.outputs,
            };
            state.nodes.push(newNode);
            state.activeAgent = evt.agent || state.activeAgent;
          } else if (evt.type === 'node_update') {
            const existing = state.nodes.find((n) => n.id === evt.id);
            if (existing) {
              if (evt.status) existing.status = evt.status;
              if (evt.text) existing.text = evt.text;
              if (evt.time) existing.time = evt.time;
              if (evt.outputs) existing.outputs = { ...(existing.outputs || {}), ...evt.outputs };
              if (evt.desc) existing.desc = evt.desc;
            }
          } else if (evt.type === 'done') {
            state.goalState = 'done';
            state.status = 'done';
            state.completedAt = new Date().toISOString();
            state.goalText = evt.goalText || 'Phase 1: Scraping Complete';
            state.summary = evt.summary || null;
            global.__applypilot_process_running__ = false;
          }
        } catch {
          // Plain log line fallback
          global.__applypilot_pipeline_run__?.logs.push(line);
        }
      }
    });

    proc.stderr.on('data', (chunk: Buffer) => {
      const errMsg = chunk.toString();
      console.warn('[pipeline_runner stderr]', errMsg);
      global.__applypilot_pipeline_run__?.logs.push(`[stderr] ${errMsg}`);
    });

    proc.on('close', (code) => {
      global.__applypilot_process_running__ = false;
      const state = global.__applypilot_pipeline_run__;
      if (state) {
        state.completedAt = new Date().toISOString();
        if (code !== 0 && state.status !== 'done') {
          state.status = 'error';
          state.error = `Pipeline process exited with code ${code}`;
          state.goalState = 'pending';
        } else {
          state.status = 'done';
          state.goalState = 'done';
        }
      }
    });

    proc.on('error', (err) => {
      global.__applypilot_process_running__ = false;
      const state = global.__applypilot_pipeline_run__;
      if (state) {
        state.status = 'error';
        state.error = `Failed to spawn pipeline runner: ${err.message}`;
      }
    });

    return NextResponse.json({
      success: true,
      message: 'Pipeline started successfully',
      run: global.__applypilot_pipeline_run__,
      isRunning: true,
    });
  } catch (err: any) {
    global.__applypilot_process_running__ = false;
    return NextResponse.json(
      { success: false, error: err.message || 'Failed to trigger pipeline' },
      { status: 500 }
    );
  }
}

