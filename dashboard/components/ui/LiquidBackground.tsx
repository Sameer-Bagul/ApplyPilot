'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { Grid3x3, Check, Sparkles, Circle, Sliders, Eye, EyeOff } from 'lucide-react';

export type BackgroundTheme =
  | 'dot_matrix_pearl'
  | 'dot_matrix_clean'
  | 'dot_matrix_blueprint'
  | 'dot_matrix_slate'
  | 'dot_matrix_dark';

export type DotDensity = 'dense' | 'standard' | 'wide';

export interface BackgroundOption {
  id: BackgroundTheme;
  name: string;
  desc: string;
  previewDots: string;
  isDark?: boolean;
}

export const BACKGROUND_OPTIONS: BackgroundOption[] = [
  {
    id: 'dot_matrix_pearl',
    name: 'Dot Grid & Pearl Spheres',
    desc: 'Crisp geometric dot matrix with floating 3D ceramic pearl spheres',
    previewDots: 'bg-slate-200 border-slate-300',
  },
  {
    id: 'dot_matrix_clean',
    name: 'Studio Precision Dot Grid',
    desc: 'Clean, distraction-free geometric dot grid on studio off-white canvas',
    previewDots: 'bg-white border-zinc-200',
  },
  {
    id: 'dot_matrix_blueprint',
    name: 'Technical Blueprint Dots',
    desc: 'Sharp technical indigo dot matrix on cool studio background',
    previewDots: 'bg-indigo-50 border-indigo-200',
  },
  {
    id: 'dot_matrix_slate',
    name: 'Slate Studio Horizon',
    desc: 'Sculptural minimal slate studio lighting with soft dot refraction',
    previewDots: 'bg-slate-300 border-slate-400',
  },
  {
    id: 'dot_matrix_dark',
    name: 'Onyx Dark Tech Grid',
    desc: 'Deep dark luxury studio with illuminated technical dot matrix',
    previewDots: 'bg-zinc-900 border-zinc-700',
    isDark: true,
  },
];

interface BackgroundContextType {
  currentTheme: BackgroundTheme;
  setTheme: (theme: BackgroundTheme) => void;
  dotDensity: DotDensity;
  setDotDensity: (density: DotDensity) => void;
  showSpheres: boolean;
  setShowSpheres: (show: boolean) => void;
  dotGrid: boolean;
  setDotGrid: (enabled: boolean) => void;
}

const BackgroundContext = createContext<BackgroundContextType>({
  currentTheme: 'dot_matrix_pearl',
  setTheme: () => {},
  dotDensity: 'standard',
  setDotDensity: () => {},
  showSpheres: true,
  setShowSpheres: () => {},
  dotGrid: true,
  setDotGrid: () => {},
});

