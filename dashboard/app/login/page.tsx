'use client';

import React, { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { LandingPage } from '@/components/LandingPage';

function LoginContent() {
  const searchParams = useSearchParams();
  const errorParam = searchParams.get('error');

  let errorMessage: string | null = null;
  if (errorParam === 'AccessDenied') {
    errorMessage = 'Access Denied: Your Google account is not on the whitelist. Strictly restricted to sameerbagul2004@gmail.com.';
  } else if (errorParam === 'CredentialsSignin') {
    errorMessage = 'Invalid admin passcode or unauthorized email. Please check your credentials.';
  } else if (errorParam) {
    errorMessage = `Authentication error: ${errorParam}`;
  }

  return <LandingPage error={errorMessage} />;
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-xs text-zinc-400">Loading portal...</div>}>
      <LoginContent />
    </Suspense>
  );
}

