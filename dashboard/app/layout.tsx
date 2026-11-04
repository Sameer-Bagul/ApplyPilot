import type { Metadata } from 'next';
import './globals.css';
import { LiquidGlassInit } from '@/components/ui/LiquidGlass';
import { BackgroundProvider, LiquidBackdrop } from '@/components/ui/LiquidBackground';
import { AuthProvider } from '@/components/AuthProvider';

export const metadata: Metadata = {
  title: 'ApplyPilot | Autonomous Job Intelligence & Acquisition Studio',
  description: 'Minimalist iOS liquid-glass workspace for autonomous job discovery, multi-agent evaluation, and high-conversion recruiter outreach.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-rose-100 selection:text-rose-900 bg-[#F4F4F8]">
        <AuthProvider>
          <LiquidGlassInit />
          <BackgroundProvider>
            {/* Dynamic Liquid Glass Artwork & Lighting Backdrop */}
            <LiquidBackdrop />

            <div className="relative z-10 min-h-screen">
              {children}
            </div>
          </BackgroundProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
