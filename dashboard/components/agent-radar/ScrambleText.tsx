'use client';

import React, { useState, useEffect, useRef } from 'react';

const SCRAMBLE_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789_#@%&*';

interface ScrambleTextProps {
  text?: string;
  triggerKey?: string | number;
  duration?: number;
  preservePrefix?: number;
  className?: string;
}

export function ScrambleText({
  text = '',
  triggerKey,
  duration = 480,
  preservePrefix = 4,
  className = '',
}: ScrambleTextProps) {
  const [display, setDisplay] = useState(text);
  const prevKeyRef = useRef<string | number | undefined>(undefined);

  useEffect(() => {
    if (prevKeyRef.current === triggerKey) {
      setDisplay(text);
      return;
    }
    prevKeyRef.current = triggerKey;

    let frameId: number;
    const startTime = performance.now();

    const tick = (now: number) => {
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
          ch === '/' ||
          ch === '(' ||
          ch === ')' ||
          ch === '.' ||
          ch === '>'
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

