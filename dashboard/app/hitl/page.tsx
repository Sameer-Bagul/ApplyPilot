'use client';

import React, { Suspense } from 'react';
import DashboardPage from '../page';

export default function HitlPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-xs text-zinc-400">Loading Safety Tickets...</div>}>
      <DashboardPage initialTab="hitl" />
    </Suspense>
  );
}
