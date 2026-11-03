import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Check,
  Search,
  Plus,
  Folder,
  Mic,
  Mail,
  Copy,
  RotateCcw,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  GitBranch,
  Building2,
  Code2,
  Sparkles,
  GitMerge,
  Layers,
  Terminal,
  BookOpen,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  Cloud,
  FileCode,
  ArrowRight,
  ChevronRight,
  Command,
  Zap,
  Wrench,
  HelpCircle,
  Filter
} from 'lucide-react';

// ============================================================================
// 1. CRYPTOGRAPHIC TEXT SCRAMBLE COMPONENT
// Replicates the exact 520ms random alphanumeric decoding glitch seen in the video
// ============================================================================
const SCRAMBLE_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789';

function ScrambleText({
  text = '',
  triggerKey,
  duration = 520,
  preservePrefix = 5,
  className = ''
}) {
  const [display, setDisplay] = useState(text);
  const prevKeyRef = useRef(null);

  useEffect(() => {
    if (prevKeyRef.current === triggerKey) {
      setDisplay(text);
      return;
    }
    prevKeyRef.current = triggerKey;

    let frameId;
    const startTime = performance.now();

    const tick = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);

      if (progress >= 1) {
        setDisplay(text);
        return;
      }

      const revealCount = Math.floor(
        preservePrefix + (text.length - preservePrefix) * Math.pow(progress, 0.85)
      );

      let result = '';
      for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (
          i < revealCount ||
          ch === ' ' ||
          ch === '·' ||
          ch === ':' ||
          ch === '-' ||
          ch === '/'
        ) {
          result += ch;
        } else {
          result += SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)];
        }
      }
      setDisplay(result);
      frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [text, triggerKey, duration, preservePrefix]);

  return <span className={className}>{display}</span>;
}

// ============================================================================
// 2. SPINNER ARC & DATA-FLOW ZONE BADGE
// ============================================================================
function SpinnerArc({ size = 15, colorClass = 'text-gray-400' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      className={`animate-spin ${colorClass} shrink-0`}
      style={{ animationDuration: '0.9s' }}
    >
      <circle
        cx="8"
        cy="8"
        r="6"
        stroke="currentColor"
        strokeOpacity="0.22"
        strokeWidth="1.65"
      />
      <path
        d="M14 8a6 6 0 0 0-6-6"
        stroke="currentColor"
        strokeWidth="1.65"
        strokeLinecap="round"
      />
    </svg>
  );
}

// ============================================================================
// 3. REUSABLE MULTI-LANE GIT DAG / BRANCHING TIMELINE ENGINE
//    - Renders parallel horizontal lanes (lane 0..4 at x = 12, 26, 40, 54, 68)
//    - Connects nodes on the same lane with continuous vertical SVG tracks
//    - Draws optional fork curves from parent lanes below
//    - When `goalState === 'done'`, draws smooth SVG cubic-bezier merge curves
//      from the top node of EVERY active lane up into the green merge circle!
// ============================================================================
const ROW_HEIGHT = 34;
const BASE_X = 12;
const LANE_GAP = 14;

