'use client';

import React, { useState, useEffect, useRef } from 'react';
import { BranchingAgentDAG, DAGNode } from './BranchingAgentDAG';
import {
  Play,
  Pause,
  RotateCcw,
  Sparkles,
  Zap,
  Cpu,
  Database,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Radio,
  ChevronDown,
  Layers,
  Terminal,
} from 'lucide-react';

interface PipelineSummary {
  durationSeconds?: number;
  newJobsDiscovered?: number;
  newLeadsEnriched?: number;
  totalJobsInDb?: number;
  totalLeadsInDb?: number;
  totalCompaniesInDb?: number;
}

interface PipelineRunState {
  status: 'idle' | 'running' | 'done' | 'error';
  mode: 'live' | 'dry_run';
  startedAt: string | null;
  completedAt: string | null;
  goalState: 'pending' | 'running' | 'done';
  goalText: string;
  activeAgent: string;
  nodes: DAGNode[];
  summary: PipelineSummary | null;
  error: string | null;
}

export function AgentRadarView() {
  const [pipelineState, setPipelineState] = useState<PipelineRunState>({
    status: 'idle',
    mode: 'live',
    startedAt: null,
    completedAt: null,
    goalState: 'pending',
    goalText: 'Ready to Run Phase 1 Job Discovery & Recruiter Acquisition Pipeline',
    activeAgent: 'applypilot-brain',
    nodes: [],
    summary: null,
    error: null,
  });

  const [selectedMode, setSelectedMode] = useState<'live' | 'deep' | 'dry_run'>('live');
  const [selectedNode, setSelectedNode] = useState<DAGNode | null>(null);
  const [expandedNodeId, setExpandedNodeId] = useState<string | null>(null);
  const [isTriggering, setIsTriggering] = useState<boolean>(false);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Poll current pipeline status on mount
  const checkStatus = async () => {
    try {
      const res = await fetch('/api/pipeline/run');
      const data = await res.json();
      if (data.success && data.run) {
        setPipelineState(data.run);
        return data.run.status;
      }
    } catch (err) {
      console.error('Failed to query pipeline run state:', err);
    }
    return 'idle';
  };

  useEffect(() => {
    let active = true;

    async function initialLoad() {
      const status = await checkStatus();
      if (status === 'running' && active) {
        startPolling();
      } else if (status === 'idle') {
        // Load initial DB telemetry traces so the DAG is not empty on first visit
        loadInitialTelemetry();
      }
    }

    initialLoad();

    return () => {
      active = false;
      stopPolling();
    };
  }, []);

  const loadInitialTelemetry = async () => {
    try {
      const res = await fetch('/api/agent-pipeline/telemetry');
      const data = await res.json();
      if (data.success && data.nodes && data.nodes.length > 0) {
        setPipelineState((prev) => ({
          ...prev,
          nodes: data.nodes,
          goalState: 'done',
          goalText: 'Phase 1: Multi-Lane Acquisition Pipeline (Live Telemetry)',
          activeAgent: 'applypilot-brain',
          summary: {
            totalJobsInDb: data.stats?.totalJobs || 0,
            totalLeadsInDb: data.stats?.totalLeads || 0,
            totalCompaniesInDb: data.stats?.watchlistCompanies || 0,
          },
        }));
      }
    } catch (err) {
      console.error('Failed to load initial telemetry', err);
    }
  };

  const startPolling = () => {
    stopPolling();
    pollTimerRef.current = setInterval(async () => {
      const status = await checkStatus();
      if (status === 'done' || status === 'error') {
        stopPolling();
      }
    }, 500);
  };

  const stopPolling = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  // Trigger Phase 1 Scraping Pipeline
  const handleTriggerPipeline = async () => {
    try {
      setIsTriggering(true);
      const isDry = selectedMode === 'dry_run';
      const limit = selectedMode === 'deep' ? 50 : 25;
      const res = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: isDry ? 'dry_run' : 'live', limit }),
      });
      const data = await res.json();
      if (data.success && data.run) {
        setPipelineState(data.run);
        startPolling();
      }
    } catch (err) {
      console.error('Failed to trigger pipeline', err);
    } finally {
      setIsTriggering(false);
    }
  };

  // Reset Pipeline State
  const handleReset = async () => {
    stopPolling();
    try {
      const res = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'reset' }),
      });
      const data = await res.json();
      if (data.success && data.run) {
        setPipelineState(data.run);
      }
    } catch (err) {
      console.error('Failed to reset pipeline:', err);
    }
  };

  const isRunning = pipelineState.status === 'running' || isTriggering;
  const isDone = pipelineState.status === 'done';

  return (
    <div className="flex flex-col gap-4 w-full">
      {/* 1. COMPACT PIPELINE CONTROLLER & TRIGGER BAR */}
      <div className="liquid-glass rounded-3xl p-4 sm:p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 relative overflow-hidden shadow-sm">
        <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />

        {/* Title and Pipeline Description */}
        <div className="flex flex-col gap-1 min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-white shadow-sm transition-all ${
                isRunning
                  ? 'bg-purple-600 animate-pulse'
                  : isDone
                  ? 'bg-emerald-600'
                  : 'bg-zinc-800'
              }`}
            >
              {isRunning ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : isDone ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                <Cpu className="w-4 h-4" />
              )}
            </div>

            <h2 className="text-lg sm:text-xl font-bold tracking-tight text-zinc-900">
              Agent Radar: Phase 1 Acquisition Pipeline
            </h2>

            <span
              className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                isRunning
                  ? 'bg-purple-100 text-purple-800 border border-purple-200 animate-pulse'
                  : isDone
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                  : 'bg-zinc-100 text-zinc-700 border border-zinc-200'
              }`}
            >
              {isRunning ? 'Streaming Live' : isDone ? 'Acquisition Synchronized' : 'Ready to Run'}
            </span>
          </div>

          <p className="text-xs text-zinc-500">
            Multi-lane DAG executing JobSpy (Indeed, Naukri, LinkedIn), 11-ATS feeds, and Deep Company Looper. <strong>Every company discovered from Indeed is automatically researched, MX-verified, and enriched with 5–10 recruiter mailboxes.</strong>
          </p>
        </div>

        {/* Execution Actions & Mode Switcher */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0 flex-wrap w-full md:w-auto justify-between md:justify-end">
          {/* Mode Switcher Pill */}
          <div className="flex items-center gap-1 p-1 rounded-2xl liquid-glass-subtle border border-white/80">
            <button
              onClick={() => setSelectedMode('live')}
              disabled={isRunning}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                selectedMode === 'live'
                  ? 'liquid-pill bg-white shadow-xs text-zinc-950 font-bold'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              Live Sweep (25 Co.)
            </button>
            <button
              onClick={() => setSelectedMode('deep')}
              disabled={isRunning}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                selectedMode === 'deep'
                  ? 'liquid-pill bg-white shadow-xs text-emerald-700 font-bold'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              Deep Looper (50 Co.)
            </button>
            <button
              onClick={() => setSelectedMode('dry_run')}
              disabled={isRunning}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                selectedMode === 'dry_run'
                  ? 'liquid-pill bg-white shadow-xs text-purple-700 font-bold'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              Fast Preview (Dry Run)
            </button>
          </div>

          {/* Reset / Reload Button */}
          <button
            onClick={handleReset}
            disabled={isRunning}
            title="Reset Pipeline"
            className="liquid-pill rounded-2xl p-2.5 text-zinc-600 hover:text-zinc-950 disabled:opacity-40 transition-all cursor-pointer shadow-xs"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* MAIN PIPELINE TRIGGER BUTTON */}
          <button
            onClick={handleTriggerPipeline}
            disabled={isRunning}
            className={`liquid-pill rounded-2xl px-5 py-2.5 flex items-center gap-2 text-xs sm:text-sm font-bold shadow-md transition-all cursor-pointer ${
              isRunning
                ? 'bg-purple-600 text-white cursor-wait opacity-90'
                : 'liquid-pill-dark text-white hover:bg-zinc-900'
            }`}
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-purple-200" />
                <span>Running Phase 1 Pipeline...</span>
              </>
            ) : isDone ? (
              <>
                <Play className="w-4 h-4 fill-current text-emerald-400" />
                <span>Re-Run Phase 1 Workflow</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current text-purple-400" />
                <span>Run Complete Pipeline</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 2. LIVE METRICS & LANE LEGEND STRIP */}
      <div className="liquid-glass rounded-2xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
        {/* Lane Legend */}
        <div className="flex items-center gap-3 text-[11px] font-mono flex-wrap">
          <span className="text-zinc-400 font-sans font-medium text-xs">Lanes:</span>
          <span className="flex items-center gap-1.5 text-purple-700">
            <span className="w-2 h-2 rounded-full bg-purple-500" />
            Brain (Orchestrator)
          </span>
          <span className="flex items-center gap-1.5 text-emerald-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Harvester (Indeed / Naukri / LinkedIn)
          </span>
          <span className="flex items-center gap-1.5 text-amber-700">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            Looper (Recruiter Emails & MX)
          </span>
          <span className="flex items-center gap-1.5 text-blue-700">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            11-ATS Stream Radar
          </span>
        </div>

        {/* Live Metrics */}
        {pipelineState.summary && (
          <div className="flex items-center gap-3 text-xs font-medium text-zinc-600 flex-wrap">
            {pipelineState.summary.newJobsDiscovered !== undefined && (
              <span className="flex items-center gap-1">
                <span className="text-zinc-400">Harvested Jobs:</span>
                <span className="font-bold text-zinc-900 font-mono">
                  +{pipelineState.summary.newJobsDiscovered}
                </span>
              </span>
            )}
            {pipelineState.summary.newLeadsEnriched !== undefined && (
              <span className="flex items-center gap-1">
                <span className="text-zinc-400">Verified Leads:</span>
                <span className="font-bold text-emerald-600 font-mono">
                  +{pipelineState.summary.newLeadsEnriched}
                </span>
              </span>
            )}
            {pipelineState.summary.durationSeconds !== undefined && (
              <span className="flex items-center gap-1">
                <span className="text-zinc-400">Duration:</span>
                <span className="font-semibold text-zinc-800 font-mono">
                  {pipelineState.summary.durationSeconds}s
                </span>
              </span>
            )}
          </div>
        )}
      </div>

      {/* 3. PURE BRANCHING TIMELINE DAG ELEMENT (SHOWING ONLY NODES & TEXT ON RIGHT) */}
      <div className="liquid-glass rounded-3xl p-4 sm:p-6 shadow-sm overflow-hidden flex flex-col relative min-h-[460px]">
        <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />

        {/* DAG Container */}
        <div className="w-full overflow-x-auto py-2">
          {pipelineState.nodes.length > 0 ? (
            <BranchingAgentDAG
              nodes={pipelineState.nodes}
              goalState={pipelineState.goalState}
              goalText={pipelineState.goalText}
              activeAgent={pipelineState.activeAgent}
              selectedNodeId={selectedNode?.id}
              onSelectNode={(node) => {
                setSelectedNode(node);
                setExpandedNodeId(expandedNodeId === node.id ? null : node.id);
              }}
              triggerKey={`pipeline-${pipelineState.nodes.length}-${pipelineState.status}`}
            />
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-center gap-3">
              <div className="w-12 h-12 rounded-full liquid-glass flex items-center justify-center text-purple-600 shadow-sm">
                <Sparkles className="w-6 h-6 animate-pulse" />
              </div>
              <div className="flex flex-col gap-1 max-w-sm">
                <span className="font-semibold text-sm text-zinc-900">
                  Phase 1 Acquisition Pipeline Ready
                </span>
                <p className="text-xs text-zinc-500">
                  Click <strong>&quot;Run Complete Pipeline&quot;</strong> above to launch Omni-Channel Harvesters (Indeed, Naukri, LinkedIn), 11-ATS feeds, and the Deep Company Looper in real time.
                </p>
              </div>
              <button
                onClick={handleTriggerPipeline}
                className="liquid-pill rounded-2xl px-4 py-2 mt-2 text-xs font-bold text-zinc-900 hover:text-black flex items-center gap-2 shadow-xs cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current text-purple-600" />
                Launch Pipeline Now
              </button>
            </div>
          )}
        </div>

        {/* INLINE INSPECTION DETAILS (EXPANDS WHEN A NODE IS CLICKED) */}
        {selectedNode && expandedNodeId === selectedNode.id && (
          <div className="mt-4 p-4 rounded-2xl liquid-glass-subtle border border-white/80 animate-in fade-in slide-in-from-top-2 duration-200 flex flex-col gap-2">
            <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60">
              <div className="flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-purple-600" />
                <span className="font-bold text-xs text-zinc-900">
                  Node Telemetry: {selectedNode.text}
                </span>
              </div>
              <span className="text-[10px] font-mono text-zinc-500">
                Agent: {selectedNode.agent || 'applypilot-brain'}
              </span>
            </div>

            {selectedNode.desc && (
              <p className="text-xs text-zinc-600 leading-relaxed">
                {selectedNode.desc}
              </p>
            )}

            {selectedNode.outputs && Object.keys(selectedNode.outputs).length > 0 && (
              <div className="flex items-center gap-2 flex-wrap pt-1">
                {Object.entries(selectedNode.outputs).map(([k, v]) => (
                  <span
                    key={k}
                    className="text-[10.5px] font-mono px-2 py-0.5 rounded-lg bg-white/80 text-zinc-700 border border-zinc-200/50"
                  >
                    <strong>{k}:</strong> {Array.isArray(v) ? v.join(', ') : String(v)}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
