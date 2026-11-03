'use client';

import React, { useEffect, useRef, ReactNode } from 'react';

export interface LiquidGlassOptions {
  refraction?: number;
  bezel?: number;
  curvature?: number;
  ior?: number;
  invert?: boolean;
  chroma?: number;
  blur?: number;
  specular?: number;
  specularWidth?: number;
  lightAngle?: number;
  fit?: boolean;
  clip?: boolean;
  mode?: 'backdrop' | 'surface';
  fallback?: string;
}

/**
 * React hook to attach true Liquid Glass refraction to an element.
 * Zero-dependency displacement map engine from liquidglass.dev.
 */
export function useLiquidGlass(options: LiquidGlassOptions = {}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const glassRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !ref.current) return;

    let destroyed = false;

    import('@/lib/liquid-glass.js').then(({ createGlass }) => {
      if (destroyed || !ref.current) return;
      try {
        glassRef.current = createGlass(ref.current, {
          fit: true,
          refraction: options.refraction ?? 20,
          bezel: options.bezel ?? 0.35,
          curvature: options.curvature ?? 4,
          chroma: options.chroma ?? 0.12,
          specular: options.specular ?? 0.55,
          specularWidth: options.specularWidth ?? 2,
          lightAngle: options.lightAngle ?? -120,
          mode: options.mode ?? 'backdrop',
          fallback: options.fallback ?? 'blur(24px) saturate(1.8)',
          ...options,
        });
      } catch (err) {
        console.warn('Liquid glass initialization notice:', err);
      }
    });

    return () => {
      destroyed = true;
      if (glassRef.current && typeof glassRef.current.destroy === 'function') {
        glassRef.current.destroy();
      }
    };
  }, []);

  return ref;
}

interface LiquidCardProps {
  children: ReactNode;
  className?: string;
  elevated?: boolean;
  interactive?: boolean;
  onClick?: () => void;
}

/**
 * True Liquid Glass card container.
 * Features specular top rim highlight, optical refraction sheen, and depth shadow.
 */
export function LiquidCard({
  children,
  className = '',
  elevated = false,
  interactive = false,
  onClick,
}: LiquidCardProps) {
  const cardClass = elevated
    ? 'liquid-glass-elevated'
    : 'liquid-glass';

  const interactiveClass = interactive
    ? 'hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300 cursor-pointer'
    : '';

  return (
    <div
      onClick={onClick}
      className={`relative rounded-3xl p-6 ${cardClass} ${interactiveClass} ${className}`}
    >
      {/* Specular light highlight on top rim */}
      <div
        className="absolute inset-x-0 top-0 h-[1.5px] rounded-t-3xl bg-gradient-to-r from-transparent via-white/90 to-transparent pointer-events-none z-10"
        aria-hidden="true"
      />
      {/* Inner ambient glow */}
      <div
        className="absolute inset-0 rounded-3xl bg-gradient-to-b from-white/30 to-transparent pointer-events-none"
        aria-hidden="true"
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
}

/**
 * Auto-registers liquidglass.dev Web Components (<lg-switch>, <lg-slider>, <lg-segmented>, etc.)
 */
export function LiquidGlassInit() {
  useEffect(() => {
    if (typeof window !== 'undefined') {
      import('@/lib/components.js').catch((err) => {
        console.warn('Could not register liquid glass components:', err);
      });
    }
  }, []);

  return null;
}
