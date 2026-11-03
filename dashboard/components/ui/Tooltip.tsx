'use client';

import React, { ReactNode } from 'react';

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

export function Tooltip({
  content,
  children,
  position = 'top',
  className = '',
}: TooltipProps) {
  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <div className={`relative inline-flex items-center group/tooltip ${className}`}>
      {children}
      <div
        className={`absolute ${positionClasses[position]} opacity-0 invisible group-hover/tooltip:opacity-100 group-hover/tooltip:visible transition-all duration-200 ease-out pointer-events-none z-50 max-w-xs w-max`}
      >
        <div className="liquid-glass rounded-xl px-3 py-2 text-xs text-zinc-800 shadow-xl border border-white/90 backdrop-blur-xl flex flex-col gap-0.5 leading-snug">
          {content}
        </div>
      </div>
    </div>
  );
}

