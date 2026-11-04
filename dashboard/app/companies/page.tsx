'use client';

import React, { Suspense } from 'react';
import DashboardPage from '../page';

export default function CompaniesPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-xs text-zinc-400">Loading Companies Watchlist...</div>}>
      <DashboardPage initialTab="companies" />
    </Suspense>
  );
}