export function BranchingGitTimeline({
  nodes = [],
  lanesConfig = {},
  goalState = 'pending',
  goalText = 'Write the brief',
  goalRight = null,
  showForkCurves = true,
  showHighlightsOnComplete = true,
  seenNodeIds = new Set(),
  scenarioKey = 'kestrel',
  onSelectNode = null,
  selectedNodeId = null
}) {
  const maxLane = useMemo(() => {
    if (!nodes.length) return 0;
    return Math.max(...nodes.map((n) => n.lane || 0), 0);
  }, [nodes]);

  const totalRows = nodes.length + 1;
  const svgHeight = totalRows * ROW_HEIGHT;
  const svgWidth = BASE_X + (maxLane + 1) * LANE_GAP + 24;

  const getLaneX = (laneIndex) => BASE_X + laneIndex * LANE_GAP;
  const getRowY = (rowIndex) => rowIndex * ROW_HEIGHT + ROW_HEIGHT / 2;

  const laneGroups = useMemo(() => {
    const groups = {};
    nodes.forEach((node, idx) => {
      const rowIndex = idx + 1;
      const lane = node.lane || 0;
      if (!groups[lane]) {
        groups[lane] = {
          lane,
          category: node.category,
          rows: [],
          nodes: []
        };
      }
      groups[lane].rows.push(rowIndex);
      groups[lane].nodes.push({ ...node, rowIndex });
    });
    return groups;
  }, [nodes]);

  const goalX = getLaneX(0);
  const goalY = getRowY(0);

  return (
    <div className="relative select-none">
      {/* SVG MULTI-LANE GRAPH LAYER */}
      <svg
        width={svgWidth}
        height={svgHeight}
        className="absolute left-0 top-0 pointer-events-none z-10 overflow-visible"
      >
        {/* 1. CONTINUOUS INTRA-LANE VERTICAL TRACKS + FORK CURVES */}
        {Object.values(laneGroups).map((group) => {
          const laneStyle = lanesConfig[group.category] || lanesConfig.default;
          const x = getLaneX(group.lane);
          const minRow = Math.min(...group.rows);
          const maxRow = Math.max(...group.rows);
          const yTop = getRowY(minRow);
          const yBottom = getRowY(maxRow);

          return (
            <g key={`lane-track-${group.lane}`}>
              {maxRow > minRow && (
                <line
                  x1={x}
                  y1={yTop}
                  x2={x}
                  y2={yBottom}
                  stroke={laneStyle.strokeColor}
                  strokeWidth="1.65"
                  strokeLinecap="round"
                  className="transition-all duration-300"
                />
              )}

              {showForkCurves && group.lane > 0 && (() => {
                const bottomNode = group.nodes[group.nodes.length - 1];
                const parentLane =
                  typeof bottomNode.forkFromLane === 'number'
                    ? bottomNode.forkFromLane
                    : 0;
                const parentCandidates = nodes
                  .map((n, i) => ({ ...n, rowIndex: i + 1 }))
                  .filter(
                    (n) => (n.lane || 0) === parentLane && n.rowIndex > maxRow
                  );

                if (!parentCandidates.length) return null;
                const parentNode = parentCandidates[0];
                const parentX = getLaneX(parentLane);
                const parentY = getRowY(parentNode.rowIndex);
                const forkTurnY = Math.min(yBottom + 16, parentY - 4);

                const d = `M ${parentX} ${parentY} C ${parentX} ${forkTurnY}, ${x} ${
                  yBottom + 12
                }, ${x} ${yBottom}`;

                return (
                  <path
                    d={d}
                    fill="none"
                    stroke={laneStyle.strokeColor}
                    strokeWidth="1.5"
                    strokeDasharray={bottomNode.dashedFork ? '3 2' : undefined}
                    strokeOpacity="0.8"
                  />
                );
              })()}
            </g>
          );
        })}

        {/* 2. BEZIER MERGE CURVES INTO TOP SYNTHESIS / RELEASE NODE */}
        {Object.values(laneGroups).map((group) => {
          const laneStyle = lanesConfig[group.category] || lanesConfig.default;
          const x = getLaneX(group.lane);
          const minRow = Math.min(...group.rows);
          const yTopNode = getRowY(minRow);

          if (group.lane === 0) {
            if (goalState !== 'done' && !showForkCurves) return null;
            return (
              <line
                key="merge-trunk-0"
                x1={goalX}
                y1={goalY + 7}
                x2={x}
                y2={yTopNode}
                stroke={laneStyle.strokeColor}
                strokeWidth="1.65"
                strokeLinecap="round"
                className="animate-merge-draw"
              />
            );
          }

          if (goalState !== 'done') return null;

          const curveStartY = goalY + 14 + group.lane * 2.5;
          const targetX = goalX + 5;
          const targetY = goalY + 1.5;

          const pathData = [
            `M ${x} ${yTopNode}`,
            `L ${x} ${curveStartY}`,
            `C ${x} ${goalY + 5}, ${targetX + group.lane * 4} ${goalY + 2}, ${targetX} ${targetY}`
          ].join(' ');

          return (
            <path
              key={`merge-curve-lane-${group.lane}`}
              d={pathData}
              fill="none"
              stroke={laneStyle.strokeColor}
              strokeWidth="1.65"
              strokeLinecap="round"
              className="animate-merge-draw"
            />
          );
        })}

        {/* 3. TOP GOAL / MERGE COMMIT NODE CIRCLE */}
        {goalState === 'pending' && (
          <circle
            cx={goalX}
            cy={goalY}
            r="6.5"
            fill="white"
            stroke="#CBD5E1"
            strokeWidth="1.5"
            strokeDasharray="2.5 2.5"
          />
        )}

        {goalState === 'writing' && (
          <g transform={`translate(${goalX}, ${goalY})`}>
            <circle
              r="6.5"
              fill="white"
              stroke="#94A3B8"
              strokeWidth="1.5"
              strokeDasharray="2.6 2.4"
              className="animate-spin"
              style={{ animationDuration: '3s' }}
            />
          </g>
        )}

        {goalState === 'done' && (
          <g>
            <circle
              cx={goalX}
              cy={goalY}
              r="7.5"
              fill="#16A34A"
              fillOpacity="0.15"
            />
            <circle cx={goalX} cy={goalY} r="6" fill="#16A34A" />
          </g>
        )}

        {/* 4. CHILD DISCOVERY / COMMIT NODE DOTS */}
        {nodes.map((node, idx) => {
          const rowIndex = idx + 1;
          const x = getLaneX(node.lane || 0);
          const y = getRowY(rowIndex);
          const laneStyle = lanesConfig[node.category] || lanesConfig.default;
          const isSelected = selectedNodeId === node.id;

          return (
            <g key={`dot-${node.id}`}>
              <circle cx={x} cy={y} r="5.2" fill="white" />
              {isSelected && (
                <circle
                  cx={x}
                  cy={y}
                  r="6.5"
                  fill="none"
                  stroke={laneStyle.dotColor}
                  strokeWidth="1.5"
                  strokeOpacity="0.5"
                />
              )}
              <circle
                cx={x}
                cy={y}
                r="3.8"
                fill={laneStyle.dotColor}
                className="transition-all duration-300"
              />
            </g>
          );
        })}
      </svg>

      {/* ROW LABELS & METADATA LAYER */}
      <div className="relative z-0 flex flex-col">
        {/* ROW 0: TOP GOAL / MERGE COMMIT ROW */}
        <div
          style={{
            height: `${ROW_HEIGHT}px`,
            paddingLeft: `${Math.max(38, BASE_X + maxLane * LANE_GAP + 18)}px`
          }}
          className="flex items-center justify-between pr-1 text-[15px] transition-all duration-300"
        >
          <div className="flex-1 min-w-0 pr-3 truncate">
            {goalState === 'done' ? (
              <ScrambleText
                text={goalText}
                triggerKey={`goal-done-${scenarioKey}-${goalText}`}
                duration={500}
                preservePrefix={8}
                className="font-semibold text-[#111827]"
              />
            ) : (
              <span className="text-[#6B7280] font-normal">{goalText}</span>
            )}
          </div>

          {goalRight && (
            <span className="text-[13px] font-mono text-[#6B7280] shrink-0">
              {goalRight}
            </span>
          )}
        </div>

        {/* ROWS 1..N: CHILD NODES */}
        {nodes.map((node, idx) => {
          const lane = node.lane || 0;
          const laneStyle = lanesConfig[node.category] || lanesConfig.default;

          const prevNode = idx > 0 ? nodes[idx - 1] : null;
          const isFirstInCategoryGroup =
            !prevNode || prevNode.category !== node.category;

          const isNewlyInserted = !seenNodeIds.has(node.id);

          const minTextLeft = Math.max(
            38 + lane * 8,
            BASE_X + maxLane * LANE_GAP + 16
          );

          const isHighlighted =
            showHighlightsOnComplete &&
            goalState === 'done' &&
            node.highlightedOnComplete;

          const isSelected = selectedNodeId === node.id;

          return (
            <div
              key={node.id}
              onClick={() => onSelectNode && onSelectNode(node)}
              style={{
                height: `${ROW_HEIGHT}px`,
                paddingLeft: `${minTextLeft}px`
              }}
              className={`relative flex items-center justify-between pr-1.5 rounded-lg text-[14px] transition-all duration-200 ${
                onSelectNode ? 'cursor-pointer' : ''
              } ${isNewlyInserted ? 'animate-node-enter' : ''} ${
                isSelected
                  ? 'bg-blue-50/90 ring-1 ring-blue-200'
                  : isHighlighted
                  ? 'bg-[#ECFDF5]/75 hover:bg-[#ECFDF5]'
                  : 'hover:bg-gray-50/80'
              }`}
            >
              <div className="flex-1 min-w-0 flex items-center gap-2 pr-3 overflow-hidden">
                <span
                  className={`truncate transition-colors duration-200 ${
                    node.bold
                      ? 'font-medium text-[#111827]'
                      : 'font-normal text-[#6B7280]'
                  }`}
                >
                  <ScrambleText
                    text={node.text}
                    triggerKey={node.id}
                    duration={520}
                    preservePrefix={5}
                  />
                </span>

                {isFirstInCategoryGroup && (
                  <span
                    className={`shrink-0 px-2 py-[1px] rounded-md text-[11.5px] font-mono leading-5 ${laneStyle.badgeClass}`}
                  >
                    {laneStyle.label}
                  </span>
                )}
              </div>

              {/* Right-aligned Command or Source Domain */}
              <span className="shrink-0 text-[12.5px] font-mono text-[#6B7280] tracking-tight bg-gray-100/70 px-1.5 py-0.5 rounded">
                {node.source}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// 4. SHARED LANE PALETTES
// ============================================================================
const DEFAULT_GIT_LANES = {
  main: {
    label: 'main',
    dotColor: '#64748B',
    strokeColor: '#CBD5E1',
    badgeClass: 'bg-slate-100 text-slate-700'
  },
  develop: {
    label: 'develop',
    dotColor: '#10B981',
    strokeColor: '#6EE7B7',
    badgeClass: 'bg-emerald-50 text-emerald-700'
  },
  feature: {
    label: 'feature/*',
    dotColor: '#2563EB',
    strokeColor: '#93C5FD',
    badgeClass: 'bg-blue-50 text-blue-700'
  },
  hotfix: {
    label: 'hotfix/*',
    dotColor: '#8B5CF6',
    strokeColor: '#C4B5FD',
    badgeClass: 'bg-violet-50 text-violet-700'
  },
  automation: {
    label: 'gh-cli / ci',
    dotColor: '#F59E0B',
    strokeColor: '#FCD34D',
    badgeClass: 'bg-amber-50 text-amber-800'
  },
  company: {
    label: 'company',
    dotColor: '#94A3B8',
    strokeColor: '#CBD5E1',
    badgeClass: 'bg-[#F3F4F6] text-[#4B5563]'
  },
  news: {
    label: 'news',
    dotColor: '#10B981',
    strokeColor: '#6EE7B7',
    badgeClass: 'bg-[#ECFDF5] text-[#047857]'
  },
  people: {
    label: 'people',
    dotColor: '#2563EB',
    strokeColor: '#93C5FD',
    badgeClass: 'bg-[#EFF6FF] text-[#1D4ED8]'
  },
  default: {
    label: 'git',
    dotColor: '#94A3B8',
    strokeColor: '#CBD5E1',
    badgeClass: 'bg-gray-100 text-gray-700'
  }
};

// ============================================================================
// 5. CURATED MULTI-STEP VISUAL SCENARIOS (TEACHING ALL 24 LEVELS + KESTREL REPLICA)
// ============================================================================
const SCENARIOS = {
  // 1. Level 1-2: Zero to GitHub Repo
  level1_2: {
    id: 'level1_2',
    badge: 'Levels 0–2',
    label: 'Zero to Published GitHub Repo',
    entityTitle: 'my-project · Repo Bootstrap Flow',
    domain: 'github.com/you/my-project',
    searchQuery: 'gh repo create --source=. --push',
    workspaceChip: 'Level 0–2 Fundamentals',
    placeholder: 'Type a git or gh command (e.g. git add -p, git commit -m "feat")...',
    defaultShowForks: true,
    lanesConfig: DEFAULT_GIT_LANES,
    steps: [
      {
        timeLabel: 'Step 1: Auth & Config',
        duration: 1400,
        showDomain: false,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'Publish local project to GitHub',
        goalRight: 'Level 0–1',
        nodes: [
          {
            id: 'l1-2',
            lane: 0,
            category: 'main',
            text: 'Configured global user.name, user.email & init.defaultBranch',
            source: 'git config --global',
            cmd: 'git config --global init.defaultBranch main',
            bold: false
          },
          {
            id: 'l1-1',
            lane: 4,
            category: 'automation',
            text: 'Authenticated GitHub CLI session via OAuth / SSH Ed25519 key',
            source: 'gh auth login',
            cmd: 'gh auth login',
            bold: true,
            highlightedOnComplete: true
          }
        ],
        pills: [
          { id: 'auth', label: 'gh auth', state: 'done', detail: 'logged in' },
          { id: 'init', label: 'git init', state: 'checking', detail: 'running' },
          { id: 'stage', label: 'Index', state: 'queued', detail: 'queued' },
          { id: 'remote', label: 'origin', state: 'queued', detail: 'queued' }
        ],
        footerText: 'Running gh auth status & git config --show-origin · Step 1 of 4',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 2: Init & Interactive Stage',
        duration: 1500,
        showDomain: false,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'Publish local project to GitHub',
        goalRight: 'Level 1',
        nodes: [
          {
            id: 'l1-4',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Interactively staged verified hunks into .git/index',
            source: 'git add -p',
            cmd: 'git add -p',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'l1-3',
            lane: 0,
            category: 'main',
            text: 'Initialized empty Git repository on branch main',
            source: 'git init -b main',
            cmd: 'git init -b main',
            bold: false
          },
          {
            id: 'l1-2',
            lane: 0,
            category: 'main',
            text: 'Configured global user.name, user.email & init.defaultBranch',
            source: 'git config --global',
            cmd: 'git config --global init.defaultBranch main',
            bold: false
          },
          {
            id: 'l1-1',
            lane: 4,
            category: 'automation',
            text: 'Authenticated GitHub CLI session via OAuth / SSH Ed25519 key',
            source: 'gh auth login',
            cmd: 'gh auth login',
            bold: true,
            highlightedOnComplete: true
          }
        ],
        pills: [
          { id: 'auth', label: 'gh auth', state: 'done', detail: 'logged in' },
          { id: 'init', label: 'git init', state: 'done', detail: 'main' },
          { id: 'stage', label: 'Index', state: 'checking', detail: '3 hunks' },
          { id: 'remote', label: 'origin', state: 'queued', detail: 'queued' }
        ],
        footerText: 'Inspecting staged changes with git diff --staged · Step 2 of 4',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 3: Commit Snapshot',
        duration: 1600,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'writing',
        goalText: 'Creating remote repository & pushing...',
        goalRight: 'Level 1–2',
        nodes: [
          {
            id: 'l1-6',
            lane: 1,
            category: 'develop',
            text: 'Recorded root tree & commit snapshot in object database',
            source: 'git commit -m',
            cmd: 'git commit -m "Initial commit"',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'l1-5',
            lane: 1,
            category: 'develop',
            text: 'Verified staged diff & porcelain status before commit',
            source: 'git diff --staged',
            cmd: 'git diff --staged',
            bold: false
          },
          {
            id: 'l1-4',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Interactively staged verified hunks into .git/index',
            source: 'git add -p',
            cmd: 'git add -p',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'l1-3',
            lane: 0,
            category: 'main',
            text: 'Initialized empty Git repository on branch main',
            source: 'git init -b main',
            cmd: 'git init -b main',
            bold: false
          },
          {
            id: 'l1-2',
            lane: 0,
            category: 'main',
            text: 'Configured global user.name, user.email & init.defaultBranch',
            source: 'git config --global',
            cmd: 'git config --global init.defaultBranch main',
            bold: false
          },
          {
            id: 'l1-1',
            lane: 4,
            category: 'automation',
            text: 'Authenticated GitHub CLI session via OAuth / SSH Ed25519 key',
            source: 'gh auth login',
            cmd: 'gh auth login',
            bold: true,
            highlightedOnComplete: true
          }
        ],
        pills: [
          { id: 'auth', label: 'gh auth', state: 'done', detail: 'logged in' },
          { id: 'init', label: 'git init', state: 'done', detail: 'main' },
          { id: 'stage', label: 'Commit', state: 'done', detail: 'a1b2c3d' },
          { id: 'remote', label: 'origin', state: 'checking', detail: 'pushing' }
        ],
        footerText: 'Provisioning GitHub repository via gh repo create · Step 3 of 4',
        footerDone: false,
        ctaMode: 'email'
      },
      {
        timeLabel: 'Step 4: Published & Tracked',
        duration: 3000,
        showDomain: true,
        headerStatus: 'complete',
        goalState: 'done',
        goalText: 'Published: origin/main tracking active',
        goalRight: '7 commands',
        nodes: [
          {
            id: 'l1-7',
            lane: 0,
            category: 'main',
            text: 'Created GitHub repo, linked origin & pushed upstream main',
            source: 'gh repo create --push',
            cmd: 'gh repo create my-project --public --source=. --remote=origin --push',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'l1-6',
            lane: 1,
            category: 'develop',
            text: 'Recorded root tree & commit snapshot in object database',
            source: 'git commit -m',
            cmd: 'git commit -m "Initial commit"',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'l1-5',
            lane: 1,
            category: 'develop',
            text: 'Verified staged diff & porcelain status before commit',
            source: 'git diff --staged',
            cmd: 'git diff --staged',
            bold: false
          },
          {
            id: 'l1-4',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Interactively staged verified hunks into .git/index',
            source: 'git add -p',
            cmd: 'git add -p',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'l1-3',
            lane: 0,
            category: 'main',
            text: 'Initialized empty Git repository on branch main',
            source: 'git init -b main',
            cmd: 'git init -b main',
            bold: false
          },
          {
            id: 'l1-2',
            lane: 0,
            category: 'main',
            text: 'Configured global user.name, user.email & init.defaultBranch',
            source: 'git config --global',
            cmd: 'git config --global init.defaultBranch main',
            bold: false
          },
          {
            id: 'l1-1',
            lane: 4,
            category: 'automation',
            text: 'Authenticated GitHub CLI session via OAuth / SSH Ed25519 key',
            source: 'gh auth login',
            cmd: 'gh auth login',
            bold: true,
            highlightedOnComplete: true
          }
        ],
        pills: [
          { id: 'auth', label: 'gh auth', state: 'done', detail: 'verified' },
          { id: 'init', label: 'git init', state: 'done', detail: 'main' },
          { id: 'stage', label: 'Commit', state: 'done', detail: 'a1b2c3d' },
          { id: 'remote', label: 'origin/main', state: 'done', detail: 'tracked' }
        ],
        footerText: 'Repository live on GitHub · upstream origin/main synchronized',
        footerDone: true,
        ctaMode: 'copy'
      }
    ]
  },

  // 2. Level 3-4: Complete Branch Network (main + develop + feature/* + hotfix/*)
  level3_4: {
    id: 'level3_4',
    badge: 'Levels 3–4',
    label: 'Branch Network & Hotfix Topology',
    entityTitle: 'Branch Network · Multi-Lane GitFlow',
    domain: 'main <- develop <- feature/* + hotfix/*',
    searchQuery: 'git log --oneline --graph --decorate --all',
    workspaceChip: 'Level 3–4 Branch Network',
    placeholder: 'Try: git switch -c feature/payments, git merge --no-ff...',
    defaultShowForks: true,
    lanesConfig: DEFAULT_GIT_LANES,
    steps: [
      {
        timeLabel: 'Step 1: Fork Integration Branch',
        duration: 1400,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'Release v2.4: Merge all active lanes',
        goalRight: '4 lanes',
        nodes: [
          {
            id: 'b2',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Created & pushed integration branch origin/develop',
            source: 'git switch -c develop',
            cmd: 'git switch -c develop && git push -u origin develop',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b1',
            lane: 0,
            category: 'main',
            text: 'Fast-forward synced production trunk origin/main',
            source: 'git pull --ff-only',
            cmd: 'git pull --ff-only origin main',
            bold: false
          }
        ],
        pills: [
          { id: 'main', label: 'main', state: 'done', detail: 'v2.3.0' },
          { id: 'dev', label: 'develop', state: 'checking', detail: 'active' },
          { id: 'feat', label: 'feature/*', state: 'queued', detail: 'queued' },
          { id: 'hotfix', label: 'hotfix/*', state: 'queued', detail: 'queued' }
        ],
        footerText: 'Branching develop from main · Step 1 of 4',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 2: Spawn Parallel Feature Branches',
        duration: 1500,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'Release v2.4: Merge all active lanes',
        goalRight: '4 lanes',
        nodes: [
          {
            id: 'b4',
            lane: 2,
            category: 'feature',
            text: 'Implemented OAuth2 PKCE + JWT session rotation',
            source: 'feature/auth',
            cmd: 'git switch -c feature/auth develop',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b3',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Forked feature/dashboard & feature/auth from develop',
            source: 'git switch -c',
            cmd: 'git push -u origin feature/auth',
            bold: false
          },
          {
            id: 'b2',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Created & pushed integration branch origin/develop',
            source: 'git switch -c develop',
            cmd: 'git switch -c develop && git push -u origin develop',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b1',
            lane: 0,
            category: 'main',
            text: 'Fast-forward synced production trunk origin/main',
            source: 'git pull --ff-only',
            cmd: 'git pull --ff-only origin main',
            bold: false
          }
        ],
        pills: [
          { id: 'main', label: 'main', state: 'done', detail: 'v2.3.0' },
          { id: 'dev', label: 'develop', state: 'done', detail: 'synced' },
          { id: 'feat', label: 'feature/*', state: 'checking', detail: '2 branches' },
          { id: 'hotfix', label: 'hotfix/*', state: 'queued', detail: 'standby' }
        ],
        footerText: 'Developing parallel features on Lane 2 · Step 2 of 4',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 3: Urgent Production Hotfix on Lane 3',
        duration: 1700,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'writing',
        goalText: 'Merging hotfix & develop into main...',
        goalRight: '4 lanes',
        nodes: [
          {
            id: 'b6',
            lane: 1,
            category: 'develop',
            text: 'Back-merged hotfix/payment-crash into develop branch',
            source: 'git merge origin/main',
            cmd: 'git switch develop && git merge origin/main',
            bold: false
          },
          {
            id: 'b5',
            lane: 3,
            forkFromLane: 0,
            category: 'hotfix',
            text: 'Patched critical Stripe webhook crash directly off main',
            source: 'hotfix/payment-crash',
            cmd: 'git switch -c hotfix/payment-crash main',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b4',
            lane: 2,
            category: 'feature',
            text: 'Implemented OAuth2 PKCE + JWT session rotation',
            source: 'feature/auth',
            cmd: 'git switch -c feature/auth develop',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b3',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Forked feature/dashboard & feature/auth from develop',
            source: 'git switch -c',
            cmd: 'git push -u origin feature/auth',
            bold: false
          },
          {
            id: 'b2',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Created & pushed integration branch origin/develop',
            source: 'git switch -c develop',
            cmd: 'git switch -c develop && git push -u origin develop',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b1',
            lane: 0,
            category: 'main',
            text: 'Fast-forward synced production trunk origin/main',
            source: 'git pull --ff-only',
            cmd: 'git pull --ff-only origin main',
            bold: false
          }
        ],
        pills: [
          { id: 'main', label: 'main', state: 'done', detail: 'v2.3.1' },
          { id: 'dev', label: 'develop', state: 'done', detail: 'merged' },
          { id: 'feat', label: 'feature/*', state: 'done', detail: 'ready' },
          { id: 'hotfix', label: 'hotfix/*', state: 'done', detail: 'patched' }
        ],
        footerText: 'Preparing --no-ff release merge & pruning merged branches · Step 3 of 4',
        footerDone: false,
        ctaMode: 'email'
      },
      {
        timeLabel: 'Step 4: Bezier Octopus Release Merge',
        duration: 3200,
        showDomain: true,
        headerStatus: 'complete',
        goalState: 'done',
        goalText: 'Released v2.4.0: All 4 branch lanes merged',
        goalRight: '4 lanes · 7 commits',
        nodes: [
          {
            id: 'b7',
            lane: 0,
            category: 'main',
            text: 'Merged develop into main (--no-ff) & pruned stale branches',
            source: 'git merge --no-ff',
            cmd: 'git merge --no-ff origin/develop && git fetch --all --prune',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b6',
            lane: 1,
            category: 'develop',
            text: 'Back-merged hotfix/payment-crash into develop branch',
            source: 'git merge origin/main',
            cmd: 'git switch develop && git merge origin/main',
            bold: false
          },
          {
            id: 'b5',
            lane: 3,
            forkFromLane: 0,
            category: 'hotfix',
            text: 'Patched critical Stripe webhook crash directly off main',
            source: 'hotfix/payment-crash',
            cmd: 'git switch -c hotfix/payment-crash main',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b4',
            lane: 2,
            category: 'feature',
            text: 'Implemented OAuth2 PKCE + JWT session rotation',
            source: 'feature/auth',
            cmd: 'git switch -c feature/auth develop',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b3',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Forked feature/dashboard & feature/auth from develop',
            source: 'git switch -c',
            cmd: 'git push -u origin feature/auth',
            bold: false
          },
          {
            id: 'b2',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Created & pushed integration branch origin/develop',
            source: 'git switch -c develop',
            cmd: 'git switch -c develop && git push -u origin develop',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'b1',
            lane: 0,
            category: 'main',
            text: 'Fast-forward synced production trunk origin/main',
            source: 'git pull --ff-only',
            cmd: 'git pull --ff-only origin main',
            bold: false
          }
        ],
        pills: [
          { id: 'main', label: 'main', state: 'done', detail: 'v2.4.0' },
          { id: 'dev', label: 'develop', state: 'done', detail: 'in-sync' },
          { id: 'feat', label: 'feature/*', state: 'done', detail: 'pruned' },
          { id: 'hotfix', label: 'hotfix/*', state: 'done', detail: 'merged' }
        ],
        footerText: 'Branch network converged into main · 0 unmerged commits',
        footerDone: true,
        ctaMode: 'copy'
      }
    ]
  },

  // 3. Level 5 & 16: GitHub Pull Request, Reviews, CI Checks & Merge Queue
  level5_pr: {
    id: 'level5_pr',
    badge: 'Levels 5 & 16',
    label: 'Pull Request Lifecycle & Merge Queue',
    entityTitle: 'PR #42 · Feature Review to Auto-Merge',
    domain: 'github.com/org/repo/pull/42',
    searchQuery: 'gh pr merge 42 --auto --squash --delete-branch',
    workspaceChip: 'Level 5 GitHub PRs',
    placeholder: 'Try: gh pr create, gh pr checks 42 --watch, gh pr review 42 --approve...',
    defaultShowForks: true,
    lanesConfig: DEFAULT_GIT_LANES,
    steps: [
      {
        timeLabel: 'Step 1: Push & Open Draft PR',
        duration: 1400,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'Squash-merge PR #42 & auto-close Issue #19',
        goalRight: 'PR #42',
        nodes: [
          {
            id: 'pr2',
            lane: 2,
            forkFromLane: 0,
            category: 'feature',
            text: 'Opened PR #42 linking "Fixes #19" with reviewers & labels',
            source: 'gh pr create',
            cmd: 'gh pr create --base main --head feature/profile --reviewer team-core --body "Fixes #19"',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'pr1',
            lane: 0,
            category: 'main',
            text: 'Pushed feature/profile with upstream tracking (-u)',
            source: 'git push -u origin',
            cmd: 'git push -u origin feature/profile',
            bold: false
          }
        ],
        pills: [
          { id: 'pr', label: 'PR #42', state: 'done', detail: 'open' },
          { id: 'ci', label: 'CI Checks', state: 'checking', detail: 'running' },
          { id: 'rev', label: 'Review', state: 'queued', detail: 'requested' },
          { id: 'queue', label: 'Merge Queue', state: 'queued', detail: 'waiting' }
        ],
        footerText: 'Triggered GitHub Actions workflow on pull_request · Step 1 of 3',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 2: Watch CI & Approve Review',
        duration: 1600,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'writing',
        goalText: 'Entering GitHub Merge Queue (--auto --squash)...',
        goalRight: 'PR #42',
        nodes: [
          {
            id: 'pr4',
            lane: 3,
            forkFromLane: 2,
            category: 'hotfix',
            text: 'Checked out PR #42 locally & submitted approving review',
            source: 'gh pr review --approve',
            cmd: 'gh pr checkout 42 && gh pr review 42 --approve',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'pr3',
            lane: 4,
            forkFromLane: 2,
            category: 'automation',
            text: 'All 6 matrix status checks & CodeQL scans passed',
            source: 'gh pr checks --watch',
            cmd: 'gh pr checks 42 --watch',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'pr2',
            lane: 2,
            forkFromLane: 0,
            category: 'feature',
            text: 'Opened PR #42 linking "Fixes #19" with reviewers & labels',
            source: 'gh pr create',
            cmd: 'gh pr create --base main --head feature/profile --reviewer team-core --body "Fixes #19"',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'pr1',
            lane: 0,
            category: 'main',
            text: 'Pushed feature/profile with upstream tracking (-u)',
            source: 'git push -u origin',
            cmd: 'git push -u origin feature/profile',
            bold: false
          }
        ],
        pills: [
          { id: 'pr', label: 'PR #42', state: 'done', detail: 'ready' },
          { id: 'ci', label: 'CI Checks', state: 'done', detail: '6 passed' },
          { id: 'rev', label: 'Review', state: 'done', detail: 'approved' },
          { id: 'queue', label: 'Merge Queue', state: 'checking', detail: 'merging' }
        ],
        footerText: 'Ruleset satisfied · executing gh pr merge 42 --auto --squash',
        footerDone: false,
        ctaMode: 'email'
      },
      {
        timeLabel: 'Step 3: Squash Merged & Branch Deleted',
        duration: 3200,
        showDomain: true,
        headerStatus: 'complete',
        goalState: 'done',
        goalText: 'PR #42 Squash-Merged · Issue #19 Auto-Closed',
        goalRight: '5 commands',
        nodes: [
          {
            id: 'pr5',
            lane: 0,
            category: 'main',
            text: 'Squash-merged PR #42 into main & deleted remote head branch',
            source: 'gh pr merge --squash',
            cmd: 'gh pr merge 42 --auto --squash --delete-branch',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'pr4',
            lane: 3,
            forkFromLane: 2,
            category: 'hotfix',
            text: 'Checked out PR #42 locally & submitted approving review',
            source: 'gh pr review --approve',
            cmd: 'gh pr checkout 42 && gh pr review 42 --approve',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'pr3',
            lane: 4,
            forkFromLane: 2,
            category: 'automation',
            text: 'All 6 matrix status checks & CodeQL scans passed',
            source: 'gh pr checks --watch',
            cmd: 'gh pr checks 42 --watch',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'pr2',
            lane: 2,
            forkFromLane: 0,
            category: 'feature',
            text: 'Opened PR #42 linking "Fixes #19" with reviewers & labels',
            source: 'gh pr create',
            cmd: 'gh pr create --base main --head feature/profile --reviewer team-core --body "Fixes #19"',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'pr1',
            lane: 0,
            category: 'main',
            text: 'Pushed feature/profile with upstream tracking (-u)',
            source: 'git push -u origin',
            cmd: 'git push -u origin feature/profile',
            bold: false
          }
        ],
        pills: [
          { id: 'pr', label: 'PR #42', state: 'done', detail: 'merged' },
          { id: 'ci', label: 'CI Checks', state: 'done', detail: '6 passed' },
          { id: 'rev', label: 'Review', state: 'done', detail: 'approved' },
          { id: 'queue', label: 'Branch', state: 'done', detail: 'deleted' }
        ],
        footerText: 'PR #42 merged cleanly · remote & local feature branch cleaned up',
        footerDone: true,
        ctaMode: 'copy'
      }
    ]
  },

  // 4. Level 8-9: Interactive Rebase, Autosquash, --onto & Range-Diff
  level8_9_rebase: {
    id: 'level8_9_rebase',
    badge: 'Levels 8–9',
    label: 'Interactive Rebase, --onto & Autosquash',
    entityTitle: 'History Surgery · Rebase & Range-Diff',
    domain: 'git rebase -i --autosquash --update-refs',
    searchQuery: 'git rebase --onto main old-base feature/login',
    workspaceChip: 'Level 8–9 Integration',
    placeholder: 'Try: git commit --fixup HEAD~1, git rebase -i --autosquash...',
    defaultShowForks: true,
    lanesConfig: DEFAULT_GIT_LANES,
    steps: [
      {
        timeLabel: 'Step 1: Fixup & Rerere Recording',
        duration: 1500,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'Transplant & autosquash feature branch onto main',
        goalRight: 'Level 8–9',
        nodes: [
          {
            id: 'rb2',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Created targeted fixup! commit for earlier auth validation patch',
            source: 'git commit --fixup',
            cmd: 'git commit --fixup=abc1234',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rb1',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Enabled git rerere (reuse recorded conflict resolution)',
            source: 'rerere.enabled=true',
            cmd: 'git config --global rerere.enabled true',
            bold: false
          }
        ],
        pills: [
          { id: 'fixup', label: 'fixup!', state: 'done', detail: 'prepared' },
          { id: 'autosquash', label: 'Autosquash', state: 'checking', detail: 'rebasing' },
          { id: 'onto', label: '--onto', state: 'queued', detail: 'queued' },
          { id: 'lease', label: 'Force-Lease', state: 'queued', detail: 'queued' }
        ],
        footerText: 'Preparing interactive rebase with --autosquash · Step 1 of 3',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 2: Rebase --onto & Update-Refs',
        duration: 1650,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'writing',
        goalText: 'Verifying patch equivalence via git range-diff...',
        goalRight: 'Level 9',
        nodes: [
          {
            id: 'rb4',
            lane: 3,
            forkFromLane: 2,
            category: 'hotfix',
            text: 'Transplanted feature commits from deprecated base onto main',
            source: 'git rebase --onto',
            cmd: 'git rebase --onto main old-base feature/login',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rb3',
            lane: 2,
            category: 'feature',
            text: 'Autosquashed fixup commits & updated stacked branch refs',
            source: 'rebase -i --autosquash',
            cmd: 'git rebase -i --autosquash --update-refs origin/main',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rb2',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Created targeted fixup! commit for earlier auth validation patch',
            source: 'git commit --fixup',
            cmd: 'git commit --fixup=abc1234',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rb1',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Enabled git rerere (reuse recorded conflict resolution)',
            source: 'rerere.enabled=true',
            cmd: 'git config --global rerere.enabled true',
            bold: false
          }
        ],
        pills: [
          { id: 'fixup', label: 'fixup!', state: 'done', detail: 'squashed' },
          { id: 'autosquash', label: 'update-refs', state: 'done', detail: 'updated' },
          { id: 'onto', label: 'range-diff', state: 'checking', detail: 'comparing' },
          { id: 'lease', label: 'Force-Lease', state: 'checking', detail: 'ready' }
        ],
        footerText: 'Auditing rewritten patch series with git range-diff · Step 2 of 3',
        footerDone: false,
        ctaMode: 'email'
      },
      {
        timeLabel: 'Step 3: Range-Diff Verified & Force-With-Lease',
        duration: 3200,
        showDomain: true,
        headerStatus: 'complete',
        goalState: 'done',
        goalText: 'Linear History Published (--force-with-lease)',
        goalRight: '6 commands',
        nodes: [
          {
            id: 'rb6',
            lane: 0,
            category: 'main',
            text: 'Safely updated remote branch after verifying no upstream race',
            source: '--force-with-lease',
            cmd: 'git push --force-with-lease origin feature/login',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rb5',
            lane: 4,
            forkFromLane: 3,
            category: 'automation',
            text: 'Compared pre-rebase & post-rebase patch series equivalence',
            source: 'git range-diff',
            cmd: 'git range-diff main...feature/login@{1} main...feature/login',
            bold: false
          },
          {
            id: 'rb4',
            lane: 3,
            forkFromLane: 2,
            category: 'hotfix',
            text: 'Transplanted feature commits from deprecated base onto main',
            source: 'git rebase --onto',
            cmd: 'git rebase --onto main old-base feature/login',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rb3',
            lane: 2,
            category: 'feature',
            text: 'Autosquashed fixup commits & updated stacked branch refs',
            source: 'rebase -i --autosquash',
            cmd: 'git rebase -i --autosquash --update-refs origin/main',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rb2',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Created targeted fixup! commit for earlier auth validation patch',
            source: 'git commit --fixup',
            cmd: 'git commit --fixup=abc1234',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rb1',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Enabled git rerere (reuse recorded conflict resolution)',
            source: 'rerere.enabled=true',
            cmd: 'git config --global rerere.enabled true',
            bold: false
          }
        ],
        pills: [
          { id: 'fixup', label: 'fixup!', state: 'done', detail: 'squashed' },
          { id: 'autosquash', label: 'update-refs', state: 'done', detail: 'clean' },
          { id: 'onto', label: 'range-diff', state: 'done', detail: 'verified' },
          { id: 'lease', label: 'Force-Lease', state: 'done', detail: 'pushed' }
        ],
        footerText: 'Rebased branch published safely · 0 collaborator commits overwritten',
        footerDone: true,
        ctaMode: 'copy'
      }
    ]
  },

  // 5. Level 10: Undo & Disaster Recovery (Reflog Time-Travel)
  level10_recovery: {
    id: 'level10_recovery',
    badge: 'Level 10',
    label: 'Disaster Recovery & Reflog Time-Travel',
    entityTitle: 'Disaster Recovery · Reflog & Dangling Commits',
    domain: 'HEAD@{1} -> recovery/payment -> main',
    searchQuery: 'git reflog && git branch recovery/payment def5678',
    workspaceChip: 'Level 10 Undo & Recovery',
    placeholder: 'Try: git reflog, git reset --soft HEAD~1, git restore --staged...',
    defaultShowForks: true,
    lanesConfig: DEFAULT_GIT_LANES,
    steps: [
      {
        timeLabel: 'Step 1: Accidental Hard Reset & Stash',
        duration: 1450,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'Rescue orphaned commits after accidental reset --hard',
        goalRight: 'Level 10',
        nodes: [
          {
            id: 'rc2',
            lane: 3,
            forkFromLane: 0,
            category: 'hotfix',
            text: 'Accidental git reset --hard HEAD~3 orphaned 3 payment commits!',
            source: 'reset --hard HEAD~3',
            cmd: 'git reset --hard HEAD~3',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rc1',
            lane: 0,
            category: 'main',
            text: 'Stashed untracked working tree files before branch surgery',
            source: 'git stash push -u',
            cmd: 'git stash push -u -m "WIP checkout"',
            bold: false
          }
        ],
        pills: [
          { id: 'stash', label: 'Stash', state: 'done', detail: 'stash@{0}' },
          { id: 'reflog', label: 'Reflog Scan', state: 'checking', detail: 'searching' },
          { id: 'branch', label: 'Recovery Branch', state: 'queued', detail: 'queued' },
          { id: 'restore', label: 'Restore', state: 'queued', detail: 'queued' }
        ],
        footerText: 'Scanning .git/logs/HEAD via git reflog · Step 1 of 3',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 2: Locate HEAD@{1} in Reflog',
        duration: 1600,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'writing',
        goalText: 'Re-attaching dangling commit graph def5678...',
        goalRight: 'Level 10',
        nodes: [
          {
            id: 'rc4',
            lane: 1,
            forkFromLane: 2,
            category: 'develop',
            text: 'Anchored new branch recovery/payment at dangling SHA def5678',
            source: 'git branch recovery',
            cmd: 'git branch recovery/payment def5678',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rc3',
            lane: 2,
            forkFromLane: 3,
            category: 'feature',
            text: 'Located lost commit def5678 at HEAD@{1} in local reflog',
            source: 'git reflog',
            cmd: 'git reflog --all',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rc2',
            lane: 3,
            forkFromLane: 0,
            category: 'hotfix',
            text: 'Accidental git reset --hard HEAD~3 orphaned 3 payment commits!',
            source: 'reset --hard HEAD~3',
            cmd: 'git reset --hard HEAD~3',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rc1',
            lane: 0,
            category: 'main',
            text: 'Stashed untracked working tree files before branch surgery',
            source: 'git stash push -u',
            cmd: 'git stash push -u -m "WIP checkout"',
            bold: false
          }
        ],
        pills: [
          { id: 'stash', label: 'Stash', state: 'done', detail: 'stash@{0}' },
          { id: 'reflog', label: 'Reflog Scan', state: 'done', detail: 'def5678' },
          { id: 'branch', label: 'Recovery Branch', state: 'done', detail: 'anchored' },
          { id: 'restore', label: 'Restore', state: 'checking', detail: 'applying' }
        ],
        footerText: 'Restoring specific file snapshot & popping stash · Step 2 of 3',
        footerDone: false,
        ctaMode: 'email'
      },
      {
        timeLabel: 'Step 3: Full Recovery & Stash Pop',
        duration: 3200,
        showDomain: true,
        headerStatus: 'complete',
        goalState: 'done',
        goalText: '100% Work Recovered: Reflog + Stash Restored',
        goalRight: '0 bytes lost',
        nodes: [
          {
            id: 'rc5',
            lane: 0,
            category: 'main',
            text: 'Merged recovered branch & popped WIP stash back to worktree',
            source: 'git stash pop',
            cmd: 'git merge recovery/payment && git stash pop',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rc4',
            lane: 1,
            forkFromLane: 2,
            category: 'develop',
            text: 'Anchored new branch recovery/payment at dangling SHA def5678',
            source: 'git branch recovery',
            cmd: 'git branch recovery/payment def5678',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rc3',
            lane: 2,
            forkFromLane: 3,
            category: 'feature',
            text: 'Located lost commit def5678 at HEAD@{1} in local reflog',
            source: 'git reflog',
            cmd: 'git reflog --all',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rc2',
            lane: 3,
            forkFromLane: 0,
            category: 'hotfix',
            text: 'Accidental git reset --hard HEAD~3 orphaned 3 payment commits!',
            source: 'reset --hard HEAD~3',
            cmd: 'git reset --hard HEAD~3',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'rc1',
            lane: 0,
            category: 'main',
            text: 'Stashed untracked working tree files before branch surgery',
            source: 'git stash push -u',
            cmd: 'git stash push -u -m "WIP checkout"',
            bold: false
          }
        ],
        pills: [
          { id: 'stash', label: 'Stash', state: 'done', detail: 'popped' },
          { id: 'reflog', label: 'Reflog Scan', state: 'done', detail: 'def5678' },
          { id: 'branch', label: 'Recovery Branch', state: 'done', detail: 'merged' },
          { id: 'restore', label: 'Worktree', state: 'done', detail: 'clean' }
        ],
        footerText: 'All 3 orphaned commits & untracked files recovered cleanly',
        footerDone: true,
        ctaMode: 'copy'
      }
    ]
  },

  // 6. Level 13 & Plumbing: Bisect Binary Search, Worktrees & Git Object Model
  level13_internals: {
    id: 'level13_internals',
    badge: 'Level 13 & Plumbing',
    label: 'Worktrees, Automated Bisect & Plumbing',
    entityTitle: 'Git Internals · Worktree + Bisect + Objects',
    domain: '.git/objects (blob -> tree -> commit)',
    searchQuery: 'git bisect run npm test && git worktree add',
    workspaceChip: 'Level 13 Expert Git',
    placeholder: 'Try: git bisect start, git worktree add, git cat-file -p HEAD...',
    defaultShowForks: true,
    lanesConfig: DEFAULT_GIT_LANES,
    steps: [
      {
        timeLabel: 'Step 1: Parallel Worktree & Sparse-Checkout',
        duration: 1450,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'Pinpoint regression across 512 commits in parallel worktree',
        goalRight: 'Level 13',
        nodes: [
          {
            id: 'in2',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Enabled cone-mode sparse-checkout for monorepo services/auth',
            source: 'git sparse-checkout',
            cmd: 'git sparse-checkout init --cone && git sparse-checkout set services/auth',
            bold: false
          },
          {
            id: 'in1',
            lane: 0,
            category: 'main',
            text: 'Mounted parallel worktree ../project-hotfix without switching HEAD',
            source: 'git worktree add',
            cmd: 'git worktree add ../project-hotfix hotfix/payment-crash',
            bold: true,
            highlightedOnComplete: true
          }
        ],
        pills: [
          { id: 'wt', label: 'Worktrees', state: 'done', detail: '2 active' },
          { id: 'bisect', label: 'git bisect', state: 'checking', detail: 'O(log n)' },
          { id: 'plumb', label: 'cat-file -p', state: 'queued', detail: 'queued' },
          { id: 'maint', label: 'commit-graph', state: 'queued', detail: 'queued' }
        ],
        footerText: 'Launching automated binary search via git bisect run · Step 1 of 3',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 2: Automated Bisect & Object Inspection',
        duration: 1650,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'writing',
        goalText: 'Inspecting culprit commit tree via git cat-file -p...',
        goalRight: '9 steps -> 512 revs',
        nodes: [
          {
            id: 'in4',
            lane: 3,
            forkFromLane: 2,
            category: 'hotfix',
            text: 'Inspected raw commit -> tree -> blob objects in .git/objects',
            source: 'git cat-file -p',
            cmd: 'git cat-file -p c4f91a2',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'in3',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Binary search isolated first bad commit c4f91a2 in 9 test runs',
            source: 'git bisect run',
            cmd: 'git bisect start HEAD v1.0.0 && git bisect run npm test',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'in2',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Enabled cone-mode sparse-checkout for monorepo services/auth',
            source: 'git sparse-checkout',
            cmd: 'git sparse-checkout init --cone && git sparse-checkout set services/auth',
            bold: false
          },
          {
            id: 'in1',
            lane: 0,
            category: 'main',
            text: 'Mounted parallel worktree ../project-hotfix without switching HEAD',
            source: 'git worktree add',
            cmd: 'git worktree add ../project-hotfix hotfix/payment-crash',
            bold: true,
            highlightedOnComplete: true
          }
        ],
        pills: [
          { id: 'wt', label: 'Worktrees', state: 'done', detail: '2 active' },
          { id: 'bisect', label: 'git bisect', state: 'done', detail: 'c4f91a2' },
          { id: 'plumb', label: 'cat-file -p', state: 'done', detail: 'verified' },
          { id: 'maint', label: 'commit-graph', state: 'checking', detail: 'writing' }
        ],
        footerText: 'Reverting culprit c4f91a2 & optimizing packfile index · Step 2 of 3',
        footerDone: false,
        ctaMode: 'email'
      },
      {
        timeLabel: 'Step 3: Culprit Reverted & Graph Optimized',
        duration: 3200,
        showDomain: true,
        headerStatus: 'complete',
        goalState: 'done',
        goalText: 'Regression c4f91a2 Reverted · Commit-Graph Optimized',
        goalRight: '512 commits searched',
        nodes: [
          {
            id: 'in5',
            lane: 0,
            category: 'main',
            text: 'Reset bisect, reverted c4f91a2 & wrote multi-pack commit-graph',
            source: 'git maintenance run',
            cmd: 'git bisect reset && git revert c4f91a2 && git commit-graph write --reachable',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'in4',
            lane: 3,
            forkFromLane: 2,
            category: 'hotfix',
            text: 'Inspected raw commit -> tree -> blob objects in .git/objects',
            source: 'git cat-file -p',
            cmd: 'git cat-file -p c4f91a2',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'in3',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Binary search isolated first bad commit c4f91a2 in 9 test runs',
            source: 'git bisect run',
            cmd: 'git bisect start HEAD v1.0.0 && git bisect run npm test',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'in2',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Enabled cone-mode sparse-checkout for monorepo services/auth',
            source: 'git sparse-checkout',
            cmd: 'git sparse-checkout init --cone && git sparse-checkout set services/auth',
            bold: false
          },
          {
            id: 'in1',
            lane: 0,
            category: 'main',
            text: 'Mounted parallel worktree ../project-hotfix without switching HEAD',
            source: 'git worktree add',
            cmd: 'git worktree add ../project-hotfix hotfix/payment-crash',
            bold: true,
            highlightedOnComplete: true
          }
        ],
        pills: [
          { id: 'wt', label: 'Worktrees', state: 'done', detail: 'pruned' },
          { id: 'bisect', label: 'git bisect', state: 'done', detail: 'c4f91a2' },
          { id: 'plumb', label: 'cat-file -p', state: 'done', detail: 'inspected' },
          { id: 'maint', label: 'commit-graph', state: 'done', detail: 'optimized' }
        ],
        footerText: 'Regression resolved in 9 binary-search steps · fsck integrity 100%',
        footerDone: true,
        ctaMode: 'copy'
      }
    ]
  },

  // 7. Level 17-19: Security, Secret Purge, SSH Signing, Rulesets & GraphQL API
  level17_19_security: {
    id: 'level17_19_security',
    badge: 'Levels 17–19',
    label: 'Security, Secret Purge, Signing & GraphQL API',
    entityTitle: 'DevSecOps · Secret Purge & Ruleset Governance',
    domain: 'gh ruleset + git filter-repo + gh attestation',
    searchQuery: 'git filter-repo --path .env --invert-paths',
    workspaceChip: 'Level 17–19 Security & Admin',
    placeholder: 'Try: gh ssh-key add, git commit -S, gh api graphql, gh secret set...',
    defaultShowForks: true,
    lanesConfig: DEFAULT_GIT_LANES,
    steps: [
      {
        timeLabel: 'Step 1: SSH Ed25519 Signing & Secret Purge',
        duration: 1500,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'Purge leaked .env from history & enforce signed rulesets',
        goalRight: 'Level 17–19',
        nodes: [
          {
            id: 'sc2',
            lane: 3,
            forkFromLane: 0,
            category: 'hotfix',
            text: 'Purged leaked .env across all historical commits via filter-repo',
            source: 'git filter-repo',
            cmd: 'git filter-repo --path .env --invert-paths',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'sc1',
            lane: 0,
            category: 'main',
            text: 'Generated Ed25519 SSH key & enabled commit.gpgsign=true',
            source: 'ssh-keygen -t ed25519',
            cmd: 'ssh-keygen -t ed25519 -C "sec@org.com" && gh ssh-key add ~/.ssh/id_ed25519.pub',
            bold: false
          }
        ],
        pills: [
          { id: 'ssh', label: 'SSH Signing', state: 'done', detail: 'Ed25519' },
          { id: 'purge', label: 'filter-repo', state: 'done', detail: '.env purged' },
          { id: 'attest', label: 'SLSA Attest', state: 'checking', detail: 'verifying' },
          { id: 'api', label: 'GraphQL API', state: 'queued', detail: 'queued' }
        ],
        footerText: 'Rotating secrets via gh secret set & verifying SLSA provenance',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 2: SLSA Attestation, Rulesets & GraphQL',
        duration: 3200,
        showDomain: true,
        headerStatus: 'complete',
        goalState: 'done',
        goalText: 'Supply-Chain Hardened: Signed, Purged & Ruleset Active',
        goalRight: 'SLSA L3 Verified',
        nodes: [
          {
            id: 'sc5',
            lane: 4,
            forkFromLane: 2,
            category: 'automation',
            text: 'Audited branch protection rulesets & vulnerabilities via GraphQL',
            source: 'gh api graphql',
            cmd: 'gh api graphql --paginate -f query="query { viewer { login } }"',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'sc4',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Verified artifact SLSA provenance attestation & pushed release tag -s',
            source: 'gh attestation verify',
            cmd: 'gh attestation verify dist/app.tar.gz --owner org',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'sc3',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Encrypted production rotation keys into GitHub Actions secrets',
            source: 'gh secret set',
            cmd: 'gh secret set PROD_API_KEY --env production',
            bold: false
          },
          {
            id: 'sc2',
            lane: 3,
            forkFromLane: 0,
            category: 'hotfix',
            text: 'Purged leaked .env across all historical commits via filter-repo',
            source: 'git filter-repo',
            cmd: 'git filter-repo --path .env --invert-paths',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'sc1',
            lane: 0,
            category: 'main',
            text: 'Generated Ed25519 SSH key & enabled commit.gpgsign=true',
            source: 'ssh-keygen -t ed25519',
            cmd: 'ssh-keygen -t ed25519 -C "sec@org.com" && gh ssh-key add ~/.ssh/id_ed25519.pub',
            bold: false
          }
        ],
        pills: [
          { id: 'ssh', label: 'SSH Signing', state: 'done', detail: 'Verified' },
          { id: 'purge', label: 'filter-repo', state: 'done', detail: '0 leaks' },
          { id: 'attest', label: 'SLSA Attest', state: 'done', detail: 'passed' },
          { id: 'api', label: 'Rulesets', state: 'done', detail: 'enforced' }
        ],
        footerText: 'Repository hardened · signed commits & merge queue required',
        footerDone: true,
        ctaMode: 'copy'
      }
    ]
  },

  // 8. Bonus God-Level: In-Memory Merge-Tree, Stacked PRs & AI Agent Worktrees
  god_level_ai: {
    id: 'god_level_ai',
    badge: 'Bonus God-Level',
    label: 'In-Memory Merge-Tree, Stacked PRs & AI Agents',
    entityTitle: 'God-Level Git · Zero-Worktree Merge & AI Swarm',
    domain: 'git merge-tree --write-tree + git absorb + worktrees',
    searchQuery: 'git merge-tree --write-tree main feature/ai-agent',
    workspaceChip: 'God-Level & AI Workflows',
    placeholder: 'Try: git merge-tree --write-tree, git absorb, gh copilot suggest...',
    defaultShowForks: true,
    lanesConfig: DEFAULT_GIT_LANES,
    steps: [
      {
        timeLabel: 'Step 1: Spawn 4 Parallel AI Agent Worktrees',
        duration: 1500,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'pending',
        goalText: 'In-memory merge 5 parallel AI agent branches',
        goalRight: '5 lanes',
        nodes: [
          {
            id: 'gd3',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Auto-absorbed uncommitted review fixes into stacked parent commits',
            source: 'git absorb --and-rebase',
            cmd: 'git absorb --and-rebase',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'gd2',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Spawned isolated agent worktrees with blobless partial clone cache',
            source: '--filter=blob:none',
            cmd: 'git clone --filter=blob:none git@github.com:org/monorepo.git',
            bold: false
          },
          {
            id: 'gd1',
            lane: 0,
            category: 'main',
            text: 'Enabled commit-graph bloom filters & fsmonitor daemon',
            source: 'core.fsmonitor=true',
            cmd: 'git config core.fsmonitor true && git maintenance start',
            bold: false
          }
        ],
        pills: [
          { id: 'clone', label: 'Blobless Clone', state: 'done', detail: 'active' },
          { id: 'absorb', label: 'git absorb', state: 'done', detail: 'stacked' },
          { id: 'mtree', label: 'merge-tree', state: 'checking', detail: 'in-memory' },
          { id: 'notes', label: 'git notes', state: 'queued', detail: 'queued' }
        ],
        footerText: 'Computing conflict-free tree SHA in-memory via git merge-tree · Step 1 of 2',
        footerDone: false,
        ctaMode: 'none'
      },
      {
        timeLabel: 'Step 2: Zero-Checkout Merge-Tree & Commit-Tree',
        duration: 3400,
        showDomain: true,
        headerStatus: 'complete',
        goalState: 'done',
        goalText: 'Zero-Checkout Merge Complete (tree 8f92e1a)',
        goalRight: '5 lanes · 18ms',
        nodes: [
          {
            id: 'gd6',
            lane: 0,
            category: 'main',
            text: 'Atomically advanced refs/heads/main via commit-tree & update-ref',
            source: 'git update-ref',
            cmd: 'git update-ref refs/heads/main $(git commit-tree 8f92e1a -p main -p feature/ai -m "Merge")',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'gd5',
            lane: 4,
            forkFromLane: 3,
            category: 'automation',
            text: 'Attached AI agent benchmark telemetry metadata via git notes',
            source: 'git notes add',
            cmd: 'git notes --ref=ai-telemetry add -m "latency: 18ms" HEAD',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'gd4',
            lane: 3,
            forkFromLane: 2,
            category: 'hotfix',
            text: 'Computed 3-way merge tree in-memory without touching working tree',
            source: 'merge-tree --write-tree',
            cmd: 'git merge-tree --write-tree main feature/ai-agent',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'gd3',
            lane: 2,
            forkFromLane: 1,
            category: 'feature',
            text: 'Auto-absorbed uncommitted review fixes into stacked parent commits',
            source: 'git absorb --and-rebase',
            cmd: 'git absorb --and-rebase',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'gd2',
            lane: 1,
            forkFromLane: 0,
            category: 'develop',
            text: 'Spawned isolated agent worktrees with blobless partial clone cache',
            source: '--filter=blob:none',
            cmd: 'git clone --filter=blob:none git@github.com:org/monorepo.git',
            bold: false
          },
          {
            id: 'gd1',
            lane: 0,
            category: 'main',
            text: 'Enabled commit-graph bloom filters & fsmonitor daemon',
            source: 'core.fsmonitor=true',
            cmd: 'git config core.fsmonitor true && git maintenance start',
            bold: false
          }
        ],
        pills: [
          { id: 'clone', label: 'Blobless Clone', state: 'done', detail: '94% faster' },
          { id: 'absorb', label: 'git absorb', state: 'done', detail: 'rebased' },
          { id: 'mtree', label: 'merge-tree', state: 'done', detail: '8f92e1a' },
          { id: 'notes', label: 'git notes', state: 'done', detail: 'attached' }
        ],
        footerText: 'In-memory merge completed in 18ms without dirtying working directory',
        footerDone: true,
        ctaMode: 'copy'
      }
    ]
  },

  // 9. Original Kestrel Freight 3-Lane Video Replica (Preserved 100%)
  kestrel: {
    id: 'kestrel',
    badge: 'Original Video',
    label: 'Kestrel Freight (Exact 3-Lane Video Replica)',
    entityTitle: 'Kestrel Freight',
    domain: 'kestrelfreight.com',
    searchQuery: 'Kestrel Freight',
    workspaceChip: 'Northpeak CRM',
    placeholder: 'Ask anything, or type / for skills',
    defaultShowForks: false,
    lanesConfig: DEFAULT_GIT_LANES,
    steps: [
      {
        timeLabel: '00:16 (Screenshot 1)',
        duration: 1800,
        showDomain: true,
        headerStatus: 'researching',
        goalState: 'writing',
        goalText: 'Writing the brief...',
        goalRight: null,
        nodes: [
          {
            id: 'k10',
            lane: 0,
            category: 'company',
            text: 'Shippers praise quote speed, carriers want faster pay',
            source: 'g2.com',
            bold: false
          },
          {
            id: 'k9',
            lane: 0,
            category: 'company',
            text: 'Runs Salesforce, Gong and Snowflake',
            source: 'builtwith.com',
            bold: false
          },
          {
            id: 'k8',
            lane: 2,
            category: 'people',
            text: '14 open operations roles, 9 posted this month',
            source: 'greenhouse.io',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'k7',
            lane: 2,
            category: 'people',
            text: 'Priya Raman runs their Salesforce rollout',
            source: 'linkedin.com',
            bold: false
          },
          {
            id: 'k6',
            lane: 2,
            forkFromLane: 1,
            category: 'people',
            text: 'Dana Whitfield joined as VP Operations',
            source: 'linkedin.com',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'k5',
            lane: 1,
            category: 'news',
            text: 'Opening an Atlanta office to cover the Southeast',
            source: 'supplychaindive.com',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'k4',
            lane: 1,
            forkFromLane: 0,
            category: 'news',
            text: 'Raised a $38M Series B led by Forge Ventures',
            source: 'freightwaves.com ^',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'k3',
            lane: 0,
            category: 'company',
            text: 'Ships for Haverford Foods and Ostrander Steel',
            source: 'kestrelfreight.com',
            bold: false
          },
          {
            id: 'k2',
            lane: 0,
            category: 'company',
            text: 'Founded 2014 in Columbus, Ohio · 420 people',
            source: 'linkedin.com',
            bold: false
          },
          {
            id: 'k1',
            lane: 0,
            category: 'company',
            text: 'Freight brokerage for mid-size manufacturers',
            source: 'kestrelfreight.com',
            bold: false
          }
        ],
        pills: [
          { id: 'company', label: 'Company', state: 'done', detail: '6 pages' },
          { id: 'funding', label: 'Funding', state: 'done', detail: '$52M' },
          { id: 'news', label: 'News', state: 'done', detail: '3 stories' },
          { id: 'people', label: 'People', state: 'done', detail: '3 people' }
        ],
        footerText: 'Writing the brief · 11 of 11 sources',
        footerDone: false,
        ctaMode: 'email'
      },
      {
        timeLabel: '00:21 (Screenshot 2)',
        duration: 3800,
        showDomain: true,
        headerStatus: 'complete',
        goalState: 'done',
        goalText: 'Brief: 4 reasons to call now',
        goalRight: '11 sources',
        nodes: [
          {
            id: 'k10',
            lane: 0,
            category: 'company',
            text: 'Shippers praise quote speed, carriers want faster pay',
            source: 'g2.com',
            bold: false
          },
          {
            id: 'k9',
            lane: 0,
            category: 'company',
            text: 'Runs Salesforce, Gong and Snowflake',
            source: 'builtwith.com',
            bold: false
          },
          {
            id: 'k8',
            lane: 2,
            category: 'people',
            text: '14 open operations roles, 9 posted this month',
            source: 'greenhouse.io',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'k7',
            lane: 2,
            category: 'people',
            text: 'Priya Raman runs their Salesforce rollout',
            source: 'linkedin.com',
            bold: false
          },
          {
            id: 'k6',
            lane: 2,
            forkFromLane: 1,
            category: 'people',
            text: 'Dana Whitfield joined as VP Operations',
            source: 'linkedin.com',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'k5',
            lane: 1,
            category: 'news',
            text: 'Opening an Atlanta office to cover the Southeast',
            source: 'supplychaindive.com',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'k4',
            lane: 1,
            forkFromLane: 0,
            category: 'news',
            text: 'Raised a $38M Series B led by Forge Ventures',
            source: 'freightwaves.com ^',
            bold: true,
            highlightedOnComplete: true
          },
          {
            id: 'k3',
            lane: 0,
            category: 'company',
            text: 'Ships for Haverford Foods and Ostrander Steel',
            source: 'kestrelfreight.com',
            bold: false
          },
          {
            id: 'k2',
            lane: 0,
            category: 'company',
            text: 'Founded 2014 in Columbus, Ohio · 420 people',
            source: 'linkedin.com',
            bold: false
          },
          {
            id: 'k1',
            lane: 0,
            category: 'company',
            text: 'Freight brokerage for mid-size manufacturers',
            source: 'kestrelfreight.com',
            bold: false
          }
        ],
        pills: [
          { id: 'company', label: 'Company', state: 'done', detail: '6 pages' },
          { id: 'funding', label: 'Funding', state: 'done', detail: '$52M' },
          { id: 'news', label: 'News', state: 'done', detail: '3 stories' },
          { id: 'people', label: 'People', state: 'done', detail: '3 people' }
        ],
        footerText: 'Brief ready · 11 sources in 21s',
        footerDone: true,
        ctaMode: 'copy'
      }
    ]
  }
};

// ============================================================================
// 6. COMPREHENSIVE GIT & GITHUB COMMAND ENCYCLOPEDIA DATABASE
//    Covers Levels 0 to 24 from the uploaded markdown file + Gap-Audit + God-Level
// ============================================================================
const ENCYCLOPEDIA_LEVELS = [
  {
    id: 'all',
    shortLabel: 'All Levels (0–24)',
    title: 'Complete Git & GitHub Command Encyclopedia'
  },
  {
    id: 'lvl0_1',
    shortLabel: 'L0–L1: Setup & Staging',
    title: 'Level 0–1: Install, Auth, Config, Working Tree & Interactive Staging'
  },
  {
    id: 'lvl2_4',
    shortLabel: 'L2–L4: Repos & Branch Networks',
    title: 'Level 2–4: Repositories, Remotes, Clones & Multi-Lane Branch Networks'
  },
  {
    id: 'lvl5_6',
    shortLabel: 'L5–L6: PRs, Issues & Projects',
    title: 'Level 5–6: Pull Requests, Code Reviews, Merge Queues, Issues & Projects'
  },
  {
    id: 'lvl7_9',
    shortLabel: 'L7–L9: Logs, Merge & Rebase',
    title: 'Level 7–9: Commit Archaeology, Conflicts, Rebase --onto & Cherry-Pick'
  },
  {
    id: 'lvl10_12',
    shortLabel: 'L10–L12: Recovery, Sync & Releases',
    title: 'Level 10–12: Undo, Reflog Recovery, Force-With-Lease, Tags & Releases'
  },
  {
    id: 'lvl13_14',
    shortLabel: 'L13–L14: Internals, Bisect & Worktrees',
    title: 'Level 13–14: Bisect, Worktrees, Sparse-Checkout, Submodules & Plumbing'
  },
  {
    id: 'lvl15_19',
    shortLabel: 'L15–L19: Actions, Security & API',
    title: 'Level 15–19: GitHub CLI, Actions CI/CD, SSH Signing, Secret Purge & API'
  },
  {
    id: 'lvl20_24',
    shortLabel: 'L20–L24 + God-Level',
    title: 'Level 20–24 + Bonus: Decision Matrix, Troubleshooting & AI Agent Flows'
  }
];

// Zones: 'worktree' | 'index' | 'local' | 'remote'
// Danger: 'safe' | 'caution' | 'destructive'
const COMMAND_DATABASE = [
  // ================= LEVEL 0 & 1: INSTALL, AUTH, CONFIG & STAGING =================
  {
    id: 'cmd-git-version-help',
    levelId: 'lvl0_1',
    levelBadge: 'Level 0.1',
    tool: 'git',
    cmd: 'git help -a',
    syntax: 'git --version | git help -a | git help -g | git <cmd> -h',
    summary: 'Discover every installed Git porcelain, plumbing command, and official tutorial guide locally.',
    zones: ['local'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Enumerated all local Git porcelain & plumbing commands (git help -a)',
    example: 'git --version\ngit help -a\ngit help everyday\ngit rebase -h',
    proTip: 'Use `git help -g` to read built-in concept guides like `everyday`, `revisions`, and `workflows` offline.'
  },
  {
    id: 'cmd-gh-auth-login',
    levelId: 'lvl0_1',
    levelBadge: 'Level 0.4',
    tool: 'gh',
    cmd: 'gh auth login',
    syntax: 'gh auth login | gh auth status | gh auth refresh | gh auth logout',
    summary: 'Authenticate GitHub CLI with GitHub.com or GitHub Enterprise via OAuth browser flow or fine-grained PAT.',
    zones: ['local', 'remote'],
    danger: 'safe',
    lane: 4,
    category: 'automation',
    graphActionText: 'Authenticated GitHub CLI session & verified token scopes (gh auth status)',
    example: 'gh auth login\ngh auth status\ngh auth refresh -s workflow,read:org',
    proTip: 'Run `gh auth status` to verify which account and token scopes (`repo`, `workflow`, `read:org`) are currently active.'
  },
  {
    id: 'cmd-git-config-origin',
    levelId: 'lvl0_1',
    levelBadge: 'Level 1.1',
    tool: 'git',
    cmd: 'git config --show-origin --list',
    syntax: 'git config [--global|--local|--worktree] user.name "Name"',
    summary: 'Configure identity & settings across system, global, local, or worktree scopes and inspect exact file origins.',
    zones: ['local'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Audited config hierarchy (--system, --global, --local) via --show-origin',
    example: 'git config --global user.name "Ada Lovelace"\ngit config --global user.email "ada@analytical.engine"\ngit config --show-origin --list',
    proTip: 'When a repo behaves unexpectedly, `--show-origin` pinpoints which config file (`~/.gitconfig` vs `.git/config`) set the rule.'
  },
  {
    id: 'cmd-git-init-main',
    levelId: 'lvl0_1',
    levelBadge: 'Level 1.2',
    tool: 'git',
    cmd: 'git init -b main',
    syntax: 'git init [-b <branch>] | git init --bare',
    summary: 'Initialize a new local Git repository and `.git/` object database with `main` as the initial HEAD branch.',
    zones: ['worktree', 'local'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Initialized .git object database on root branch main (git init -b main)',
    example: 'mkdir my-project && cd my-project\ngit init -b main\ngit rev-parse --show-toplevel',
    proTip: 'Use `git init --bare` on servers where no working tree checkout should exist.'
  },
  {
    id: 'cmd-git-status-porcelain',
    levelId: 'lvl0_1',
    levelBadge: 'Level 1.4',
    tool: 'git',
    cmd: 'git status --short --branch',
    syntax: 'git status [-sb | --porcelain=v2 | --ignored]',
    summary: 'Inspect working tree vs staging index in compact 2-column format (`XY`: Column 1 = Index, Column 2 = Worktree).',
    zones: ['worktree', 'index'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Scanned 2-column staging & worktree state (git status -sb)',
    example: 'git status --short --branch\ngit status --porcelain\ngit status --ignored',
    proTip: 'In `git status -s`, `M ` (left column) means staged in index; ` M` (right column) means modified in working tree but unstaged.'
  },
  {
    id: 'cmd-git-add-patch',
    levelId: 'lvl0_1',
    levelBadge: 'Level 1.5',
    tool: 'git',
    cmd: 'git add -p',
    syntax: 'git add -p [<file>] | git add -A | git add -u',
    summary: 'Interactively review and stage individual diff hunks (or split hunks with `s`) into the staging area.',
    zones: ['worktree', 'index'],
    danger: 'safe',
    lane: 1,
    category: 'develop',
    graphActionText: 'Interactively selected & staged clean code hunks into index (git add -p)',
    example: 'git add -p src/app.js\n# y = stage hunk, n = skip, s = split, e = manual edit',
    proTip: '`git add -p` prevents accidental debugging `console.log` lines from sneaking into commits.'
  },
  {
    id: 'cmd-git-diff-staged',
    levelId: 'lvl0_1',
    levelBadge: 'Level 1.6',
    tool: 'git',
    cmd: 'git diff --staged',
    syntax: 'git diff [--staged | --stat | --name-only | -w | main...feature]',
    summary: 'Compare the staging index against `HEAD` to review the exact snapshot that your next commit will record.',
    zones: ['index', 'local'],
    danger: 'safe',
    lane: 1,
    category: 'develop',
    graphActionText: 'Compared staged index tree against HEAD commit (git diff --staged)',
    example: 'git diff\ngit diff --staged\ngit diff --stat main...feature/login\ngit diff --check',
    proTip: 'Use `git diff --check` before committing to catch trailing whitespace or leftover conflict markers.'
  },
  {
    id: 'cmd-git-commit-fixup',
    levelId: 'lvl0_1',
    levelBadge: 'Level 1.7',
    tool: 'git',
    cmd: 'git commit --fixup HEAD~1',
    syntax: 'git commit -m "<msg>" | --amend --no-edit | --fixup=<commit>',
    summary: 'Create a commit or target an earlier commit with `fixup!` so `git rebase -i --autosquash` folds it automatically.',
    zones: ['index', 'local'],
    danger: 'caution',
    lane: 1,
    category: 'develop',
    graphActionText: 'Recorded targeted fixup! commit snapshot in local DAG (git commit --fixup)',
    example: 'git commit -m "Add login page"\ngit commit --amend --no-edit\ngit commit --fixup=abc1234',
    proTip: 'Never `--amend` commits already pushed to a shared team branch; use `--fixup` on feature branches before PR merge.'
  },

  // ================= LEVEL 2 TO 4: REPOS, REMOTES & BRANCH NETWORKS =================
  {
    id: 'cmd-gh-repo-create-push',
    levelId: 'lvl2_4',
    levelBadge: 'Level 2.2',
    tool: 'gh',
    cmd: 'gh repo create --public --source=. --remote=origin --push',
    syntax: 'gh repo create [<name>] [--public|--private] [--source=.] [--push]',
    summary: 'Create a new GitHub repository, configure `origin` remote, and push your local branch in a single command.',
    zones: ['local', 'remote'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Created GitHub repo, linked origin & pushed main (gh repo create --push)',
    example: 'gh repo create my-project --public --source=. --remote=origin --push\ngh repo view --web',
    proTip: 'Add `--clone` when creating an empty remote repository from scratch without a local directory.'
  },
  {
    id: 'cmd-git-clone-filter',
    levelId: 'lvl2_4',
    levelBadge: 'Level 2.4',
    tool: 'git',
    cmd: 'git clone --filter=blob:none <url>',
    syntax: 'git clone [--depth 1 | --filter=blob:none | --branch <br>] <url>',
    summary: 'Perform a fast blobless partial clone that downloads full commit/tree history immediately and fetches file blobs on demand.',
    zones: ['remote', 'local', 'worktree'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Cloned repository with on-demand blobless filter (--filter=blob:none)',
    example: 'git clone --filter=blob:none git@github.com:OWNER/REPO.git\ngit clone --depth 1 https://github.com/OWNER/REPO.git',
    proTip: 'Unlike `--depth 1` shallow clones, `--filter=blob:none` gives you full `git log` and `git blame` history at a fraction of download size.'
  },
  {
    id: 'cmd-git-remote-manage',
    levelId: 'lvl2_4',
    levelBadge: 'Level 2.5',
    tool: 'git',
    cmd: 'git remote add upstream <url>',
    syntax: 'git remote -v | add <name> <url> | set-url origin <ssh-url>',
    summary: 'Manage remote repository endpoints (`origin` for your repo/fork, `upstream` for the original canonical repository).',
    zones: ['local', 'remote'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Configured upstream remote & switched origin to SSH Ed25519 URL',
    example: 'git remote -v\ngit remote add upstream https://github.com/ORIGINAL/REPO.git\ngit remote set-url origin git@github.com:YOU/REPO.git',
    proTip: 'Run `git remote show origin` to inspect tracked head branches and push/pull URL configurations.'
  },
  {
    id: 'cmd-git-switch-create',
    levelId: 'lvl2_4',
    levelBadge: 'Level 3.2',
    tool: 'git',
    cmd: 'git switch -c feature/auth develop',
    syntax: 'git switch -c <new-branch> [<start-point>] | git switch -',
    summary: 'Create a new branch forked from `develop` (or any commit/remote ref) and switch the working tree to it.',
    zones: ['local', 'worktree'],
    danger: 'safe',
    lane: 2,
    category: 'feature',
    graphActionText: 'Forked new parallel branch feature/auth off develop (git switch -c)',
    example: 'git switch -c feature/auth develop\ngit switch main\ngit switch -',
    proTip: 'Use `git switch -` to toggle back and forth between your current branch and previous branch.'
  },
  {
    id: 'cmd-git-branch-vv',
    levelId: 'lvl2_4',
    levelBadge: 'Level 3.1 & 3.6',
    tool: 'git',
    cmd: 'git branch -avv',
    syntax: 'git branch [-avv | --merged main | --no-merged | -d | -D]',
    summary: 'Inspect all local and remote-tracking branches along with HEAD commit SHAs and ahead/behind upstream counts.',
    zones: ['local'],
    danger: 'safe',
    lane: 1,
    category: 'develop',
    graphActionText: 'Inspected branch topology & upstream ahead/behind tracking (git branch -avv)',
    example: 'git branch -avv\ngit branch --merged main\ngit branch --set-upstream-to=origin/develop develop',
    proTip: 'Combine with `git rev-list --left-right --count main...feature/auth` to get exact numeric ahead/behind commit counts.'
  },

  // ================= LEVEL 5 & 6: PULL REQUESTS, REVIEWS & ISSUES =================
  {
    id: 'cmd-gh-pr-create',
    levelId: 'lvl5_6',
    levelBadge: 'Level 5.2',
    tool: 'gh',
    cmd: 'gh pr create --base main --head feature/auth --reviewer team',
    syntax: 'gh pr create [--draft] [--base <br>] [--reviewer <users>] [--body "Fixes #42"]',
    summary: 'Open a GitHub Pull Request directly from the terminal with reviewers, labels, milestone, and auto-closing issue links.',
    zones: ['local', 'remote'],
    danger: 'safe',
    lane: 2,
    category: 'feature',
    graphActionText: 'Opened Pull Request #42 on GitHub targeting main (gh pr create)',
    example: 'gh pr create \\\n  --base main \\\n  --head feature/auth \\\n  --title "Implement OAuth2 PKCE" \\\n  --body "Fixes #42" \\\n  --reviewer alice,bob',
    proTip: 'Include `Fixes #42` or `Closes #42` in the PR body so GitHub automatically closes the linked issue on merge.'
  },
  {
    id: 'cmd-gh-pr-review-checks',
    levelId: 'lvl5_6',
    levelBadge: 'Level 5.4 & 16.4',
    tool: 'gh',
    cmd: 'gh pr checks 42 --watch',
    syntax: 'gh pr checkout 42 | gh pr diff 42 | gh pr review 42 --approve',
    summary: 'Stream live CI/CD status checks for a PR in the terminal, inspect its diff, or submit an approving code review.',
    zones: ['local', 'remote'],
    danger: 'safe',
    lane: 4,
    category: 'automation',
    graphActionText: 'Watched live CI status checks pass & approved PR #42 (gh pr checks --watch)',
    example: 'gh pr checkout 42\ngh pr diff 42\ngh pr checks 42 --watch\ngh pr review 42 --approve --body "LGTM!"',
    proTip: '`gh pr checkout 42` fetches and switches to a contributor’s PR branch even if it lives on an external fork.'
  },
  {
    id: 'cmd-gh-pr-merge-auto',
    levelId: 'lvl5_6',
    levelBadge: 'Level 5.6',
    tool: 'gh',
    cmd: 'gh pr merge 42 --auto --squash --delete-branch',
    syntax: 'gh pr merge <num> [--merge | --squash | --rebase] [--auto] [--delete-branch]',
    summary: 'Queue a Pull Request to automatically squash-merge as soon as required status checks and reviews pass, then delete the branch.',
    zones: ['local', 'remote'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Auto-squash merged PR #42 into main & deleted head branch (gh pr merge)',
    example: 'gh pr merge 42 --auto --squash --delete-branch',
    proTip: '`--auto` works seamlessly with GitHub Merge Queues and branch protection rulesets.'
  },
  {
    id: 'cmd-gh-issue-project',
    levelId: 'lvl5_6',
    levelBadge: 'Level 6.1 & 19.4',
    tool: 'gh',
    cmd: 'gh issue create --title "Bug" --label bug --assignee "@me"',
    syntax: 'gh issue list --search "auth" | gh issue comment 42 | gh project item-add',
    summary: 'Create, search, label, and link GitHub Issues and attach them to GitHub Projects v2 boards from the CLI.',
    zones: ['remote'],
    danger: 'safe',
    lane: 4,
    category: 'automation',
    graphActionText: 'Created Issue #42 & linked item to GitHub Project board (gh issue create)',
    example: 'gh issue create --title "Session expiry bug" --label bug --assignee "@me"\ngh issue list --search "session label:bug"',
    proTip: 'Use `gh search issues "repo:owner/name is:open label:bug"` for cross-repository queries.'
  },

  // ================= LEVEL 7 TO 9: ARCHAEOLOGY, MERGE, REBASE & CHERRY-PICK =================
  {
    id: 'cmd-git-log-graph-pickaxe',
    levelId: 'lvl7_9',
    levelBadge: 'Level 7.1',
    tool: 'git',
    cmd: 'git log -S "verifyToken" --oneline --graph --all',
    syntax: 'git log --oneline --graph --decorate --all | -S "<str>" | -G "<regex>"',
    summary: 'Render the ASCII branch commit DAG or run a Pickaxe search (`-S`) to find every commit that added or removed a token.',
    zones: ['local'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Executed Pickaxe archaeology search (-S "verifyToken") across commit DAG',
    example: 'git log --oneline --graph --decorate --all\ngit log -S "verifyToken" -p\ngit log -G "verify(Token|Session)" --all',
    proTip: '`-S` finds commits where the count of occurrences changed; `-G` searches added/removed diff lines matching a regex.'
  },
  {
    id: 'cmd-git-blame-range-diff',
    levelId: 'lvl7_9',
    levelBadge: 'Level 7.3 & 7.4',
    tool: 'git',
    cmd: 'git blame -w -C -C -C -L 20,60 src/auth.js',
    syntax: 'git blame -w -C -C -C -L <start>,<end> <file> | git range-diff',
    summary: 'Trace the true original commit behind lines of code—ignoring whitespace (`-w`) and following code moved across files (`-C -C -C`).',
    zones: ['local'],
    danger: 'safe',
    lane: 1,
    category: 'develop',
    graphActionText: 'Traced cross-file line origin with git blame -w -C -C -C',
    example: 'git blame -w -C -C -C -L 20,60 src/auth.js\ngit range-diff main...feature@{1} main...feature',
    proTip: 'Adding `-C -C -C` prevents refactoring commits that merely moved a function between files from hiding the real author.'
  },
  {
    id: 'cmd-git-merge-no-ff',
    levelId: 'lvl7_9',
    levelBadge: 'Level 8 & 9.1',
    tool: 'git',
    cmd: 'git merge --no-ff feature/login',
    syntax: 'git merge [--no-ff | --ff-only | --squash | --abort] <branch>',
    summary: 'Integrate a branch and record an explicit 2-parent merge commit (`--no-ff`) preserving the feature branch topology.',
    zones: ['local', 'worktree'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Created 2-parent merge commit integrating feature/login (--no-ff)',
    example: 'git switch main\ngit merge --no-ff feature/login\n# On conflict: git diff --name-only --diff-filter=U',
    proTip: 'During a merge conflict, run `git diff --name-only --diff-filter=U` to list only unresolved files.'
  },
  {
    id: 'cmd-git-rebase-onto',
    levelId: 'lvl7_9',
    levelBadge: 'Level 9.2',
    tool: 'git',
    cmd: 'git rebase --onto main old-base feature/login',
    syntax: 'git rebase -i --autosquash --update-refs | git rebase --onto <new> <old> <br>',
    summary: 'Transplant a commit range onto a completely different base branch (`--onto`) or autosquash fixups while updating stacked refs.',
    zones: ['local', 'worktree'],
    danger: 'caution',
    lane: 2,
    category: 'feature',
    graphActionText: 'Transplanted branch commits onto main via git rebase --onto',
    example: 'git rebase --onto main develop feature/login\ngit rebase -i --autosquash --update-refs origin/main',
    proTip: '`--update-refs` automatically moves any intermediate stacked branches along with the rebased tip!'
  },
  {
    id: 'cmd-git-cherry-pick-revert',
    levelId: 'lvl7_9',
    levelBadge: 'Level 9.4 & 9.5',
    tool: 'git',
    cmd: 'git cherry-pick abc1234^..def5678',
    syntax: 'git cherry-pick <sha> | git revert -m 1 <merge-sha>',
    summary: 'Copy specific commits onto the current branch (`cherry-pick`) or safely undo a published commit with an inverse commit (`revert`).',
    zones: ['local', 'worktree'],
    danger: 'safe',
    lane: 3,
    category: 'hotfix',
    graphActionText: 'Cherry-picked inclusive commit range abc1234^..def5678 onto hotfix branch',
    example: 'git cherry-pick abc1234^..def5678\ngit revert -m 1 MERGE_COMMIT_SHA',
    proTip: 'When reverting a merge commit, `-m 1` specifies parent 1 (usually `main`) as the mainline to keep.'
  },

  // ================= LEVEL 10 TO 12: UNDO, RECOVERY, SYNC & RELEASES =================
  {
    id: 'cmd-git-restore-source',
    levelId: 'lvl10_12',
    levelBadge: 'Level 10.1 & 10.2',
    tool: 'git',
    cmd: 'git restore --source=HEAD~2 --staged --worktree src/app.js',
    syntax: 'git restore [--staged] [--source=<commit>] [-p] <file>',
    summary: 'Unstage files (`--staged`), discard working-tree edits, or surgically restore a file from any historical commit.',
    zones: ['local', 'index', 'worktree'],
    danger: 'caution',
    lane: 1,
    category: 'develop',
    graphActionText: 'Surgically restored src/app.js from HEAD~2 into index & worktree',
    example: 'git restore --staged src/app.js\ngit restore --source=v1.0.0 -- src/config.js',
    proTip: 'Unlike `git reset`, `git restore` never moves your branch `HEAD` pointer—it only updates files in the index or worktree.'
  },
  {
    id: 'cmd-git-reset-modes',
    levelId: 'lvl10_12',
    levelBadge: 'Level 10.3',
    tool: 'git',
    cmd: 'git reset --soft HEAD~1',
    syntax: 'git reset [--soft | --mixed | --hard] <commit>',
    summary: 'Move the current branch pointer backward: `--soft` keeps changes staged; `--mixed` keeps changes unstaged; `--hard` wipes both.',
    zones: ['local', 'index', 'worktree'],
    danger: 'destructive',
    lane: 0,
    category: 'main',
    graphActionText: 'Moved HEAD~1 with --soft, keeping all commit changes staged in index',
    example: 'git reset --soft HEAD~1\ngit reset --mixed HEAD~1\n# Danger: git reset --hard HEAD~1',
    proTip: 'Use `git reset --soft HEAD~3 && git commit -m "Clean commit"` as the fastest way to squash your last 3 unpushed commits.'
  },
  {
    id: 'cmd-git-reflog-rescue',
    levelId: 'lvl10_12',
    levelBadge: 'Level 10.4',
    tool: 'git',
    cmd: 'git reflog && git branch recovery/work HEAD@{1}',
    syntax: 'git reflog [--all] | git branch <recovery-name> <sha>',
    summary: 'Inspect the local chronological safety log of every `HEAD` movement to rescue commits lost after a hard reset or bad rebase.',
    zones: ['local'],
    danger: 'safe',
    lane: 3,
    category: 'hotfix',
    graphActionText: 'Rescued orphaned commit from HEAD@{1} via git reflog into recovery branch',
    example: 'git reflog\ngit branch recovery/payment def5678',
    proTip: 'Always create a new branch (`git branch recovery <sha>`) rather than running another `reset --hard` while recovering.'
  },
  {
    id: 'cmd-git-push-force-lease',
    levelId: 'lvl10_12',
    levelBadge: 'Level 11.5',
    tool: 'git',
    cmd: 'git push --force-with-lease origin feature/login',
    syntax: 'git push --force-with-lease [--force-if-includes] origin <branch>',
    summary: 'Safely update a remote branch after rebasing—aborting automatically if a teammate pushed new commits you haven’t fetched.',
    zones: ['local', 'remote'],
    danger: 'caution',
    lane: 2,
    category: 'feature',
    graphActionText: 'Published rebased branch with atomic --force-with-lease check',
    example: 'git fetch origin\ngit rebase origin/main\ngit push --force-with-lease origin feature/login',
    proTip: 'Never run plain `git push --force`; `--force-with-lease` verifies your remote-tracking ref matches the server first.'
  },
  {
    id: 'cmd-gh-release-create',
    levelId: 'lvl10_12',
    levelBadge: 'Level 12.2',
    tool: 'gh',
    cmd: 'gh release create v2.4.0 --generate-notes dist/*.zip',
    syntax: 'git tag -s v2.4.0 | gh release create <tag> --generate-notes [<files>...]',
    summary: 'Create a signed release tag and publish a GitHub Release with auto-generated PR changelog notes and binary assets.',
    zones: ['local', 'remote'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Published signed GitHub Release v2.4.0 with auto-generated changelog notes',
    example: 'git tag -s v2.4.0 -m "Release v2.4.0"\ngit push origin v2.4.0\ngh release create v2.4.0 --generate-notes dist/app.zip',
    proTip: '`--generate-notes` automatically groups all merged PRs and first-time contributors since the previous tag.'
  },

  // ================= LEVEL 13 & 14: BISECT, WORKTREES & PLUMBING =================
  {
    id: 'cmd-git-bisect-run',
    levelId: 'lvl13_14',
    levelBadge: 'Level 13.1',
    tool: 'git',
    cmd: 'git bisect start HEAD v1.0.0 && git bisect run npm test',
    syntax: 'git bisect start <bad> <good> | git bisect run <cmd> | git bisect reset',
    summary: 'Execute an automated O(log N) binary search across hundreds of commits to pinpoint the exact commit that broke your test suite.',
    zones: ['local', 'worktree'],
    danger: 'safe',
    lane: 2,
    category: 'feature',
    graphActionText: 'Pinpointed regression commit in O(log N) steps via git bisect run',
    example: 'git bisect start HEAD v1.0.0\ngit bisect run npm test\ngit bisect reset',
    proTip: 'In a script passed to `git bisect run`, exit code `0` means good, `1..124` (except 125) means bad, and `125` skips untestable commits.'
  },
  {
    id: 'cmd-git-worktree-add',
    levelId: 'lvl13_14',
    levelBadge: 'Level 13.2',
    tool: 'git',
    cmd: 'git worktree add -b hotfix/crash ../project-hotfix main',
    syntax: 'git worktree add [-b <new-br>] <path> [<commit>] | list | remove',
    summary: 'Mount multiple independent working directories linked to the same `.git` object store so you can work on branches simultaneously.',
    zones: ['local', 'worktree'],
    danger: 'safe',
    lane: 3,
    category: 'hotfix',
    graphActionText: 'Mounted parallel worktree ../project-hotfix linked to shared .git store',
    example: 'git worktree list\ngit worktree add -b hotfix/crash ../project-hotfix main\ngit worktree remove ../project-hotfix',
    proTip: 'Worktrees are ideal for running parallel AI coding agents or fixing an urgent bug without stashing your active feature work.'
  },
  {
    id: 'cmd-git-sparse-submodule',
    levelId: 'lvl13_14',
    levelBadge: 'Level 13.3 & 13.4',
    tool: 'git',
    cmd: 'git sparse-checkout init --cone && git sparse-checkout set apps/web',
    syntax: 'git sparse-checkout set <dirs> | git submodule update --init --recursive',
    summary: 'Populate only specific directories in a massive monorepo (`sparse-checkout --cone`) or sync nested Git submodules.',
    zones: ['local', 'worktree'],
    danger: 'safe',
    lane: 1,
    category: 'develop',
    graphActionText: 'Scoped working tree to apps/web via cone-mode git sparse-checkout',
    example: 'git sparse-checkout init --cone\ngit sparse-checkout set apps/web packages/ui\ngit submodule update --init --recursive',
    proTip: 'Combine `git clone --filter=blob:none --no-checkout` with `git sparse-checkout set` for sub-second checkouts on huge monorepos.'
  },
  {
    id: 'cmd-git-plumbing-cat-file',
    levelId: 'lvl13_14',
    levelBadge: 'Level 13.8',
    tool: 'git',
    cmd: 'git cat-file -p HEAD',
    syntax: 'git cat-file [-t | -p] <obj> | git hash-object -w | git ls-tree HEAD',
    summary: 'Inspect raw low-level Git objects (`blob`, `tree`, `commit`, `tag`) directly inside the `.git/objects` content-addressable store.',
    zones: ['local'],
    danger: 'safe',
    lane: 3,
    category: 'hotfix',
    graphActionText: 'Decoded raw commit & tree pointers in .git/objects (git cat-file -p)',
    example: 'git cat-file -t HEAD\ngit cat-file -p HEAD\ngit ls-tree HEAD',
    proTip: 'Every commit points to a `tree` SHA, which maps filenames and permissions (`100644`) to immutable `blob` SHAs.'
  },

  // ================= LEVEL 15 TO 19: ACTIONS, SECURITY, RULESETS & API =================
  {
    id: 'cmd-gh-workflow-run-watch',
    levelId: 'lvl15_19',
    levelBadge: 'Level 16.2 & 16.3',
    tool: 'gh',
    cmd: 'gh workflow run deploy.yml --ref main -f env=staging',
    syntax: 'gh workflow run <file> | gh run watch <id> | gh run view --log-failed',
    summary: 'Trigger a `workflow_dispatch` GitHub Actions pipeline with inputs, watch live step progress, or dump failed job logs.',
    zones: ['remote'],
    danger: 'safe',
    lane: 4,
    category: 'automation',
    graphActionText: 'Dispatched GitHub Actions workflow & streamed live job logs (gh run watch)',
    example: 'gh workflow run deploy.yml --ref main -f environment=staging\ngh run list --workflow deploy.yml\ngh run view --log-failed\ngh run rerun RUN_ID --failed',
    proTip: '`gh run view --log-failed` outputs only the failing step logs—saving you from scrolling through thousands of lines in a browser.'
  },
  {
    id: 'cmd-git-filter-repo-secrets',
    levelId: 'lvl15_19',
    levelBadge: 'Level 17.4',
    tool: 'git',
    cmd: 'git filter-repo --path .env --invert-paths',
    syntax: 'git rm --cached .env | git filter-repo --path <file> --invert-paths',
    summary: 'Stop tracking a secret file (`git rm --cached`) or completely purge it from every historical commit in the repository (`filter-repo`).',
    zones: ['local', 'index'],
    danger: 'destructive',
    lane: 3,
    category: 'hotfix',
    graphActionText: 'Purged leaked .env file from entire repository commit history (filter-repo)',
    example: '# 1. Revoke secret immediately!\n# 2. Remove from index:\ngit rm --cached .env\n# 3. Purge from all history:\ngit filter-repo --path .env --invert-paths',
    proTip: 'Always rotate/revoke the leaked API key first—rewriting Git history does not invalidate cached clones or webhook logs.'
  },
  {
    id: 'cmd-gh-api-graphql',
    levelId: 'lvl15_19',
    levelBadge: 'Level 18.1 & 18.5',
    tool: 'gh',
    cmd: 'gh api graphql --paginate -f query="query { viewer { login } }"',
    syntax: 'gh api repos/{owner}/{repo}/pulls --paginate --jq ".[].title"',
    summary: 'Execute authenticated GitHub REST or GraphQL queries with automatic pagination and built-in `--jq` JSON filtering.',
    zones: ['remote'],
    danger: 'safe',
    lane: 4,
    category: 'automation',
    graphActionText: 'Queried GitHub GraphQL API with automatic cursor pagination (gh api)',
    example: 'gh api repos/OWNER/REPO/pulls --paginate --jq ".[].title"\ngh api graphql -f query="query { viewer { login } }"',
    proTip: 'Use placeholders `{owner}` and `{repo}` in `gh api repos/{owner}/{repo}/...`—`gh` auto-fills them from your current directory!'
  },
  {
    id: 'cmd-gh-ruleset-attestation',
    levelId: 'lvl15_19',
    levelBadge: 'Level 15 & 19.2',
    tool: 'gh',
    cmd: 'gh ruleset check main && gh attestation verify app.tar.gz',
    syntax: 'gh ruleset list | gh ruleset check <branch> | gh attestation verify <file>',
    summary: 'Inspect active repository branch-protection rulesets and cryptographically verify SLSA build provenance attestations.',
    zones: ['remote', 'local'],
    danger: 'safe',
    lane: 0,
    category: 'main',
    graphActionText: 'Verified branch rulesets & cryptographic SLSA build provenance attestation',
    example: 'gh ruleset list\ngh ruleset check main\ngh attestation verify dist/bundle.tgz --owner my-org',
    proTip: '`gh ruleset check` shows all organization and repo rules applying to a branch before your push gets rejected.'
  },

  // ================= LEVEL 20 TO 24 + BONUS GOD-LEVEL =================
  {
    id: 'cmd-god-merge-tree',
    levelId: 'lvl20_24',
    levelBadge: 'Bonus God-Level',
    tool: 'git',
    cmd: 'git merge-tree --write-tree main feature/ai-agent',
    syntax: 'git merge-tree --write-tree <branch1> <branch2>',
    summary: 'Compute a complete 3-way merge directly in the `.git/objects` database in memory without touching the working tree or index!',
    zones: ['local'],
    danger: 'safe',
    lane: 3,
    category: 'hotfix',
    graphActionText: 'Computed zero-checkout 3-way merge tree SHA in memory (git merge-tree)',
    example: 'TREE_SHA=$(git merge-tree --write-tree main feature/ai)\nCOMMIT_SHA=$(git commit-tree $TREE_SHA -p main -p feature/ai -m "Merge")\ngit update-ref refs/heads/main $COMMIT_SHA',
    proTip: 'Modern Git servers (including GitHub) and AI agent orchestrators use `git merge-tree --write-tree` to test and execute merges in milliseconds without a checkout.'
  },
  {
    id: 'cmd-god-absorb-notes',
    levelId: 'lvl20_24',
    levelBadge: 'Bonus God-Level',
    tool: 'git',
    cmd: 'git absorb --and-rebase && git notes add -m "verified" HEAD',
    syntax: 'git absorb --and-rebase | git notes add -m "<meta>" <commit>',
    summary: 'Automatically identify which earlier commit in a stack each staged hunk belongs to, generate `fixup!` commits, and attach metadata via `git notes`.',
    zones: ['index', 'local'],
    danger: 'safe',
    lane: 2,
    category: 'feature',
    graphActionText: 'Auto-absorbed review fixes into parent commits & attached git notes',
    example: 'git add -u\ngit absorb --and-rebase\ngit notes add -m "Reviewed-by: AI-Agent-v4" HEAD',
    proTip: '`git notes` attaches searchable metadata to commits without changing their SHA-1/SHA-256 hash!'
  }
];

// ============================================================================
// 7. DECISION MATRIX & TROUBLESHOOTING RECIPES (FROM ENCYCLOPEDIA FINAL AUDIT)
// ============================================================================
const DECISION_GUIDES = [
  {
    title: 'git reset vs. git restore vs. git revert',
    items: [
      {
        cmd: 'git restore <file>',
        when: 'You want to discard unstaged edits or unstage (`--staged`) a file without moving the branch commit pointer.',
        rewritesHistory: 'No (File-level only)',
        badge: 'Safe for files'
      },
      {
        cmd: 'git reset [--soft|--mixed|--hard] HEAD~1',
        when: 'You want to move the current branch pointer backward on UNPUBLISHED local commits.',
        rewritesHistory: 'Yes (Moves branch ref)',
        badge: 'Local branches only'
      },
      {
        cmd: 'git revert <commit>',
        when: 'You need to undo a commit that has ALREADY been pushed to `main` or shared with teammates.',
        rewritesHistory: 'No (Creates new inverse commit)',
        badge: 'Production safe'
      }
    ]
  },
  {
    title: 'git merge vs. git rebase vs. Squash Merge',
    items: [
      {
        cmd: 'git merge --no-ff <branch>',
        when: 'Combining shared branches (`develop` -> `main`) where preserving true historical branch topology matters.',
        rewritesHistory: 'No',
        badge: 'Preserves topology'
      },
      {
        cmd: 'git rebase origin/main',
        when: 'Updating your own private feature branch so your commits sit cleanly on top of the latest `main`.',
        rewritesHistory: 'Yes (New commit SHAs)',
        badge: 'Linear feature history'
      },
      {
        cmd: 'gh pr merge --squash',
        when: 'Merging a feature PR with 15 messy "WIP" commits into `main` as one clean, atomic commit.',
        rewritesHistory: 'Condenses branch into 1 commit',
        badge: 'Clean trunk log'
      }
    ]
  }
];

const TROUBLESHOOTING_RECIPES = [
  {
    error: '! [rejected] main -> main (non-fast-forward)',
    cause: 'The remote branch on GitHub has new commits that do not exist in your local branch.',
    diagnosis: 'git fetch origin && git status -sb',
    fix: 'git pull --rebase origin main && git push origin main',
    warning: 'Never blindly run `git push --force` on `main`—you will erase teammates’ commits.'
  },
  {
    error: 'You are in "detached HEAD" state',
    cause: 'You checked out a raw commit SHA or tag instead of a branch name (`HEAD` points directly to a commit, not `refs/heads/*`).',
    diagnosis: 'git status && git log -1',
    fix: 'git switch -crescue-branch',
    warning: 'Any commits made in detached HEAD will become orphaned when you switch away unless you create a branch with `git switch -c`.'
  },
  {
    error: 'Permission denied (publickey) / fatal: Could not read from remote',
    cause: 'SSH agent is not running, your Ed25519 key is not loaded, or the public key isn’t registered on GitHub.',
    diagnosis: 'ssh -T git@github.com && gh ssh-key list',
    fix: 'eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519 && gh ssh-key add ~/.ssh/id_ed25519.pub',
    warning: 'Never upload your private key (`~/.ssh/id_ed25519`); only upload the `.pub` file.'
  },
  {
    error: 'Accidental commit of API secret / .env file pushed to GitHub',
    cause: 'A `.env` or credential file was staged before being added to `.gitignore`.',
    diagnosis: 'git log --stat -- .env',
    fix: '1) Revoke key immediately -> 2) git filter-repo --path .env --invert-paths -> 3) git push --force-with-lease',
    warning: 'Deleting `.env` in a new commit does NOT remove it from earlier commit objects.'
  }
];

// ============================================================================
// 8. MAIN APPLICATION
// ============================================================================
export default function App() {
  const [scenarioKey, setScenarioKey] = useState('level3_4');
  const [stepIndex, setStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [showForkCurves, setShowForkCurves] = useState(true);
  const [showHighlights, setShowHighlights] = useState(true);

  // Dynamic custom nodes & goal state when user executes commands from Encyclopedia or Terminal
  const [customNodesOverride, setCustomNodesOverride] = useState(null);
  const [customGoalOverride, setCustomGoalOverride] = useState(null);
  const [customFooterOverride, setCustomFooterOverride] = useState(null);

  // Encyclopedia & Inspector states
  const [activeRightTab, setActiveRightTab] = useState('encyclopedia'); // 'encyclopedia' | 'decisions' | 'troubleshoot'
  const [selectedLevelId, setSelectedLevelId] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCommand, setSelectedCommand] = useState(COMMAND_DATABASE[11]); // git switch -c feature/auth
  const [selectedNodeId, setSelectedNodeId] = useState(null);

  // Interactive Terminal CLI Sandbox state
  const [terminalInput, setTerminalInput] = useState('');
  const [terminalHistory, setTerminalHistory] = useState([
    {
      cmd: 'git log --oneline --graph --decorate --all',
      output: 'Multi-lane DAG engine ready. Click any command on the right or type a git/gh command below!'
    }
  ]);

  const [copiedNotice, setCopiedNotice] = useState(false);
  const [copiedCmdId, setCopiedCmdId] = useState(null);
  const [emailNotice, setEmailNotice] = useState(false);
  const [seenNodeIds, setSeenNodeIds] = useState(() => new Set());

  const scenario = SCENARIOS[scenarioKey] || SCENARIOS.level3_4;
  const currentStep = scenario.steps[stepIndex] || scenario.steps[0];
  const activeNodes = customNodesOverride || currentStep.nodes;
  const activeGoalState = customGoalOverride?.state || currentStep.goalState;
  const activeGoalText = customGoalOverride?.text || currentStep.goalText;
  const activeGoalRight = customGoalOverride?.right || currentStep.goalRight;
  const activeFooterText = customFooterOverride || currentStep.footerText;

  // Auto-advance timeline
  useEffect(() => {
    if (!isPlaying) return;

    const timer = setTimeout(() => {
      if (stepIndex < scenario.steps.length - 1) {
        setStepIndex((prev) => prev + 1);
      } else {
        setIsPlaying(false);
      }
    }, currentStep.duration);

    return () => clearTimeout(timer);
  }, [isPlaying, stepIndex, scenario.steps.length, currentStep.duration]);

  // Track seen nodes so only newly added rows trigger the cryptographic scramble
  useEffect(() => {
    if (!activeNodes.length) return;
    const timer = setTimeout(() => {
      setSeenNodeIds((prev) => {
        const next = new Set(prev);
        activeNodes.forEach((n) => next.add(n.id));
        return next;
      });
    }, 560);
    return () => clearTimeout(timer);
  }, [activeNodes]);

  // Filter Encyclopedia commands by Level + Search Query
  const filteredCommands = useMemo(() => {
    return COMMAND_DATABASE.filter((item) => {
      const matchesLevel =
        selectedLevelId === 'all' || item.levelId === selectedLevelId;
      const q = searchTerm.trim().toLowerCase();
      if (!q) return matchesLevel;
      return (
        matchesLevel &&
        (item.cmd.toLowerCase().includes(q) ||
          item.summary.toLowerCase().includes(q) ||
          item.levelBadge.toLowerCase().includes(q) ||
          item.syntax.toLowerCase().includes(q))
      );
    });
  }, [selectedLevelId, searchTerm]);

  const handleRestart = () => {
    setCustomNodesOverride(null);
    setCustomGoalOverride(null);
    setCustomFooterOverride(null);
    setSeenNodeIds(new Set());
    setStepIndex(0);
    setIsPlaying(true);
  };

  const handleScenarioSwitch = (newKey) => {
    setScenarioKey(newKey);
    setCustomNodesOverride(null);
    setCustomGoalOverride(null);
    setCustomFooterOverride(null);
    setShowForkCurves(SCENARIOS[newKey].defaultShowForks);
    setSeenNodeIds(new Set());
    setStepIndex(0);
    setIsPlaying(true);
  };

  // ==========================================================================
  // SIMULATE ANY ENCYCLOPEDIA COMMAND ON THE MULTI-LANE BRANCHING GRAPH
  // ==========================================================================
  const handleSimulateCommandOnGraph = (cmdObj) => {
    setSelectedCommand(cmdObj);
    setIsPlaying(false);

    const baseNodes =
      customNodesOverride ||
      scenario.steps[scenario.steps.length - 1].nodes;

    const isMergeOrRelease =
      cmdObj.cmd.includes('merge') ||
      cmdObj.cmd.includes('release') ||
      cmdObj.cmd.includes('push --force-with-lease') ||
      cmdObj.cmd.includes('gh repo create');

    const newNodeId = `sim-${cmdObj.id}-${Date.now()}`;
    const newNode = {
      id: newNodeId,
      lane: cmdObj.lane ?? 1,
      forkFromLane: Math.max(0, (cmdObj.lane ?? 1) - 1),
      category: cmdObj.category || 'feature',
      text: cmdObj.graphActionText || `Executed ${cmdObj.cmd}`,
      source: cmdObj.cmd.split(' ').slice(0, 3).join(' '),
      cmd: cmdObj.cmd,
      bold: true,
      highlightedOnComplete: true
    };

    const nextNodes = [newNode, ...baseNodes.slice(0, 9)];
    setCustomNodesOverride(nextNodes);
    setSelectedNodeId(newNodeId);

    setCustomGoalOverride({
      state: isMergeOrRelease ? 'done' : 'done',
      text: isMergeOrRelease
        ? `Merged & converged: ${cmdObj.cmd}`
        : `Simulated: ${cmdObj.cmd}`,
      right: cmdObj.levelBadge
    });

    setCustomFooterOverride(
      `Executed "${cmdObj.cmd}" on Lane ${cmdObj.lane ?? 0} (${cmdObj.zones.join(' -> ')})`
    );

    setTerminalHistory((prev) => [
      {
        cmd: cmdObj.cmd,
        output: `✓ [Lane ${cmdObj.lane ?? 0}] ${cmdObj.graphActionText}`
      },
      ...prev.slice(0, 5)
    ]);
  };

  // ==========================================================================
  // INTERACTIVE TERMINAL CLI PARSER (Parses real user-typed git & gh commands!)
  // ==========================================================================
  const handleRunTerminalCommand = (rawInput) => {
    const trimmed = (rawInput || terminalInput).trim();
    if (!trimmed) return;

    setIsPlaying(false);
    const lower = trimmed.toLowerCase();

    // Match against database first or infer lane & category intelligently
    const matchedDb = COMMAND_DATABASE.find((c) =>
      lower.startsWith(c.cmd.toLowerCase().split(' ').slice(0, 3).join(' '))
    );

    let lane = 0;
    let category = 'main';
    let actionText = `Executed: ${trimmed}`;
    let shouldMerge = false;

    if (
      lower.includes('switch -c') ||
      lower.includes('checkout -b') ||
      lower.includes('feature')
    ) {
      lane = 2;
      category = 'feature';
      actionText = `Created & switched to feature branch (${trimmed})`;
    } else if (
      lower.includes('hotfix') ||
      lower.includes('cherry-pick') ||
      lower.includes('reflog') ||
      lower.includes('filter-repo') ||
      lower.includes('bisect')
    ) {
      lane = 3;
      category = 'hotfix';
      actionText = `Executed history/recovery operation (${trimmed})`;
    } else if (
      lower.startsWith('gh ') ||
      lower.includes('workflow') ||
      lower.includes('api')
    ) {
      lane = 4;
      category = 'automation';
      actionText = `Executed GitHub CLI automation (${trimmed})`;
      if (lower.includes('gh pr merge') || lower.includes('gh release')) {
        shouldMerge = true;
      }
    } else if (
      lower.includes('add') ||
      lower.includes('commit') ||
      lower.includes('rebase') ||
      lower.includes('stash') ||
      lower.includes('develop')
    ) {
      lane = 1;
      category = 'develop';
      actionText = `Updated index / branch history (${trimmed})`;
    } else if (lower.includes('merge') || lower.includes('push')) {
      lane = 0;
      category = 'main';
      actionText = `Integrated changes into trunk (${trimmed})`;
      shouldMerge = true;
    }

    if (matchedDb) {
      setSelectedCommand(matchedDb);
    }

    const baseNodes =
      customNodesOverride ||
      scenario.steps[scenario.steps.length - 1].nodes;

    const newNodeId = `cli-${Date.now()}`;
    const newNode = {
      id: newNodeId,
      lane,
      forkFromLane: Math.max(0, lane - 1),
      category,
      text: actionText,
      source: trimmed.slice(0, 22),
      cmd: trimmed,
      bold: true,
      highlightedOnComplete: true
    };

    setCustomNodesOverride([newNode, ...baseNodes.slice(0, 9)]);
    setSelectedNodeId(newNodeId);

    setCustomGoalOverride({
      state: 'done',
      text: shouldMerge
        ? `Merged all active lanes -> ${trimmed}`
        : `Active HEAD: ${trimmed}`,
      right: `Lane ${lane}`
    });

    setCustomFooterOverride(`CLI executed: ${trimmed}`);
    setTerminalHistory((prev) => [
      {
        cmd: trimmed,
        output: `✓ Spawned node on Lane ${lane} [${category}]`
      },
      ...prev.slice(0, 5)
    ]);
    setTerminalInput('');
  };

  const handleCopyBrief = () => {
    const summaryLines = [
      `${scenario.entityTitle} (${scenario.domain})`,
      `${activeGoalText}`,
      '',
      ...activeNodes.map(
        (n) => `• [Lane ${n.lane ?? 0} | ${n.category}] ${n.text} (${n.source})`
      )
    ].join('\n');

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(summaryLines).catch(() => {});
    }
    setCopiedNotice(true);
    setTimeout(() => setCopiedNotice(false), 2000);
  };

  const handleCopySnippet = (text, id) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(() => {});
    }
    setCopiedCmdId(id);
    setTimeout(() => setCopiedCmdId(null), 1800);
  };

  return (
    <div className="min-h-screen bg-[#ECEBE8] text-[#111827] flex flex-col items-center p-3 sm:p-6 font-sans antialiased selection:bg-blue-100">
      <style>{`
        @keyframes nodeSlideIn {
          0% {
            opacity: 0;
            transform: translateY(-10px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-node-enter {
          animation: nodeSlideIn 320ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
        @keyframes drawMergeLine {
          0% {
            stroke-dashoffset: 320;
            opacity: 0.3;
          }
          100% {
            stroke-dashoffset: 0;
            opacity: 1;
          }
        }
        .animate-merge-draw {
          stroke-dasharray: 320;
          animation: drawMergeLine 550ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
      `}</style>

      {/* ====================================================================
          TOP NAVIGATION & VISUAL WORKFLOW SCENARIO SELECTOR
         ==================================================================== */}
      <div className="w-full max-w-[1380px] mb-4 bg-white/95 backdrop-blur-md border border-black/[0.07] rounded-2xl p-3.5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gray-900 text-white flex items-center justify-center shadow-xs">
              <GitBranch className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-[16px] font-bold tracking-tight text-gray-900">
                  Git & GitHub Command Encyclopedia · Multi-Lane Visual Simulator
                </h1>
                <span className="px-2 py-0.5 text-[11px] font-mono font-semibold bg-emerald-50 text-emerald-700 rounded-md border border-emerald-200/60">
                  Levels 0–24 + God-Level
                </span>
              </div>
              <p className="text-xs text-gray-500">
                Select any visual workflow below or click{' '}
                <span className="font-medium text-gray-700">
                  &ldquo;Simulate on Graph&rdquo;
                </span>{' '}
                on any command in the Encyclopedia to watch it mutate the multi-lane DAG.
              </p>
            </div>
          </div>

          {/* Playback & Graph Geometry Controls */}
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              onClick={() => {
                setCustomNodesOverride(null);
                setCustomGoalOverride(null);
                setIsPlaying(false);
                setStepIndex(Math.max(0, scenario.steps.length - 2));
              }}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-xs font-medium text-gray-700 transition"
              title="View Parallel Lanes before merge"
            >
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              <span>Parallel Lanes</span>
            </button>

            <button
              onClick={() => {
                setCustomNodesOverride(null);
                setCustomGoalOverride(null);
                setIsPlaying(false);
                setStepIndex(scenario.steps.length - 1);
              }}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-emerald-200 bg-emerald-50/70 hover:bg-emerald-50 text-xs font-medium text-emerald-800 transition"
              title="View Bezier Merge Curves into top green synthesis node"
            >
              <GitMerge className="w-3.5 h-3.5 text-emerald-600" />
              <span>Bezier Merge</span>
            </button>

            <button
              onClick={() => setShowForkCurves((v) => !v)}
              className={`px-2.5 py-1.5 rounded-lg border text-xs font-medium transition ${
                showForkCurves
                  ? 'bg-violet-50 border-violet-200 text-violet-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {showForkCurves ? '✓ Fork Curves' : '+ Fork Curves'}
            </button>

            <div className="h-4 w-[1px] bg-gray-200 mx-1" />

            <button
              onClick={() => {
                setCustomNodesOverride(null);
                setCustomGoalOverride(null);
                setIsPlaying(false);
                setStepIndex((prev) =>
                  prev > 0 ? prev - 1 : scenario.steps.length - 1
                );
              }}
              className="p-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 transition"
            >
              <SkipBack className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={() => {
                if (stepIndex === scenario.steps.length - 1 && !isPlaying) {
                  handleRestart();
                } else {
                  setIsPlaying((p) => !p);
                }
              }}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-900 hover:bg-gray-800 text-white text-xs font-medium transition"
            >
              {isPlaying ? (
                <>
                  <Pause className="w-3.5 h-3.5" />
                  <span>Pause</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  <span>Play</span>
                </>
              )}
            </button>

            <button
              onClick={() => {
                setCustomNodesOverride(null);
                setCustomGoalOverride(null);
                setIsPlaying(false);
                setStepIndex((prev) => (prev + 1) % scenario.steps.length);
              }}
              className="p-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 transition"
            >
              <SkipForward className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={handleRestart}
              className="p-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 transition"
              title="Reset & Replay"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Scenario Pills Bar (8 Curated Multi-Lane Visual Scenarios) */}
        <div className="pt-2.5 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          {Object.values(SCENARIOS).map((sc) => {
            const active = scenarioKey === sc.id;
            return (
              <button
                key={sc.id}
                onClick={() => handleScenarioSwitch(sc.id)}
                className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all border ${
                  active
                    ? 'bg-gray-900 text-white border-gray-900 shadow-xs'
                    : 'bg-[#F8F9FA] text-gray-700 border-gray-200/80 hover:bg-gray-100'
                }`}
              >
                <span
                  className={`px-1.5 py-0.2 rounded text-[10px] font-mono ${
                    active
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : 'bg-gray-200/80 text-gray-600'
                  }`}
                >
                  {sc.badge}
                </span>
                <span>{sc.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ====================================================================
          MAIN 2-COLUMN WORKSPACE:
          LEFT: KESTREL-STYLE MULTI-LANE BRANCHING CARD + LIVE CLI TERMINAL
          RIGHT: SEARCHABLE LEVEL 0-24 COMMAND ENCYCLOPEDIA & ARCHITECTURE INSPECTOR
         ==================================================================== */}
      <div className="w-full max-w-[1380px] grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* ==================================================================
            LEFT COLUMN (7 COLS): MULTI-LANE BRANCHING CARD + TERMINAL SANDBOX
           ================================================================== */}
        <div className="lg:col-span-7 flex flex-col gap-3.5">
          {/* EXACT KESTREL FREIGHT / GIT DAG CARD */}
          <div className="w-full bg-white rounded-[22px] border border-[#E4E4E7] shadow-[0_20px_50px_-15px_rgba(0,0,0,0.08),0_2px_10px_-2px_rgba(0,0,0,0.03)] overflow-hidden transition-all duration-300">
            <div className="px-6 pt-6 pb-4">
              {/* Top Header Row */}
              <div className="flex items-center justify-between gap-4 mb-3.5">
                <div className="flex items-baseline gap-2 min-w-0">
                  <h2 className="text-[17px] font-semibold tracking-[-0.015em] text-[#111827] truncate">
                    {scenario.entityTitle}
                  </h2>
                  <span
                    className={`text-[14.5px] font-mono text-[#9CA3AF] transition-all duration-300 truncate ${
                      currentStep.showDomain
                        ? 'opacity-100 translate-x-0'
                        : 'opacity-0 -translate-x-1 pointer-events-none'
                    }`}
                  >
                    {scenario.domain}
                  </span>
                </div>

                {/* Right Status Indicator */}
                <div className="shrink-0 flex items-center">
                  {activeGoalState !== 'done' ? (
                    <div className="flex items-center gap-2 text-[13.5px] font-medium text-[#2563EB]">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-[#2563EB]"></span>
                      </span>
                      <span>Executing Flow</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-[13.5px] font-medium text-[#16A34A]">
                      <span className="inline-flex rounded-full h-2 w-2 bg-[#16A34A]" />
                      <span>Merged & Verified</span>
                    </div>
                  )}
                </div>
              </div>

              {/* MULTI-LANE SVG BRANCHING TIMELINE */}
              <BranchingGitTimeline
                nodes={activeNodes}
                lanesConfig={scenario.lanesConfig}
                goalState={activeGoalState}
                goalText={activeGoalText}
                goalRight={activeGoalRight}
                showForkCurves={showForkCurves}
                showHighlightsOnComplete={showHighlights}
                seenNodeIds={seenNodeIds}
                scenarioKey={scenarioKey}
                selectedNodeId={selectedNodeId}
                onSelectNode={(node) => {
                  setSelectedNodeId(node.id);
                  if (node.cmd) {
                    const found = COMMAND_DATABASE.find(
                      (c) =>
                        node.cmd.includes(c.cmd.split(' ')[0]) &&
                        node.cmd.includes(c.cmd.split(' ')[1] || '')
                    );
                    if (found) setSelectedCommand(found);
                  }
                }}
              />

              {/* HORIZONTAL STATUS PILLS ROW */}
              <div className="mt-4 pt-1 flex items-center gap-2 overflow-x-auto no-scrollbar">
                {currentStep.pills.map((pill) => {
                  const isDone =
                    pill.state === 'done' || activeGoalState === 'done';
                  const isChecking =
                    !isDone && pill.state === 'checking';

                  return (
                    <div
                      key={pill.id}
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[13px] whitespace-nowrap transition-all duration-300 ${
                        isDone
                          ? 'border-[#E5E7EB] bg-white text-[#1F2937]'
                          : isChecking
                          ? 'border-[#E5E7EB] bg-white text-[#1F2937]'
                          : 'border-[#F3F4F6] bg-[#FAFAFA] text-[#9CA3AF]'
                      }`}
                    >
                      {isDone && (
                        <Check
                          className="w-3.5 h-3.5 text-[#16A34A] shrink-0"
                          strokeWidth={2.4}
                        />
                      )}
                      {isChecking && (
                        <SpinnerArc size={13} colorClass="text-[#6B7280]" />
                      )}
                      {!isDone && !isChecking && (
                        <span className="w-1.5 h-1.5 rounded-full bg-[#D1D5DB] shrink-0 mr-0.5" />
                      )}

                      <span
                        className={
                          isDone || isChecking
                            ? 'font-medium text-[#374151]'
                            : ''
                        }
                      >
                        {pill.label}
                      </span>
                      <span
                        className={
                          isDone || isChecking
                            ? 'text-[#6B7280]'
                            : 'text-[#9CA3AF]'
                        }
                      >
                        {pill.detail}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* LIVE ACTIVITY FOOTER BAR + CTA */}
              <div className="mt-3.5 min-h-[34px] flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0 text-[13.5px]">
                  {activeGoalState === 'done' || currentStep.footerDone ? (
                    <Check
                      className="w-4 h-4 text-[#16A34A] shrink-0"
                      strokeWidth={2.4}
                    />
                  ) : (
                    <SpinnerArc size={15} colorClass="text-[#9CA3AF]" />
                  )}

                  <span className="truncate text-[#374151] font-mono text-[12.5px]">
                    {activeFooterText}
                  </span>
                </div>

                {currentStep.ctaMode === 'email' && activeGoalState !== 'done' && (
                  <button
                    onClick={() => {
                      setEmailNotice(true);
                      setTimeout(() => setEmailNotice(false), 2000);
                    }}
                    className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#EFF6FF] hover:bg-[#DBEAFE] text-[#2563EB] text-[13px] font-medium transition-all"
                  >
                    <Mail className="w-3.5 h-3.5" />
                    <span>
                      {emailNotice
                        ? 'CI Webhook armed!'
                        : "Email me when it's ready"}
                    </span>
                  </button>
                )}

                {(currentStep.ctaMode === 'copy' || activeGoalState === 'done') && (
                  <button
                    onClick={handleCopyBrief}
                    className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border border-[#E5E7EB] bg-white hover:bg-[#F9FAFB] text-[#374151] text-[13px] font-medium shadow-2xs transition-all"
                  >
                    {copiedNotice ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-emerald-700">Copied Log!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-[#6B7280]" />
                        <span>Copy branch log</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* MIDDLE COMMAND CONTEXT BAR + QUICK LANE INJECTOR */}
            <div className="border-t border-[#F0F0F2] px-6 py-3 flex flex-wrap items-center justify-between gap-2 bg-[#FAFAFA]/60">
              <div className="flex items-center gap-2 min-w-0">
                <Terminal className="w-4 h-4 text-[#6B7280] shrink-0" />
                <code className="text-[13px] text-[#111827] font-mono truncate">
                  {selectedCommand ? selectedCommand.cmd : scenario.searchQuery}
                </code>
                <span
                  className={`px-2 py-0.5 rounded-md text-[11.5px] font-medium shrink-0 ${
                    activeGoalState === 'done'
                      ? 'bg-[#ECFDF5] text-[#047857]'
                      : 'bg-[#EFF6FF] text-[#2563EB]'
                  }`}
                >
                  {selectedCommand ? selectedCommand.levelBadge : scenario.badge}
                </span>
              </div>

              {/* Quick Lane Node Spawners */}
              <div className="flex items-center gap-1">
                <span className="text-[11px] text-gray-400 mr-1">
                  Spawn Lane:
                </span>
                {[
                  { lane: 0, label: 'L0 main' },
                  { lane: 1, label: 'L1 dev' },
                  { lane: 2, label: 'L2 feat' },
                  { lane: 3, label: 'L3 fix' },
                  { lane: 4, label: 'L4 gh' }
                ].map((l) => (
                  <button
                    key={l.lane}
                    onClick={() => {
                      const sampleCmds = [
                        'git pull --ff-only origin main',
                        'git add -p && git commit -m "feat: update"',
                        'git switch -c feature/new-branch',
                        'git cherry-pick abc1234',
                        'gh pr checks 42 --watch'
                      ];
                      handleRunTerminalCommand(sampleCmds[l.lane]);
                    }}
                    className="px-2 py-0.5 rounded border border-gray-200 bg-white hover:bg-gray-100 text-[11px] font-mono text-gray-700 transition"
                    title={`Spawn node on ${l.label}`}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </div>

            {/* BOTTOM INTERACTIVE GIT / GH CLI TERMINAL COMPOSER */}
            <div className="border-t border-[#F0F0F2] px-6 pt-3.5 pb-4 bg-white">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-emerald-600 font-mono font-bold text-sm select-none">
                  $
                </span>
                <input
                  type="text"
                  value={terminalInput}
                  onChange={(e) => setTerminalInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && terminalInput.trim()) {
                      handleRunTerminalCommand(terminalInput);
                    }
                  }}
                  placeholder={scenario.placeholder}
                  className="w-full text-[14.5px] font-mono text-[#111827] placeholder-[#9CA3AF] bg-transparent focus:outline-none"
                />
                <button
                  onClick={() => handleRunTerminalCommand(terminalInput || 'git switch -c feature/ai-agent')}
                  className="shrink-0 inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-gray-900 hover:bg-gray-800 text-white text-xs font-medium transition"
                >
                  <span>Run on Graph</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {/* Quick Command Suggestion Chips */}
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F3F4F6] text-[#374151] text-[12px] font-medium">
                    <Folder className="w-3 h-3 text-[#6B7280]" />
                    <span>{scenario.workspaceChip}</span>
                  </span>
                  {[
                    'git switch -c feature/rag',
                    'git rebase -i --autosquash',
                    'gh pr merge 42 --squash',
                    'git reflog',
                    'git bisect run npm test'
                  ].map((quickCmd) => (
                    <button
                      key={quickCmd}
                      onClick={() => handleRunTerminalCommand(quickCmd)}
                      className="px-2 py-0.5 rounded-md bg-gray-50 hover:bg-blue-50 hover:text-blue-700 border border-gray-200/80 text-[11.5px] font-mono text-gray-600 transition"
                    >
                      {quickCmd}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* TIMELINE SCRUBBER + LIVE CLI OUTPUT LOG */}
          <div className="bg-white/90 backdrop-blur-md border border-black/[0.06] rounded-2xl p-3.5 flex flex-col gap-2.5 shadow-2xs">
            <div className="flex items-center gap-3">
              <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider shrink-0">
                {currentStep.timeLabel}
              </span>
              <div className="flex-1 flex items-center gap-1.5">
                {scenario.steps.map((s, idx) => {
                  const active = idx === stepIndex;
                  const passed = idx < stepIndex;
                  return (
                    <button
                      key={idx}
                      onClick={() => {
                        setCustomNodesOverride(null);
                        setCustomGoalOverride(null);
                        setIsPlaying(false);
                        setStepIndex(idx);
                      }}
                      className="group flex-1 py-1 focus:outline-none"
                      title={`Jump to ${s.timeLabel}`}
                    >
                      <div
                        className={`h-1.5 rounded-full transition-all ${
                          active
                            ? 'bg-emerald-600 scale-y-125'
                            : passed
                            ? 'bg-emerald-300 group-hover:bg-emerald-400'
                            : 'bg-gray-200 group-hover:bg-gray-300'
                        }`}
                      />
                    </button>
                  );
                })}
              </div>
              <span className="text-[11px] font-mono text-gray-500 shrink-0">
                Step {stepIndex + 1}/{scenario.steps.length}
              </span>
            </div>

            {/* Compact Terminal Execution History */}
            <div className="bg-gray-950 text-gray-200 rounded-xl p-2.5 font-mono text-[11.5px] flex flex-col gap-1 max-h-[92px] overflow-y-auto">
              {terminalHistory.map((entry, i) => (
                <div key={i} className="flex items-center justify-between gap-2">
                  <div className="truncate">
                    <span className="text-emerald-400 mr-1.5">$</span>
                    <span className="text-white">{entry.cmd}</span>
                  </div>
                  <span className="text-gray-400 text-[11px] shrink-0">
                    {entry.output}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ==================================================================
            RIGHT COLUMN (5 COLS): ENCYCLOPEDIA, ARCHITECTURE ZONES & GUIDES
           ================================================================== */}
        <div className="lg:col-span-5 flex flex-col gap-3.5">
          {/* 1. SELECTED COMMAND ARCHITECTURE & 4-ZONE DATA FLOW INSPECTOR */}
          {selectedCommand && (
            <div className="bg-white rounded-2xl border border-[#E4E4E7] p-4 shadow-xs">
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-gray-900 text-white">
                    {selectedCommand.levelBadge}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-md text-[11px] font-mono font-medium ${
                      selectedCommand.tool === 'gh'
                        ? 'bg-amber-50 text-amber-800 border border-amber-200'
                        : 'bg-blue-50 text-blue-700 border border-blue-200'
                    }`}
                  >
                    {selectedCommand.tool === 'gh' ? 'GitHub CLI (gh)' : 'Git Core'}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-md text-[11px] font-medium ${
                      selectedCommand.danger === 'destructive'
                        ? 'bg-red-50 text-red-700 border border-red-200'
                        : selectedCommand.danger === 'caution'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    }`}
                  >
                    {selectedCommand.danger === 'destructive'
                      ? '⚠ History / Worktree Destructive'
                      : selectedCommand.danger === 'caution'
                      ? '⚡ Rewrites Commits / Index'
                      : '✓ Non-Destructive'}
                  </span>
                </div>

                <button
                  onClick={() => handleSimulateCommandOnGraph(selectedCommand)}
                  className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium shadow-2xs transition"
                >
                  <Zap className="w-3.5 h-3.5" />
                  <span>Simulate on Graph</span>
                </button>
              </div>

              {/* Command Title & Syntax */}
              <div className="flex items-center justify-between bg-gray-950 text-gray-100 px-3 py-2 rounded-xl font-mono text-[12.5px] mb-2.5">
                <code className="truncate text-emerald-300">
                  {selectedCommand.cmd}
                </code>
                <button
                  onClick={() =>
                    handleCopySnippet(selectedCommand.example, selectedCommand.id)
                  }
                  className="text-gray-400 hover:text-white text-xs flex items-center gap-1 shrink-0 ml-2"
                >
                  {copiedCmdId === selectedCommand.id ? (
                    <span className="text-emerald-400 text-[11px]">Copied!</span>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span className="text-[11px]">Copy</span>
                    </>
                  )}
                </button>
              </div>

              <p className="text-[13px] text-gray-700 leading-relaxed mb-3">
                {selectedCommand.summary}
              </p>

              {/* 4-ZONE GIT ARCHITECTURE PIPELINE (Working Tree -> Index -> Local Repo -> Remote GitHub) */}
              <div className="mb-3">
                <div className="text-[10.5px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                  Affected Git & GitHub Architecture Zones
                </div>
                <div className="grid grid-cols-4 gap-1.5">
                  {[
                    { id: 'worktree', label: 'Working Tree', icon: FileCode },
                    { id: 'index', label: 'Staging Index', icon: Layers },
                    { id: 'local', label: 'Local .git DAG', icon: Database },
                    { id: 'remote', label: 'GitHub Remote', icon: Cloud }
                  ].map((zone) => {
                    const Icon = zone.icon;
                    const active = selectedCommand.zones.includes(zone.id);
                    return (
                      <div
                        key={zone.id}
                        className={`flex flex-col items-center justify-center p-2 rounded-xl border text-center transition-all ${
                          active
                            ? 'bg-emerald-50/90 border-emerald-300 text-emerald-900 shadow-2xs'
                            : 'bg-gray-50/70 border-gray-200/60 text-gray-400'
                        }`}
                      >
                        <Icon
                          className={`w-4 h-4 mb-1 ${
                            active ? 'text-emerald-600' : 'text-gray-400'
                          }`}
                        />
                        <span className="text-[10.5px] font-medium leading-tight">
                          {zone.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Multi-line Example & Pro-Tip */}
              <div className="bg-gray-50 rounded-xl p-2.5 border border-gray-200/80 font-mono text-[11.5px] text-gray-800 whitespace-pre-wrap mb-2">
                {selectedCommand.example}
              </div>
              <div className="flex items-start gap-2 text-[12px] text-blue-800 bg-blue-50/70 border border-blue-200/60 rounded-xl px-3 py-2">
                <Sparkles className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Engineering Rule:</strong> {selectedCommand.proTip}
                </span>
              </div>
            </div>
          )}

          {/* 2. ENCYCLOPEDIA / DECISION MATRIX / TROUBLESHOOTING TABS */}
          <div className="bg-white rounded-2xl border border-[#E4E4E7] shadow-xs overflow-hidden flex flex-col">
            {/* Top Mode Tabs */}
            <div className="flex items-center border-b border-gray-100 bg-gray-50/60 p-1.5 gap-1">
              <button
                onClick={() => setActiveRightTab('encyclopedia')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold transition ${
                  activeRightTab === 'encyclopedia'
                    ? 'bg-white text-gray-900 shadow-2xs border border-gray-200/60'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <BookOpen className="w-3.5 h-3.5 text-emerald-600" />
                <span>Encyclopedia (L0–L24)</span>
              </button>

              <button
                onClick={() => setActiveRightTab('decisions')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold transition ${
                  activeRightTab === 'decisions'
                    ? 'bg-white text-gray-900 shadow-2xs border border-gray-200/60'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <GitMerge className="w-3.5 h-3.5 text-blue-600" />
                <span>Decision Guide</span>
              </button>

              <button
                onClick={() => setActiveRightTab('troubleshoot')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold transition ${
                  activeRightTab === 'troubleshoot'
                    ? 'bg-white text-gray-900 shadow-2xs border border-gray-200/60'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <Wrench className="w-3.5 h-3.5 text-amber-600" />
                <span>Troubleshooting</span>
              </button>
            </div>

            {/* TAB 1: SEARCHABLE LEVEL 0-24 COMMAND ENCYCLOPEDIA */}
            {activeRightTab === 'encyclopedia' && (
              <div className="p-3.5 flex flex-col gap-3">
                {/* Search Input */}
                <div className="relative">
                  <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search 180+ commands (e.g. rebase --onto, reflog, bisect, gh pr, filter-repo)..."
                    className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-900 placeholder-gray-400 focus:outline-none focus:bg-white focus:border-blue-400"
                  />
                </div>

                {/* Level Filter Chips */}
                <div className="flex items-center gap-1 overflow-x-auto no-scrollbar pb-0.5">
                  {ENCYCLOPEDIA_LEVELS.map((lvl) => (
                    <button
                      key={lvl.id}
                      onClick={() => setSelectedLevelId(lvl.id)}
                      className={`shrink-0 px-2.5 py-1 rounded-lg text-[11px] font-medium transition ${
                        selectedLevelId === lvl.id
                          ? 'bg-gray-900 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {lvl.shortLabel}
                    </button>
                  ))}
                </div>

                {/* Command List */}
                <div className="flex flex-col gap-2 max-h-[390px] overflow-y-auto pr-1">
                  {filteredCommands.map((item) => {
                    const isSelected = selectedCommand?.id === item.id;
                    return (
                      <div
                        key={item.id}
                        onClick={() => setSelectedCommand(item)}
                        className={`group p-2.5 rounded-xl border transition-all cursor-pointer flex items-start justify-between gap-2 ${
                          isSelected
                            ? 'bg-blue-50/60 border-blue-300 shadow-2xs'
                            : 'bg-white hover:bg-gray-50 border-gray-200/80'
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-gray-100 text-gray-700 font-medium">
                              {item.levelBadge}
                            </span>
                            <code className="text-[12.5px] font-mono font-semibold text-gray-900 truncate">
                              {item.cmd}
                            </code>
                          </div>
                          <p className="text-[11.5px] text-gray-600 line-clamp-2">
                            {item.summary}
                          </p>
                        </div>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSimulateCommandOnGraph(item);
                          }}
                          className="shrink-0 px-2.5 py-1 rounded-lg bg-gray-900 hover:bg-emerald-600 text-white text-[11px] font-medium transition flex items-center gap-1"
                          title="Animate this command on the multi-lane branching graph"
                        >
                          <Play className="w-2.5 h-2.5" />
                          <span>Simulate</span>
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* TAB 2: COMMAND DECISION MATRIX (reset vs restore vs revert, merge vs rebase) */}
            {activeRightTab === 'decisions' && (
              <div className="p-3.5 flex flex-col gap-3.5 max-h-[470px] overflow-y-auto">
                {DECISION_GUIDES.map((guide, gIdx) => (
                  <div
                    key={gIdx}
                    className="border border-gray-200 rounded-xl p-3 bg-gray-50/50"
                  >
                    <h3 className="text-xs font-bold text-gray-900 mb-2">
                      {guide.title}
                    </h3>
                    <div className="flex flex-col gap-2">
                      {guide.items.map((it, iIdx) => (
                        <div
                          key={iIdx}
                          className="bg-white p-2.5 rounded-lg border border-gray-200/80 flex flex-col gap-1"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <code className="text-xs font-mono font-semibold text-blue-700">
                              {it.cmd}
                            </code>
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                              {it.badge}
                            </span>
                          </div>
                          <p className="text-[11.5px] text-gray-700">
                            {it.when}
                          </p>
                          <span className="text-[10.5px] text-gray-500 font-mono">
                            Rewrites history: {it.rewritesHistory}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* TAB 3: REAL-WORLD TROUBLESHOOTING RECIPES */}
            {activeRightTab === 'troubleshoot' && (
              <div className="p-3.5 flex flex-col gap-2.5 max-h-[470px] overflow-y-auto">
                {TROUBLESHOOTING_RECIPES.map((rec, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl border border-gray-200 bg-white flex flex-col gap-1.5"
                  >
                    <div className="flex items-center gap-1.5 text-red-700 font-mono text-xs font-semibold">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{rec.error}</span>
                    </div>
                    <p className="text-[11.5px] text-gray-600">{rec.cause}</p>
                    <div className="bg-gray-950 text-emerald-300 rounded-lg p-2 font-mono text-[11px]">
                      <div># Diagnose: {rec.diagnosis}</div>
                      <div className="text-white mt-0.5"># Fix: {rec.fix}</div>
                    </div>
                    <div className="text-[11px] text-amber-800 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200/60">
                      <strong>Warning:</strong> {rec.warning}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}