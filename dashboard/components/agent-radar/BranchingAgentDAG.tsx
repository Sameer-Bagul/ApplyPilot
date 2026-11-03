'use client';

import React, { useMemo } from 'react';
import { ScrambleText } from './ScrambleText';
import { Check, ShieldCheck, Zap, Radio, Globe, Terminal, Users, Sparkles } from 'lucide-react';

export interface DAGNode {
  id: string;
  lane: number;
  forkFromLane?: number;
  text: string;
  desc?: string;
  category: 'system' | 'harvester' | 'deep_looper' | 'ats_radar' | 'apply_worker' | 'outreach' | string;
  status: 'done' | 'running' | 'failed' | 'pending';
  time?: string;
  command?: string;
  agent?: string;
  route?: 'DUAL_ATTACK' | 'PORTAL_ONLY' | 'EMAIL_ONLY' | string;
  inputs?: Record<string, any>;
  outputs?: Record<string, any>;
}

export interface LaneDefinition {
  name: string;
  label: string;
  strokeColor: string;
  dotColor: string;
  badgeClass: string;
}

export const PIPELINE_LANES: Record<string, LaneDefinition> = {
  system: {
    name: 'Orchestrator',
    label: 'Brain',
    strokeColor: '#8B5CF6',
    dotColor: '#8B5CF6',
    badgeClass: 'bg-purple-50 text-purple-700 border border-purple-200/60',
  },
  harvester: {
    name: 'Directory Harvester',
    label: 'Harvester',
    strokeColor: '#10B981',
    dotColor: '#10B981',
    badgeClass: 'bg-emerald-50 text-emerald-700 border border-emerald-200/60',
  },
  deep_looper: {
    name: 'Deep Looper & MX',
    label: 'Looper',
    strokeColor: '#F59E0B',
    dotColor: '#F59E0B',
    badgeClass: 'bg-amber-50 text-amber-700 border border-amber-200/60',
  },
  ats_radar: {
    name: '11-ATS Radar',
    label: 'ATS Radar',
    strokeColor: '#3B82F6',
    dotColor: '#3B82F6',
    badgeClass: 'bg-blue-50 text-blue-700 border border-blue-200/60',
  },
  apply_worker: {
    name: 'Parallel CDP Workers',
    label: 'CDP Worker',
    strokeColor: '#F43F5E',
    dotColor: '#F43F5E',
    badgeClass: 'bg-rose-50 text-rose-700 border border-rose-200/60',
  },
  outreach: {
    name: 'Dual-Attack & HITL',
    label: 'Dual-Attack',
    strokeColor: '#6366F1',
    dotColor: '#6366F1',
    badgeClass: 'bg-indigo-50 text-indigo-700 border border-indigo-200/60',
  },
  default: {
    name: 'Agent Process',
    label: 'Process',
    strokeColor: '#64748B',
    dotColor: '#64748B',
    badgeClass: 'bg-zinc-100 text-zinc-700 border border-zinc-200/60',
  },
};

const ROW_HEIGHT = 44;
const BASE_X = 18;
const LANE_GAP = 18;

interface BranchingAgentDAGProps {
  nodes: DAGNode[];
  goalState?: 'pending' | 'running' | 'done';
  goalText?: string;
  activeAgent?: string;
  selectedNodeId?: string | null;
  onSelectNode?: (node: DAGNode) => void;
  triggerKey?: string | number;
}