export function BackgroundProvider({ children }: { children: React.ReactNode }) {
  const [currentTheme, setCurrentThemeState] = useState<BackgroundTheme>('dot_matrix_pearl');
  const [dotDensity, setDotDensityState] = useState<DotDensity>('standard');
  const [showSpheres, setShowSpheresState] = useState<boolean>(true);
  const [dotGrid, setDotGridState] = useState<boolean>(true);

  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem('applypilot_bg_theme') as BackgroundTheme;
      // Reset if legacy busy theme was stored or match valid theme
      if (
        savedTheme &&
        BACKGROUND_OPTIONS.some((o) => o.id === savedTheme) &&
        savedTheme !== ('ocean' as any) &&
        savedTheme !== ('silk' as any)
      ) {
        setCurrentThemeState(savedTheme);
      } else {
        setCurrentThemeState('dot_matrix_pearl');
        localStorage.setItem('applypilot_bg_theme', 'dot_matrix_pearl');
      }

      const savedDensity = localStorage.getItem('applypilot_dot_density') as DotDensity;
      if (savedDensity && ['dense', 'standard', 'wide'].includes(savedDensity)) {
        setDotDensityState(savedDensity);
      }

      const savedSpheres = localStorage.getItem('applypilot_show_spheres');
      if (savedSpheres !== null) {
        setShowSpheresState(savedSpheres === 'true');
      }

      const savedDots = localStorage.getItem('applypilot_dot_grid');
      if (savedDots !== null) {
        setDotGridState(savedDots === 'true');
      }
    } catch {
      // LocalStorage access fallback
    }
  }, []);

  const setTheme = (theme: BackgroundTheme) => {
    setCurrentThemeState(theme);
    try {
      localStorage.setItem('applypilot_bg_theme', theme);
    } catch {}
  };

  const setDotDensity = (density: DotDensity) => {
    setDotDensityState(density);
    try {
      localStorage.setItem('applypilot_dot_density', density);
    } catch {}
  };

  const setShowSpheres = (show: boolean) => {
    setShowSpheresState(show);
    try {
      localStorage.setItem('applypilot_show_spheres', String(show));
    } catch {}
  };

  const setDotGrid = (enabled: boolean) => {
    setDotGridState(enabled);
    try {
      localStorage.setItem('applypilot_dot_grid', String(enabled));
    } catch {}
  };

  return (
    <BackgroundContext.Provider
      value={{
        currentTheme,
        setTheme,
        dotDensity,
        setDotDensity,
        showSpheres,
        setShowSpheres,
        dotGrid,
        setDotGrid,
      }}
    >
      {children}
    </BackgroundContext.Provider>
  );
}

export function useBackground() {
  return useContext(BackgroundContext);
}

/**
 * Renders the full-screen dynamic backdrop behind all liquid glass panels.
 * Features crisp geometric dotted grid pattern and floating 3D ceramic pearl spheres.
 */
