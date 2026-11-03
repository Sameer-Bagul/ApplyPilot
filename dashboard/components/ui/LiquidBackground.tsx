'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { Palette, Sparkles, Check, Image as ImageIcon } from 'lucide-react';

export type BackgroundTheme =
  | 'ocean'
  | 'silk'
  | 'pearl_matrix'
  | 'sky_ribbon'
  | 'slate_slabs'
  | 'sunset_mesh';

export interface BackgroundOption {
  id: BackgroundTheme;
  name: string;
  desc: string;
  previewColor: string;
  imageSrc?: string;
  hasDotGrid?: boolean;
}

export const BACKGROUND_OPTIONS: BackgroundOption[] = [
  {
    id: 'ocean',
    name: 'VisionOS Ocean Ribbon',
    desc: 'Dynamic cobalt blue & sapphire silk ribbons with specular refraction',
    previewColor: 'from-blue-600 to-cyan-400',
    imageSrc: '/backgrounds/ocean_ribbon_artwork.jpg',
    hasDotGrid: true,
  },
  {
    id: 'silk',
    name: 'Liquid Silk & Spheres',
    desc: '3D multi-color fluid ribbons in cobalt, peach, rose, and lilac',
    previewColor: 'from-purple-500 via-rose-400 to-amber-300',
    imageSrc: '/backgrounds/liquid_glass_artwork.jpg',
    hasDotGrid: true,
  },
  {
    id: 'pearl_matrix',
    name: 'Pearl Spheres & Matrix',
    desc: 'Minimalist 3D ceramic spheres with geometric dot refraction grid',
    previewColor: 'from-zinc-300 to-zinc-100',
    imageSrc: '/backgrounds/user_pearl_matrix.png',
    hasDotGrid: true,
  },
  {
    id: 'sky_ribbon',
    name: 'Sky Blue Waves',
    desc: 'Vibrant azure fluid waves behind frosted glass',
    previewColor: 'from-sky-400 to-blue-600',
    imageSrc: '/backgrounds/user_sky_ribbon.jpg',
    hasDotGrid: true,
  },
  {
    id: 'slate_slabs',
    name: 'Slate Glass Studio',
    desc: 'Sculptural minimal glass slabs with soft ambient rim light',
    previewColor: 'from-slate-400 to-slate-200',
    imageSrc: '/backgrounds/user_slate_slabs.png',
    hasDotGrid: false,
  },
  {
    id: 'sunset_mesh',
    name: 'Sunset Ambient Mesh',
    desc: 'Soft ethereal glowing pastel spheres with smooth gradient lighting',
    previewColor: 'from-rose-300 via-purple-300 to-amber-200',
    hasDotGrid: true,
  },
];

interface BackgroundContextType {
  currentTheme: BackgroundTheme;
  setTheme: (theme: BackgroundTheme) => void;
  dotGrid: boolean;
  setDotGrid: (enabled: boolean) => void;
}

const BackgroundContext = createContext<BackgroundContextType>({
  currentTheme: 'ocean',
  setTheme: () => {},
  dotGrid: true,
  setDotGrid: () => {},
});

