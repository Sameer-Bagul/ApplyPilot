'use client';

import React, { useState } from 'react';
import { DAGNode, PIPELINE_LANES } from './BranchingAgentDAG';
import {
  Terminal,
  Copy,
  Check,
  Zap,
  Cpu,
  Layers,
  ArrowRight,
  ShieldCheck,
  FileCode,
  Globe,
  Radio,
  Clock,
  Sparkles,
} from 'lucide-react';

interface NodeInspectorProps {
  node: DAGNode | null;
  onClose?: () => void;
}

export function NodeInspector({ node }: NodeInspectorProps) {
  const [activeTab, setActiveTab] = useState<'action' | 'telemetry' | 'architecture'>('action');
  const [copiedPayload, setCopiedPayload] = useState(false);
  const [copiedCommand, setCopiedCommand] = useState(false);

  if (!node) {
    return (
      <div className="liquid-glass rounded-3xl p-6 flex flex-col items-center justify-center min-h-[420px] text-center text-zinc-400 gap-3 border border-white/80">
        <div className="w-12 h-12 rounded-2xl bg-zinc-100 flex items-center justify-center text-zinc-400 shadow-inner">
          <Cpu className="w-6 h-6" />
        </div>
        <p className="text-sm font-medium text-zinc-600">Select any node in the DAG</p>
        <p className="text-xs text-zinc-400 max-w-xs leading-relaxed">
          Click any step on the left branching timeline to inspect live tool calls, CDP selectors, verified emails, and execution payloads.
        </p>
      </div>
    );
  }

  const laneDef = PIPELINE_LANES[node.category] || PIPELINE_LANES.default;

  const copyToClipboard = (text: string, type: 'command' | 'payload') => {
    navigator.clipboard.writeText(text);
    if (type === 'command') {
      setCopiedCommand(true);
      setTimeout(() => setCopiedCommand(false), 2000);
    } else {
      setCopiedPayload(true);
      setTimeout(() => setCopiedPayload(false), 2000);
    }
  };

  return (
    <div className="liquid-glass rounded-3xl p-5 flex flex-col gap-4 relative overflow-hidden shadow-sm">
      <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-white/95 to-transparent pointer-events-none z-20" />
      {/* Node Header */}
      <div className="flex flex-col gap-2 pb-3 border-b border-zinc-200/60">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${laneDef.badgeClass}`}>
                {laneDef.name}
              </span>
              {node.route === 'DUAL_ATTACK' && (
                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-600 border border-rose-200/60">
                  <Zap className="w-3 h-3" />
                  DUAL ATTACK
                </span>
              )}
              <span
                className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full tracking-wider ${
                  node.status === 'done'
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60'
                    : 'bg-amber-50 text-amber-700 border border-amber-200/60 animate-pulse'
                }`}
              >
                {node.status}
              </span>
            </div>
            <h3 className="text-base font-semibold text-zinc-900 tracking-tight leading-snug">
              {node.text}
            </h3>
          </div>
        </div>

        {node.desc && (
          <p className="text-xs text-zinc-500 leading-relaxed">
            {node.desc}
          </p>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1.5 p-1 rounded-2xl liquid-glass-subtle border border-white/80">
        <button
          onClick={() => setActiveTab('action')}
          className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'action'
              ? 'liquid-pill bg-white shadow-xs text-zinc-950 font-bold'
              : 'text-zinc-500 hover:text-zinc-800'
          }`}
        >
          Action & Tool
        </button>
        <button
          onClick={() => setActiveTab('telemetry')}
          className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'telemetry'
              ? 'liquid-pill bg-white shadow-xs text-zinc-950 font-bold'
              : 'text-zinc-500 hover:text-zinc-800'
          }`}
        >
          Telemetry
        </button>
        <button
          onClick={() => setActiveTab('architecture')}
          className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'architecture'
              ? 'liquid-pill bg-white shadow-xs text-zinc-950 font-bold'
              : 'text-zinc-500 hover:text-zinc-800'
          }`}
        >
          Agent Spec
        </button>
      </div>

      {/* Tab 1: Action & Invoked Tool */}
      {activeTab === 'action' && (
        <div className="flex flex-col gap-3">
          {/* Invocation Box */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-xs text-zinc-500">
              <span className="flex items-center gap-1 font-medium">
                <Terminal className="w-3.5 h-3.5 text-zinc-600" />
                Invoked Tool / Command
              </span>
              {node.command && (
                <button
                  onClick={() => copyToClipboard(node.command!, 'command')}
                  className="hover:text-zinc-900 flex items-center gap-1 cursor-pointer transition-colors"
                >
                  {copiedCommand ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-600" />
                      <span className="text-[10px] text-emerald-600 font-medium">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span className="text-[10px]">Copy</span>
                    </>
                  )}
                </button>
              )}
            </div>

            <div className="p-3 rounded-2xl bg-zinc-900 text-zinc-200 font-mono text-xs overflow-x-auto shadow-inner leading-relaxed select-all">
              {node.command || 'Direct autonomous subagent execution'}
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-2 text-xs pt-1">
            <div className="p-2.5 rounded-2xl bg-white/60 border border-zinc-200/50 flex flex-col gap-0.5">
              <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider">Agent Identifier</span>
              <span className="font-mono font-medium text-zinc-800 truncate">{node.agent || 'applypilot-core'}</span>
            </div>
            <div className="p-2.5 rounded-2xl bg-white/60 border border-zinc-200/50 flex flex-col gap-0.5">
              <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider">Latency / Time</span>
              <span className="font-mono font-medium text-zinc-800">{node.time || 'Immediate'}</span>
            </div>
            <div className="p-2.5 rounded-2xl bg-white/60 border border-zinc-200/50 flex flex-col gap-0.5">
              <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider">Execution Lane</span>
              <span className="font-mono font-medium text-zinc-800">Lane {node.lane} ({laneDef.label})</span>
            </div>
            <div className="p-2.5 rounded-2xl bg-white/60 border border-zinc-200/50 flex flex-col gap-0.5">
              <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider">Attack Vector</span>
              <span className="font-mono font-medium text-rose-600">{node.route || 'HYBRID'}</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Telemetry JSON */}
      {activeTab === 'telemetry' && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span className="font-medium flex items-center gap-1.5">
              <FileCode className="w-3.5 h-3.5" />
              Runtime Payload (Inputs & Outputs)
            </span>
            <button
              onClick={() =>
                copyToClipboard(
                  JSON.stringify({ inputs: node.inputs, outputs: node.outputs }, null, 2),
                  'payload'
                )
              }
              className="hover:text-zinc-900 flex items-center gap-1 cursor-pointer transition-colors"
            >
              {copiedPayload ? (
                <>
                  <Check className="w-3 h-3 text-emerald-600" />
                  <span className="text-[10px] text-emerald-600 font-medium">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span className="text-[10px]">Copy JSON</span>
                </>
              )}
            </button>
          </div>

          <div className="p-3 rounded-2xl bg-zinc-950 text-emerald-400 font-mono text-[11px] overflow-x-auto max-h-64 shadow-inner leading-relaxed">
            <pre>
              {JSON.stringify(
                {
                  id: node.id,
                  agent: node.agent,
                  route: node.route,
                  inputs: node.inputs || {},
                  outputs: node.outputs || {},
                },
                null,
                2
              )}
            </pre>
          </div>
        </div>
      )}

      {/* Tab 3: Agent Spec & Architecture */}
      {activeTab === 'architecture' && (
        <div className="flex flex-col gap-2.5 text-xs text-zinc-600 leading-relaxed">
          <div className="p-3 rounded-2xl bg-white/70 border border-zinc-200/60 flex flex-col gap-1.5">
            <span className="font-semibold text-zinc-900 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-purple-600" />
              Autonomous Role in Dual-Attack Pipeline
            </span>
            <p className="text-[11px] text-zinc-500">
              {node.category === 'harvester' &&
                'Scans Bangalore startup lists, VC boards (Getro/Consider), and seed directories, extracting unindexed startups directly into career_watchlist.'}
              {node.category === 'deep_looper' &&
                'Loops over active companies, querying DuckDuckGo for recruiter leads, verifying Google DoH MX records, and generating verified emails with 280-char notes.'}
              {node.category === 'ats_radar' &&
                'Polls 11 major ATS platforms (Ashby, Greenhouse, Lever, Workday) and Schema.org JobPosting feeds using ETag change detection.'}
              {node.category === 'apply_worker' &&
                'Operates an isolated Chrome DevTools Protocol session (ports 9222+wid) to solve form fields using Tier 0 cached selectors and zero-token deterministic fills.'}
              {node.category === 'outreach' &&
                'Simultaneously executes verified recruiter outreach while syncing Gmail IMAP for candidate responses, 2FA OTP codes, and unparking jobs.'}
              {node.category === 'system' &&
                'Orchestrates state across all worker threads, tracking execution transitions in apply_traces and synchronizing the master SQLite database.'}
            </p>
          </div>

          <div className="p-3 rounded-2xl bg-white/70 border border-zinc-200/60 flex flex-col gap-1">
            <span className="font-semibold text-zinc-900 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              Reliability & Guardrails
            </span>
            <p className="text-[11px] text-zinc-500">
              Failures escalate to Human-In-The-Loop (HITL) via email dispatch. Workday accounts and OTPs are decrypted and handled with zero cloud token leak.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