export function LiquidBackdrop() {
  const { currentTheme, dotDensity, showSpheres, dotGrid } = useBackground();
  const isDark = currentTheme === 'dot_matrix_dark';

  // Choose appropriate dot grid class
  let dotGridClass = 'dot-grid-pattern';
  if (currentTheme === 'dot_matrix_blueprint') {
    dotGridClass = 'dot-grid-blueprint';
  } else if (currentTheme === 'dot_matrix_dark') {
    dotGridClass = 'dot-grid-dark';
  } else if (dotDensity === 'dense') {
    dotGridClass = 'dot-grid-dense';
  } else if (dotDensity === 'wide') {
    dotGridClass = 'dot-grid-wide';
  }

  const renderSpheres = showSpheres && currentTheme !== 'dot_matrix_clean';

  return (
    <div
      className={`fixed inset-0 pointer-events-none overflow-hidden z-0 transition-colors duration-500 ${
        isDark
          ? 'bg-gradient-to-br from-[#0c0d14] via-[#111827] to-[#030712]'
          : currentTheme === 'dot_matrix_slate'
          ? 'bg-gradient-to-b from-[#e2e8f0] via-[#cbd5e1] to-[#94a3b8]'
          : 'bg-gradient-to-b from-[#ffffff] via-[#f7f8fb] to-[#eceff4]'
      }`}
      aria-hidden="true"
    >
      {/* 1. SOFT DIRECTIONAL STUDIO LIGHTING */}
      <div
        className={`absolute inset-0 transition-opacity duration-500 ${
          isDark
            ? 'bg-[radial-gradient(circle_at_50%_0%,rgba(30,41,59,0.5)_0%,transparent_70%)]'
            : 'bg-[radial-gradient(circle_at_50%_10%,rgba(255,255,255,0.9)_0%,transparent_65%)]'
        }`}
      />

      {/* 2. OPTICAL DOT MATRIX GRID (Crisp geometric dots that bend through glass edges) */}
      {dotGrid && (
        <div
          className={`absolute inset-0 ${dotGridClass} transition-all duration-300 ${
            isDark ? 'opacity-40' : 'opacity-70'
          }`}
        />
      )}

      {/* 3. 3D FLOATING CERAMIC PEARL SPHERES (From Reference Image 1) */}
      {renderSpheres && (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {/* Sphere 1: Top Right */}
          <div
            className={`absolute -top-20 right-[12%] w-72 h-72 lg:w-96 lg:h-96 rounded-full animate-float-subtle transition-all duration-700 ${
              isDark
                ? 'bg-gradient-to-br from-slate-700 via-slate-800 to-slate-950 shadow-2xl'
                : 'pearl-sphere'
            }`}
            style={{ animationDelay: '0s' }}
          />

          {/* Sphere 2: Mid-Right */}
          <div
            className={`absolute top-[36%] -right-16 w-56 h-56 lg:w-72 lg:h-72 rounded-full animate-float-reverse transition-all duration-700 ${
              isDark
                ? 'bg-gradient-to-br from-slate-700 via-slate-800 to-slate-950 shadow-2xl'
                : 'pearl-sphere'
            }`}
            style={{ animationDelay: '1.5s' }}
          />

          {/* Sphere 3: Bottom Right Giant */}
          <div
            className={`absolute -bottom-28 -right-12 w-96 h-96 lg:w-[480px] lg:h-[480px] rounded-full animate-float-subtle transition-all duration-700 ${
              isDark
                ? 'bg-gradient-to-br from-slate-700 via-slate-800 to-slate-950 shadow-2xl'
                : 'pearl-sphere'
            }`}
            style={{ animationDelay: '3s' }}
          />

          {/* Sphere 4: Bottom Left */}
          <div
            className={`absolute -bottom-10 left-[8%] w-64 h-64 lg:w-80 lg:h-80 rounded-full animate-float-reverse transition-all duration-700 ${
              isDark
                ? 'bg-gradient-to-br from-slate-700 via-slate-800 to-slate-950 shadow-2xl'
                : 'pearl-sphere'
            }`}
            style={{ animationDelay: '2s' }}
          />

          {/* Sphere 5: Mid/Top Left */}
          <div
            className={`absolute top-[18%] -left-14 w-48 h-48 lg:w-60 lg:h-60 rounded-full animate-float-subtle transition-all duration-700 ${
              isDark
                ? 'bg-gradient-to-br from-slate-700 via-slate-800 to-slate-950 shadow-2xl'
                : 'pearl-sphere'
            }`}
            style={{ animationDelay: '4s' }}
          />
        </div>
      )}

      {/* 4. SOFT READABILITY STUDIO MIST */}
      <div
        className={`absolute inset-0 pointer-events-none transition-colors duration-500 ${
          isDark
            ? 'bg-gradient-to-b from-transparent via-black/10 to-black/30'
            : 'bg-gradient-to-b from-white/10 via-white/5 to-white/20'
        }`}
      />
    </div>
  );
}

/**
 * Interactive Studio Dotted Grid & Backdrop Controller.
 */
