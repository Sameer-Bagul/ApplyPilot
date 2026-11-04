'use client';

import React, { Suspense } from 'react';
import DashboardPage from '../page';

export default function RadarPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-xs text-zinc-400">Loading Agent Radar...</div>}>
      <DashboardPage initialTab="radar" />
    </Suspense>
  );
}