export function BranchingAgentDAG({
  nodes = [],
  goalState = 'running',
  goalText = 'Autonomous Pipeline Execution',
  activeAgent = '',
  selectedNodeId = null,
  onSelectNode,
  triggerKey = 'pipeline',
}: BranchingAgentDAGProps) {
  const maxLane = useMemo(() => {
    if (!nodes.length) return 0;
    return Math.max(...nodes.map((n) => n.lane ?? 0), 0);
  }, [nodes]);

  const totalRows = nodes.length + 1;
  const svgHeight = totalRows * ROW_HEIGHT;
  const svgWidth = BASE_X + (maxLane + 1) * LANE_GAP + 24;

  const getLaneX = (laneIndex: number) => BASE_X + laneIndex * LANE_GAP;
  const getRowY = (rowIndex: number) => rowIndex * ROW_HEIGHT + ROW_HEIGHT / 2;

  // Group nodes by lane
  const laneGroups = useMemo(() => {
    const groups: Record<
      number,
      { lane: number; category: string; rows: number[]; nodes: (DAGNode & { rowIndex: number })[] }
    > = {};

    nodes.forEach((node, idx) => {
      const rowIndex = idx + 1;
      const lane = node.lane ?? 0;
      if (!groups[lane]) {
        groups[lane] = {
          lane,
          category: node.category,
          rows: [],
          nodes: [],
        };
      }
      groups[lane].rows.push(rowIndex);
      groups[lane].nodes.push({ ...node, rowIndex });
    });
    return groups;
  }, [nodes]);

  const goalX = getLaneX(0);
  const goalY = getRowY(0);

  const leftPadding = Math.max(56, BASE_X + (maxLane + 1) * LANE_GAP + 16);

  return (
    <div className="relative select-none w-full">
      {/* SVG MULTI-LANE GRAPH LAYER */}
      <svg
        width={svgWidth}
        height={svgHeight}
        className="absolute left-0 top-0 pointer-events-none z-10 overflow-visible"
      >
        {/* 1. CONTINUOUS INTRA-LANE VERTICAL TRACKS & FORK CURVES */}
        {Object.values(laneGroups).map((group) => {
          const laneDef = PIPELINE_LANES[group.category] || PIPELINE_LANES.default;
          const x = getLaneX(group.lane);
          const minRow = Math.min(...group.rows);
          const maxRow = Math.max(...group.rows);
          const yTop = getRowY(minRow);
          const yBottom = getRowY(maxRow);

          return (
            <g key={`lane-group-${group.lane}`}>
              {/* Continuous vertical track */}
              {maxRow > minRow && (
                <line
                  x1={x}
                  y1={yTop}
                  x2={x}
                  y2={yBottom}
                  stroke={laneDef.strokeColor}
                  strokeWidth="2"
                  strokeLinecap="round"
                  className="transition-all duration-300 opacity-80"
                />
              )}

              {/* Fork Curve from Parent Lane */}
              {group.lane > 0 && (() => {
                const bottomNode = group.nodes[group.nodes.length - 1];
                const parentLane =
                  typeof bottomNode.forkFromLane === 'number'
                    ? bottomNode.forkFromLane
                    : 0;

                const parentCandidates = nodes
                  .map((n, i) => ({ ...n, rowIndex: i + 1 }))
                  .filter((n) => (n.lane ?? 0) === parentLane && n.rowIndex > maxRow);

                if (!parentCandidates.length) {
                  // Connect to root goal or top of parent lane
                  const parentX = getLaneX(parentLane);
                  const parentY = yTop + 14;
                  return (
                    <path
                      d={`M ${parentX} ${parentY} C ${parentX} ${yTop - 6}, ${x} ${yTop - 6}, ${x} ${yTop}`}
                      fill="none"
                      stroke={laneDef.strokeColor}
                      strokeWidth="1.8"
                      strokeDasharray="3 2"
                      strokeOpacity="0.75"
                    />
                  );
                }

                const parentNode = parentCandidates[0];
                const parentX = getLaneX(parentLane);
                const parentY = getRowY(parentNode.rowIndex);
                const forkTurnY = Math.min(yBottom + 16, parentY - 4);

                const d = `M ${parentX} ${parentY} C ${parentX} ${forkTurnY}, ${x} ${yBottom + 12}, ${x} ${yBottom}`;

                return (
                  <path
                    d={d}
                    fill="none"
                    stroke={laneDef.strokeColor}
                    strokeWidth="1.8"
                    strokeDasharray="3 2"
                    strokeOpacity="0.75"
                  />
                );
              })()}
            </g>
          );
        })}

        {/* 2. BEZIER MERGE CURVES INTO TOP GOAL CIRCLE (WHEN DONE) */}
        {Object.values(laneGroups).map((group) => {
          const laneDef = PIPELINE_LANES[group.category] || PIPELINE_LANES.default;
          const x = getLaneX(group.lane);
          const minRow = Math.min(...group.rows);
          const yTopNode = getRowY(minRow);

          if (group.lane === 0) {
            return (
              <line
                key="merge-trunk-0"
                x1={goalX}
                y1={goalY + 8}
                x2={x}
                y2={yTopNode}
                stroke={laneDef.strokeColor}
                strokeWidth="2"
                strokeLinecap="round"
                strokeOpacity="0.85"
              />
            );
          }

          if (goalState !== 'done') return null;

          const curveStartY = goalY + 16 + group.lane * 3;
          const targetX = goalX + 6;
          const targetY = goalY + 2;

          const pathData = [
            `M ${x} ${yTopNode}`,
            `L ${x} ${curveStartY}`,
            `C ${x} ${goalY + 6}, ${targetX + group.lane * 3} ${goalY + 2}, ${targetX} ${targetY}`,
          ].join(' ');

          return (
            <path
              key={`merge-curve-lane-${group.lane}`}
              d={pathData}
              fill="none"
              stroke={laneDef.strokeColor}
              strokeWidth="2"
              strokeLinecap="round"
              className="animate-in fade-in duration-500"
            />
          );
        })}

        {/* 3. TOP GOAL / MERGE COMMIT CIRCLE */}
        {goalState === 'pending' && (
          <circle
            cx={goalX}
            cy={goalY}
            r="8"
            fill="white"
            stroke="#CBD5E1"
            strokeWidth="2"
            strokeDasharray="3 3"
          />
        )}

        {goalState === 'running' && (
          <g transform={`translate(${goalX}, ${goalY})`}>
            <circle
              r="8"
              fill="white"
              stroke="#8B5CF6"
              strokeWidth="2"
              strokeDasharray="3 3"
              className="animate-spin"
              style={{ animationDuration: '3s' }}
            />
            <circle r="3.5" fill="#8B5CF6" />
          </g>
        )}

        {goalState === 'done' && (
          <g>
            <circle cx={goalX} cy={goalY} r="10" fill="#10B981" fillOpacity="0.2" className="animate-pulse" />
            <circle cx={goalX} cy={goalY} r="7" fill="#10B981" />
          </g>
        )}

        {/* 4. NODE DOTS & ACTIVE PULSES */}
        {nodes.map((node, idx) => {
          const rowIndex = idx + 1;
          const x = getLaneX(node.lane ?? 0);
          const y = getRowY(rowIndex);
          const laneDef = PIPELINE_LANES[node.category] || PIPELINE_LANES.default;
          const isSelected = selectedNodeId === node.id;
          const isRunning = node.status === 'running';

          return (
            <g key={`dot-${node.id}`} className="transition-all duration-300">
              {/* White background badge */}
              <circle cx={x} cy={y} r="6.5" fill="white" />

              {/* Pulsing halo if running */}
              {isRunning && (
                <circle
                  cx={x}
                  cy={y}
                  r="10"
                  fill={laneDef.dotColor}
                  fillOpacity="0.25"
                  className="animate-ping"
                  style={{ animationDuration: '1.8s' }}
                />
              )}

              {/* Selected highlight ring */}
              {isSelected && (
                <circle
                  cx={x}
                  cy={y}
                  r="9"
                  fill="none"
                  stroke={laneDef.dotColor}
                  strokeWidth="2"
                  strokeOpacity="0.9"
                />
              )}

              {/* Core dot */}
              <circle
                cx={x}
                cy={y}
                r="4.5"
                fill={laneDef.dotColor}
                className="transition-transform duration-200"
              />
            </g>
          );
        })}
      </svg>

      {/* ROW LABELS & METADATA LAYER */}
      <div className="relative z-0 flex flex-col">
        {/* ROW 0: TOP GOAL / PIPELINE MERGE ROW */}
        <div
          style={{
            height: `${ROW_HEIGHT}px`,
            paddingLeft: `${leftPadding}px`,
          }}
          className="flex items-center justify-between pr-3 text-sm transition-all duration-200 border-b border-zinc-200/50 bg-white/40 rounded-t-2xl"
        >
          <div className="flex items-center gap-2.5 min-w-0 pr-3 truncate">
            {goalState === 'done' ? (
              <span className="flex items-center gap-1.5 font-semibold text-emerald-700">
                <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                <ScrambleText
                  text={goalText}
                  triggerKey={`goal-done-${triggerKey}-${goalText}`}
                  duration={450}
                  preservePrefix={6}
                />
              </span>
            ) : (
              <span className="flex items-center gap-2 font-medium text-zinc-800">
                <Sparkles className="w-4 h-4 text-purple-600 animate-spin" style={{ animationDuration: '4s' }} />
                <span>{goalText}</span>
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {activeAgent && (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200/60">
                active: {activeAgent}
              </span>
            )}
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full tracking-wide uppercase ${
                goalState === 'done'
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-amber-100 text-amber-800 animate-pulse'
              }`}
            >
              {goalState === 'done' ? 'Completed' : 'Streaming'}
            </span>
          </div>
        </div>

        {/* ROWS 1..N: CHILD NODES */}
        {nodes.map((node, idx) => {
          const lane = node.lane ?? 0;
          const laneDef = PIPELINE_LANES[node.category] || PIPELINE_LANES.default;
          const isSelected = selectedNodeId === node.id;
          const isRunning = node.status === 'running';

          return (
            <div
              key={node.id}
              onClick={() => onSelectNode && onSelectNode(node)}
              style={{
                height: `${ROW_HEIGHT}px`,
                paddingLeft: `${leftPadding}px`,
              }}
              className={`relative flex items-center justify-between pr-3 text-xs transition-all duration-150 cursor-pointer border-b border-zinc-100/60 ${
                isSelected
                  ? 'bg-purple-50/70 shadow-sm border-purple-200/50'
                  : 'hover:bg-white/60'
              }`}
            >
              <div className="flex-1 min-w-0 flex items-center gap-2 pr-2 overflow-hidden">
                <span
                  className={`truncate transition-colors ${
                    isSelected ? 'font-semibold text-zinc-900' : 'font-medium text-zinc-700'
                  }`}
                >
                  <ScrambleText
                    text={node.text}
                    triggerKey={`${triggerKey}-${node.id}`}
                    duration={420}
                    preservePrefix={4}
                  />
                </span>

                {/* Category lane pill */}
                <span
                  className={`shrink-0 px-2 py-0.5 rounded-md text-[10.5px] font-mono font-medium ${laneDef.badgeClass}`}
                >
                  {laneDef.label}
                </span>

                {/* Dual-Attack Route pill */}
                {node.route === 'DUAL_ATTACK' && (
                  <span className="hidden sm:inline-flex items-center gap-1 shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-600 border border-rose-200/50">
                    <Zap className="w-2.5 h-2.5" />
                    DUAL
                  </span>
                )}
              </div>

              {/* Right status info */}
              <div className="flex items-center gap-2 shrink-0">
                {isRunning ? (
                  <span className="text-[11px] font-mono text-amber-600 animate-pulse font-medium">
                    in progress...
                  </span>
                ) : (
                  <span className="text-[11px] font-mono text-zinc-500 bg-zinc-100/70 px-2 py-0.5 rounded border border-zinc-200/40">
                    {node.time || 'Done'}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