export function WallpaperSwitcher() {
  const {
    currentTheme,
    setTheme,
    dotDensity,
    setDotDensity,
    showSpheres,
    setShowSpheres,
    dotGrid,
    setDotGrid,
  } = useBackground();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        title="Configure Studio Dotted Grid & Canvas"
        className="liquid-pill rounded-full px-3 py-1.5 sm:px-3.5 sm:py-2 flex items-center gap-2 text-xs font-semibold text-zinc-700 hover:text-zinc-950 transition-all cursor-pointer shadow-xs"
      >
        <Grid3x3 className="w-3.5 h-3.5 text-zinc-800" />
        <span className="hidden sm:inline">Grid Studio</span>
      </button>

      {isOpen && (
        <>
          {/* Backdrop dismissal overlay */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />

          {/* Configuration Popover */}
          <div className="absolute right-0 top-full mt-2 w-80 sm:w-88 liquid-glass-elevated rounded-3xl p-4 shadow-2xl z-50 animate-in fade-in zoom-in-95 duration-150 border border-white/95">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-200/60 mb-3">
              <div className="flex items-center gap-2">
                <Grid3x3 className="w-4 h-4 text-zinc-900" />
                <span className="text-xs font-bold text-zinc-900 tracking-tight">
                  Studio Grid & Backdrop
                </span>
              </div>
              <span className="text-[10px] font-mono text-zinc-400">Glass Optics</span>
            </div>

            {/* Presets List */}
            <div className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-1.5 px-1">
              Canvas Presets
            </div>
            <div className="flex flex-col gap-1.5 max-h-60 overflow-y-auto pr-1">
              {BACKGROUND_OPTIONS.map((opt) => {
                const isSelected = currentTheme === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => {
                      setTheme(opt.id);
                    }}
                    className={`liquid-row rounded-2xl p-2.5 flex items-center gap-3 text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'border-zinc-400 bg-white shadow-xs'
                        : 'hover:bg-white/90'
                    }`}
                  >
                    {/* Visual Dot Matrix Pattern Thumbnail */}
                    <div
                      className={`w-9 h-9 rounded-xl ${opt.previewDots} shrink-0 shadow-xs border flex items-center justify-center relative overflow-hidden`}
                    >
                      <div className="absolute inset-0 dot-grid-pattern opacity-60" />
                      {opt.id === 'dot_matrix_pearl' && (
                        <div className="w-4 h-4 rounded-full pearl-sphere shadow-xs relative z-10" />
                      )}
                    </div>

                    <div className="flex flex-col min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span
                          className={`text-xs font-semibold truncate ${
                            isSelected ? 'text-zinc-950 font-bold' : 'text-zinc-800'
                          }`}
                        >
                          {opt.name}
                        </span>
                        {isSelected && <Check className="w-3.5 h-3.5 text-zinc-900 shrink-0" />}
                      </div>
                      <span className="text-[10.5px] text-zinc-500 truncate leading-tight mt-0.5">
                        {opt.desc}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Dot Spacing Controls */}
            <div className="mt-3 pt-3 border-t border-zinc-200/60 flex items-center justify-between text-xs">
              <span className="text-zinc-600 font-medium text-[11px]">Grid Spacing:</span>
              <div className="flex items-center gap-1 bg-zinc-100 p-0.5 rounded-xl border border-zinc-200/60">
                {(
                  [
                    { id: 'dense', label: '18px' },
                    { id: 'standard', label: '26px' },
                    { id: 'wide', label: '34px' },
                  ] as const
                ).map((d) => (
                  <button
                    key={d.id}
                    onClick={() => setDotDensity(d.id)}
                    className={`px-2 py-0.5 text-[10.5px] font-semibold rounded-lg transition-all cursor-pointer ${
                      dotDensity === d.id
                        ? 'bg-white text-zinc-950 shadow-xs'
                        : 'text-zinc-500 hover:text-zinc-900'
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 3D Pearl Spheres Toggle */}
            <div className="mt-2.5 pt-2.5 border-t border-zinc-200/60 flex items-center justify-between text-xs">
              <span className="text-zinc-600 font-medium text-[11px]">3D Pearl Spheres:</span>
              <button
                onClick={() => setShowSpheres(!showSpheres)}
                className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  showSpheres
                    ? 'bg-zinc-900 text-white shadow-xs'
                    : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
                }`}
              >
                {showSpheres ? (
                  <>
                    <Eye className="w-3 h-3" />
                    <span>Visible</span>
                  </>
                ) : (
                  <>
                    <EyeOff className="w-3 h-3" />
                    <span>Hidden</span>
                  </>
                )}
              </button>
            </div>

            {/* Dot Matrix Grid Toggle */}
            <div className="mt-2.5 pt-2.5 border-t border-zinc-200/60 flex items-center justify-between text-xs">
              <span className="text-zinc-600 font-medium text-[11px]">Dotted Matrix:</span>
              <button
                onClick={() => setDotGrid(!dotGrid)}
                className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition-all cursor-pointer ${
                  dotGrid
                    ? 'bg-zinc-900 text-white shadow-xs'
                    : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
                }`}
              >
                {dotGrid ? 'Enabled' : 'Disabled'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
