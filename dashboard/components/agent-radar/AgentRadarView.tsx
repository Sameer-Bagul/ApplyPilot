'use client';

import React, { useState, useEffect, useRef } from 'react';
import { BranchingAgentDAG, DAGNode } from './BranchingAgentDAG';
import { NodeInspector } from './NodeInspector';
import {
  Play,
  Pause,
  SkipForward,
  SkipBack,
  RotateCcw,
  Radio,
  Sparkles,
  Zap,
  Cpu,
  Layers,
  Database,
  RefreshCw,
  SlidersHorizontal,
  Activity,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';

interface ScenarioStep {
  stepName: string;
  goalState: 'pending' | 'running' | 'done';
  goalText: string;
  activeAgent: string;
  footerText: string;
  nodes: DAGNode[];
}

interface Scenario {
  id: string;
  title: string;
  subtitle: string;
  goalText: string;
  steps: ScenarioStep[];
}

export function AgentRadarView() {
  const [mode, setMode] = useState<'scenario' | 'live'>('scenario');
  const [scenarios, setScenarios] = useState<Record<string, Scenario>>({});
  const [selectedScenarioKey, setSelectedScenarioKey] = useState<string>('daily_cycle');
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [selectedNode, setSelectedNode] = useState<DAGNode | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Live Telemetry Mode state
  const [liveData, setLiveData] = useState<{
    nodes: DAGNode[];
    stats: {
      totalJobs: number;
      totalLeads: number;
      watchlistCompanies: number;
      tracesRecorded: number;
    };
  } | null>(null);
  const [liveLoading, setLiveLoading] = useState<boolean>(false);
  const [lastLivePoll, setLastLivePoll] = useState<string>('');

  // Fetch scenarios on mount
  useEffect(() => {
    async function loadScenarios() {
      try {
        setLoading(true);
        const res = await fetch('/api/agent-pipeline/scenarios');
        const data = await res.json();
        if (data.success && data.scenarios) {
          setScenarios(data.scenarios);
          // Auto select first node of first step
          const initialNodes = data.scenarios.daily_cycle?.steps[0]?.nodes || [];
          if (initialNodes.length > 0) {
            setSelectedNode(initialNodes[0]);
          }
        }
      } catch (err) {
        console.error('Failed to load scenarios', err);
      } finally {
        setLoading(false);
      }
    }
    loadScenarios();
  }, []);

  // Fetch live telemetry
  const fetchLiveTelemetry = async () => {
    try {
      setLiveLoading(true);
      const res = await fetch('/api/agent-pipeline/telemetry');
      const data = await res.json();
      if (data.success) {
        setLiveData({
          nodes: data.nodes || [],
          stats: data.stats || {
            totalJobs: 0,
            totalLeads: 0,
            watchlistCompanies: 0,
            tracesRecorded: 0,
          },
        });
        setLastLivePoll(new Date().toLocaleTimeString());
        if (data.nodes && data.nodes.length > 0 && !selectedNode) {
          setSelectedNode(data.nodes[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load live telemetry', err);
    } finally {
      setLiveLoading(false);
    }
  };

  useEffect(() => {
    if (mode === 'live') {
      fetchLiveTelemetry();
      const interval = setInterval(fetchLiveTelemetry, 5000);
      return () => clearInterval(interval);
    }
  }, [mode]);

  // Current active scenario and step
  const activeScenario = scenarios[selectedScenarioKey];
  const totalSteps = activeScenario?.steps?.length || 1;
  const currentStep = activeScenario?.steps[currentStepIndex];

  // Auto-advance scenario playback
  useEffect(() => {
    if (mode !== 'scenario' || !isPlaying || !activeScenario) return;

    const baseDelay = 2600;
    const intervalTime = Math.max(700, baseDelay / playbackSpeed);

    const timer = setTimeout(() => {
      setCurrentStepIndex((prev) => {
        const next = prev + 1;
        if (next >= totalSteps) {
          setIsPlaying(false);
          return prev;
        }
        return next;
      });
    }, intervalTime);

    return () => clearTimeout(timer);
  }, [mode, isPlaying, currentStepIndex, totalSteps, playbackSpeed, activeScenario]);

  // When step changes, update selected node to the newly added node if none selected or if active
  useEffect(() => {
    if (mode === 'scenario' && currentStep && currentStep.nodes.length > 0) {
      const lastNode = currentStep.nodes[currentStep.nodes.length - 1];
      setSelectedNode(lastNode);
    }
  }, [currentStepIndex, mode]);

  const handleStepPrev = () => {
    setIsPlaying(false);
    setCurrentStepIndex((prev) => Math.max(0, prev - 1));
  };

  const handleStepNext = () => {
    setIsPlaying(false);
    setCurrentStepIndex((prev) => Math.min(totalSteps - 1, prev + 1));
  };

  const handleReset = () => {
    setCurrentStepIndex(0);
    setIsPlaying(true);
  };

  return (
    <div className="flex flex-col gap-6">
      {/* 1. TOP HEADER & MODE CONTROLS */}
      <div className="liquid-glass rounded-3xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 relative overflow-hidden shadow-sm">
        <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 shadow-sm">
              <Activity className="w-4 h-4 animate-pulse" />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-zinc-900">
              Agent Execution Radar & DAG
            </h2>
            <span className="text-[10px] uppercase font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60">
              Real-Time Directed Graph
            </span>
          </div>
          <p className="text-xs text-zinc-500">
            Multi-lane visualization of autonomous harvesters, deep loopers, 11-ATS launch detection, and Dual-Attack parallel CDP workers.
          </p>
        </div>

        {/* Mode Switcher: Simulation Scenarios vs Live SQLite Telemetry */}
        <div className="flex items-center gap-2 p-1.5 rounded-2xl liquid-glass-subtle border border-white/80 self-stretch md:self-auto">
          <button
            onClick={() => {
              setMode('scenario');
              setIsPlaying(true);
            }}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              mode === 'scenario'
                ? 'liquid-pill bg-white shadow-sm text-purple-700'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-600" />
            Pipeline Simulator
          </button>

          <button
            onClick={() => {
              setMode('live');
              setIsPlaying(false);
              fetchLiveTelemetry();
            }}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              mode === 'live'
                ? 'liquid-pill bg-white shadow-sm text-emerald-700'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            <Database className="w-3.5 h-3.5 text-emerald-600" />
            Live DB Telemetry
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping shrink-0" />
          </button>
        </div>
      </div>

      {/* 2. PLAYBACK TRANSPORT OR LIVE STATUS BAR */}
      {mode === 'scenario' ? (
        <div className="liquid-glass rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4 relative overflow-hidden shadow-sm">
          <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
          {/* Scenario Selection */}
          <div className="flex items-center gap-3 w-full md:w-auto">
            <span className="text-xs font-semibold text-zinc-700 shrink-0">Scenario:</span>
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
              {Object.keys(scenarios).map((sKey) => {
                const sc = scenarios[sKey];
                const isActive = selectedScenarioKey === sKey;
                return (
                  <button
                    key={sKey}
                    onClick={() => {
                      setSelectedScenarioKey(sKey);
                      setCurrentStepIndex(0);
                      setIsPlaying(true);
                    }}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
                      isActive
                        ? 'liquid-pill-dark shadow-sm'
                        : 'liquid-pill text-zinc-600 hover:text-zinc-900'
                    }`}
                  >
                    {sc.title}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Transport Controls */}
          <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
            {/* Step Counter */}
            <div className="text-xs font-mono text-zinc-600 px-3 py-1 rounded-xl liquid-glass-subtle border border-white/80">
              Phase <span className="font-semibold text-zinc-900">{currentStepIndex + 1}</span> of {totalSteps}
            </div>

            {/* Transport Buttons */}
            <div className="flex items-center gap-1">
              <button
                onClick={handleReset}
                title="Restart Scenario"
                className="liquid-pill rounded-xl p-2 text-zinc-600 hover:text-zinc-900 transition-all cursor-pointer shadow-xs"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleStepPrev}
                disabled={currentStepIndex === 0}
                title="Previous Step"
                className="liquid-pill rounded-xl p-2 text-zinc-600 hover:text-zinc-900 disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer shadow-xs"
              >
                <SkipBack className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                title={isPlaying ? 'Pause' : 'Play'}
                className="liquid-pill rounded-xl px-3.5 py-2 bg-purple-600 text-white hover:bg-purple-700 transition-all cursor-pointer shadow-md flex items-center gap-1.5 text-xs font-semibold"
              >
                {isPlaying ? (
                  <>
                    <Pause className="w-3.5 h-3.5" />
                    Pause
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    Play
                  </>
                )}
              </button>
              <button
                onClick={handleStepNext}
                disabled={currentStepIndex >= totalSteps - 1}
                title="Next Step"
                className="liquid-pill rounded-xl p-2 text-zinc-600 hover:text-zinc-900 disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer shadow-xs"
              >
                <SkipForward className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Speed Selector */}
            <div className="flex items-center gap-1 liquid-glass-subtle p-1 rounded-xl border border-white/80">
              {[1, 2, 4].map((spd) => (
                <button
                  key={spd}
                  onClick={() => setPlaybackSpeed(spd)}
                  className={`px-2 py-0.5 rounded-lg text-[11px] font-mono font-medium transition-all cursor-pointer ${
                    playbackSpeed === spd
                      ? 'liquid-pill bg-white text-zinc-900 shadow-xs font-bold'
                      : 'text-zinc-500 hover:text-zinc-900'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Live Mode Status Bar */
        <div className="liquid-glass rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4 relative overflow-hidden shadow-sm">
          <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
          <div className="flex items-center gap-3">
            <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-zinc-900">Connected to ~/.applypilot/applypilot.db</span>
              {lastLivePoll && (
                <span className="text-[11px] font-mono text-zinc-400">
                  (updated {lastLivePoll})
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4 flex-wrap text-xs">
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-400">Jobs:</span>
              <span className="font-semibold text-zinc-800">{liveData?.stats?.totalJobs ?? 0}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-400">Verified Leads:</span>
              <span className="font-semibold text-emerald-600">{liveData?.stats?.totalLeads ?? 0}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-400">Watchlist:</span>
              <span className="font-semibold text-zinc-800">{liveData?.stats?.watchlistCompanies ?? 0}</span>
            </div>
            <button
              onClick={fetchLiveTelemetry}
              disabled={liveLoading}
              className="liquid-pill flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-zinc-700 text-xs font-semibold shadow-xs transition-all cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${liveLoading ? 'animate-spin' : ''}`} />
              Refresh Now
            </button>
          </div>
        </div>
      )}

      {/* 3. MAIN SPLIT VIEWPORT: DAG GRAPH ON LEFT, NODE INSPECTOR ON RIGHT */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT / CENTER: Directed Acyclic Graph */}
        <div className="lg:col-span-7 flex flex-col gap-3">
          <div className="liquid-glass rounded-3xl p-5 shadow-sm overflow-hidden flex flex-col gap-3 min-h-[440px] relative">
            <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
            {/* Graph Header / Legend */}
            <div className="flex items-center justify-between pb-3 border-b border-zinc-200/60">
              <span className="text-xs font-semibold text-zinc-700 uppercase tracking-wider flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-purple-600" />
                Multi-Lane Agent Pipeline
              </span>

              {/* Lane Color Badges */}
              <div className="flex items-center gap-1.5 text-[10px] font-mono flex-wrap">
                <span className="flex items-center gap-1 text-purple-700">
                  <span className="w-2 h-2 rounded-full bg-purple-500" />
                  Brain
                </span>
                <span className="flex items-center gap-1 text-emerald-700">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Harvester
                </span>
                <span className="flex items-center gap-1 text-amber-700">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  Looper
                </span>
                <span className="flex items-center gap-1 text-blue-700">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  ATS
                </span>
                <span className="flex items-center gap-1 text-rose-700">
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  Worker
                </span>
                <span className="flex items-center gap-1 text-indigo-700">
                  <span className="w-2 h-2 rounded-full bg-indigo-500" />
                  Outreach
                </span>
              </div>
            </div>

            {/* DAG Canvas */}
            <div className="w-full overflow-x-auto py-2">
              {mode === 'scenario' ? (
                currentStep ? (
                  <BranchingAgentDAG
                    nodes={currentStep.nodes}
                    goalState={currentStep.goalState}
                    goalText={currentStep.goalText}
                    activeAgent={currentStep.activeAgent}
                    selectedNodeId={selectedNode?.id}
                    onSelectNode={(node) => setSelectedNode(node)}
                    triggerKey={`${selectedScenarioKey}-${currentStepIndex}`}
                  />
                ) : (
                  <div className="p-8 text-center text-xs text-zinc-400">Loading scenario DAG...</div>
                )
              ) : liveData && liveData.nodes.length > 0 ? (
                <BranchingAgentDAG
                  nodes={liveData.nodes}
                  goalState="done"
                  goalText="Live Production Telemetry Stream"
                  activeAgent="applypilot-brain"
                  selectedNodeId={selectedNode?.id}
                  onSelectNode={(node) => setSelectedNode(node)}
                  triggerKey={`live-telemetry-${liveData.nodes.length}`}
                />
              ) : (
                <div className="p-8 text-center text-xs text-zinc-400">
                  {liveLoading ? 'Querying database traces...' : 'No telemetry events recorded yet.'}
                </div>
              )}
            </div>

            {/* Step Footer Subtext */}
            {mode === 'scenario' && currentStep?.footerText && (
              <div className="mt-2 p-3 rounded-2xl bg-white/50 border border-zinc-200/50 text-xs text-zinc-500 flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                <span className="truncate">{currentStep.footerText}</span>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: Deep Node Inspector */}
        <div className="lg:col-span-5">
          <NodeInspector node={selectedNode} />
        </div>
      </div>

      {/* 4. REAL-TIME 11-ATS PLATFORM GRID & ARCHITECTURE REFERENCE */}
      <div className="liquid-glass rounded-3xl p-6 flex flex-col gap-4 border border-white/80 shadow-sm">
        <div className="flex flex-col gap-1 pb-3 border-b border-zinc-200/60">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio className="w-4 h-4 text-blue-500 animate-pulse" />
              <h3 className="text-base font-semibold text-zinc-900 tracking-tight">
                11-ATS Keyless Stream Poller & ETag Change Detection
              </h3>
            </div>
            <span className="text-[11px] font-mono text-zinc-400">Zero Auth Required</span>
          </div>
          <p className="text-xs text-zinc-500">
            ApplyPilot connects directly to public REST/JSON APIs, XML streams, and JSON-LD Schema.org feeds with millisecond launch detection.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {[
            { name: 'Naukri India', status: 'JobSpy API', type: 'naukri.com' },
            { name: 'Indeed (India/US)', status: 'Live API', type: 'in.indeed.com' },
            { name: 'LinkedIn Jobs', status: 'Direct Stream', type: 'linkedin.com/jobs' },
            { name: 'Greenhouse', status: 'Live API', type: 'boards-api.greenhouse.io' },
            { name: 'Lever', status: 'Live API', type: 'api.lever.co' },
            { name: 'Ashby', status: 'REST & GraphQL', type: 'api.ashbyhq.com' },
            { name: 'Workday', status: 'CXS Endpoint', type: 'host/wday/cxs' },
            { name: 'Workable', status: 'Widget API', type: 'apply.workable.com' },
            { name: 'SmartRecruiters', status: 'Postings API', type: 'api.smartrecruiters.com' },
            { name: 'BambooHR', status: 'Careers List', type: 'slug.bamboohr.com' },
            { name: 'Recruitee', status: 'Offers API', type: 'slug.recruitee.com' },
            { name: 'Teamtailor', status: 'JSON Feed', type: 'slug.teamtailor.com' },
            { name: 'Breezy HR', status: 'JSON Feed', type: 'slug.breezy.hr' },
            { name: 'Personio', status: 'XML Stream', type: 'slug.jobs.personio.de' },
            { name: 'Custom Pages', status: 'JSON-LD + ETag', type: 'Schema.org JobPosting' },
          ].map((ats, idx) => (
            <div key={idx} className="liquid-glass rounded-2xl p-3 flex flex-col gap-1.5 border border-white/60">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-zinc-900">{ats.name}</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
              </div>
              <span className="text-[10px] text-emerald-600 font-medium">{ats.status}</span>
              <span className="text-[9.5px] text-zinc-400 font-mono truncate">{ats.type}</span>
            </div>
          ))}
        </div>

        {/* CLI Autonomous Control Reference */}
        <div className="liquid-glass rounded-2xl p-4 flex flex-col gap-2 mt-2 bg-white/40 border border-zinc-200/50">
          <span className="text-xs font-semibold text-zinc-700 tracking-wide">
            Autonomous CLI Discovery & Looper Shortcuts
          </span>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 font-mono text-[11px] text-zinc-700">
            <div className="p-2.5 rounded-xl bg-zinc-900 text-zinc-200 select-all truncate">
              uv run applypilot run discover --source naukri --source indeed
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-900 text-zinc-200 select-all truncate">
              uv run applypilot loop-companies --tier 1 --limit 50 --target-emails 8
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-900 text-zinc-200 select-all truncate">
              uv run applypilot run-daily --dry-run
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

