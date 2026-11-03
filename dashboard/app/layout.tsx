import type { Metadata } from 'next';
import './globals.css';
import { LiquidGlassInit } from '@/components/ui/LiquidGlass';
import { BackgroundProvider, LiquidBackdrop } from '@/components/ui/LiquidBackground';

export const metadata: Metadata = {
  title: 'ApplyPilot | Autonomous Job Intelligence & Acquisition',
  description: 'Minimalist iOS liquid-glass dashboard for job discovery, company watchlists, and recruiter outreach.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-rose-100 selection:text-rose-900 bg-[#F4F4F8]">
        <LiquidGlassInit />
        <BackgroundProvider>
          {/* Dynamic Liquid Glass Artwork & Lighting Backdrop */}
          <LiquidBackdrop />

          <div className="relative z-10 min-h-screen">
            {children}
          </div>
        </BackgroundProvider>
      </body>
    </html>
  );
}