export function BackgroundProvider({ children }: { children: React.ReactNode }) {
  const [currentTheme, setCurrentThemeState] = useState<BackgroundTheme>('ocean');
  const [dotGrid, setDotGridState] = useState<boolean>(true);

  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem('applypilot_bg_theme') as BackgroundTheme;
      if (savedTheme && BACKGROUND_OPTIONS.some((o) => o.id === savedTheme)) {
        setCurrentThemeState(savedTheme);
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

  const setDotGrid = (enabled: boolean) => {
    setDotGridState(enabled);
    try {
      localStorage.setItem('applypilot_dot_grid', String(enabled));
    } catch {}
  };

  return (
    <BackgroundContext.Provider value={{ currentTheme, setTheme, dotGrid, setDotGrid }}>
      {children}
    </BackgroundContext.Provider>
  );
}

export function useBackground() {
  return useContext(BackgroundContext);
}

/**
 * Renders the full-screen dynamic backdrop behind all liquid glass panels.
 */
export function LiquidBackdrop() {
  const { currentTheme, dotGrid } = useBackground();
  const activeOption = BACKGROUND_OPTIONS.find((o) => o.id === currentTheme) || BACKGROUND_OPTIONS[0];

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
      {/* 1. PHOTO/ARTWORK BACKDROP LAYER */}
      {activeOption.imageSrc && (
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat transition-all duration-700 ease-out"
          style={{
            backgroundImage: `url(${activeOption.imageSrc})`,
            opacity: 0.92,
          }}
        />
      )}

      {/* 2. ATMOSPHERIC GLOW SPHERES (Always active for ethereal depth) */}
      <div className="absolute top-[-10%] left-[-5%] w-[650px] h-[650px] rounded-full bg-gradient-to-br from-[#FFD1B3]/35 via-[#FF8C82]/25 to-transparent blur-[130px] opacity-75" />
      <div className="absolute top-[20%] right-[-10%] w-[750px] h-[750px] rounded-full bg-gradient-to-bl from-[#DDD6FE]/40 via-[#FBCFE8]/30 to-transparent blur-[150px] opacity-75" />
      <div className="absolute bottom-[-15%] left-[20%] w-[800px] h-[800px] rounded-full bg-gradient-to-tr from-[#C7D2FE]/30 via-[#E0E7FF]/20 to-transparent blur-[160px] opacity-70" />
      <div className="absolute bottom-[20%] right-[10%] w-[550px] h-[550px] rounded-full bg-gradient-to-tl from-[#A7F3D0]/25 via-[#BAE6FD]/20 to-transparent blur-[140px] opacity-70" />

      {/* 3. OPTICAL DOT MATRIX GRID (Refracts and bends through glass edges like in Image 1) */}
      {dotGrid && (
        <div
          className="absolute inset-0 opacity-[0.24] transition-opacity duration-300"
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(15, 23, 42, 0.45) 1.25px, transparent 1.25px)',
            backgroundSize: '24px 24px',
          }}
        />
      )}

      {/* 4. SOFT READABILITY MIST SCRIM (Ensures dark text and tables are 100% sharp) */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/25 via-white/10 to-white/30 backdrop-blur-[0.5px]" />
    </div>
  );
}

/**
 * Interactive Wallpaper Switcher Button and Popover.
 */
export function WallpaperSwitcher() {
  const { currentTheme, setTheme, dotGrid, setDotGrid } = useBackground();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        title="Change Liquid Glass Wallpaper"
        className="liquid-pill rounded-full px-3 py-1.5 sm:px-3.5 sm:py-2 flex items-center gap-2 text-xs font-semibold text-zinc-700 hover:text-zinc-950 transition-all cursor-pointer shadow-xs"
      >
        <Sparkles className="w-3.5 h-3.5 text-purple-600" />
        <span className="hidden sm:inline">Wallpaper</span>
      </button>

      {isOpen && (
        <>
          {/* Backdrop dismissal overlay */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />

          {/* Wallpaper Selection Popover */}
          <div className="absolute right-0 top-full mt-2 w-72 sm:w-80 liquid-glass-elevated rounded-3xl p-4 shadow-2xl z-50 animate-in fade-in zoom-in-95 duration-150 border border-white/95">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-200/60 mb-3">
              <div className="flex items-center gap-2">
                <Palette className="w-4 h-4 text-purple-600" />
                <span className="text-xs font-bold text-zinc-900 tracking-tight">
                  Liquid Glass Backdrops
                </span>
              </div>
              <span className="text-[10px] font-mono text-zinc-400">VisionOS Optic</span>
            </div>

            <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-1">
              {BACKGROUND_OPTIONS.map((opt) => {
                const isSelected = currentTheme === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => {
                      setTheme(opt.id);
                      setIsOpen(false);
                    }}
                    className={`liquid-row rounded-2xl p-2.5 flex items-center gap-3 text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'border-purple-300/80 bg-white shadow-xs'
                        : 'hover:bg-white/90'
                    }`}
                  >
                    {/* Visual Color Pill Preview */}
                    <div
                      className={`w-9 h-9 rounded-xl bg-gradient-to-tr ${opt.previewColor} shrink-0 shadow-sm border border-white/80 overflow-hidden relative`}
                    >
                      {opt.imageSrc && (
                        <div
                          className="absolute inset-0 bg-cover bg-center"
                          style={{ backgroundImage: `url(${opt.imageSrc})` }}
                        />
                      )}
                    </div>

                    <div className="flex flex-col min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-semibold truncate ${isSelected ? 'text-zinc-950' : 'text-zinc-800'}`}>
                          {opt.name}
                        </span>
                        {isSelected && <Check className="w-3.5 h-3.5 text-purple-600 shrink-0" />}
                      </div>
                      <span className="text-[10.5px] text-zinc-500 truncate leading-tight mt-0.5">
                        {opt.desc}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Dot Matrix Grid Toggle */}
            <div className="mt-3 pt-3 border-t border-zinc-200/60 flex items-center justify-between text-xs">
              <span className="text-zinc-600 font-medium text-[11px]">Refraction Dot Matrix:</span>
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
