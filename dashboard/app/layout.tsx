import type { Metadata } from 'next';
import './globals.css';
import { LiquidGlassInit } from '@/components/ui/LiquidGlass';

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
      <body className="antialiased selection:bg-rose-100 selection:text-rose-900 bg-[#F7F6F9]">
        <LiquidGlassInit />
        {/* Ethereal atmospheric background glow spheres from liquidglass.dev & iOS liquid glass */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
          <div className="absolute top-[-12%] left-[-8%] w-[680px] h-[680px] rounded-full bg-gradient-to-br from-[#FFD1B3]/45 via-[#FF8C82]/35 to-transparent blur-[140px]" />
          <div className="absolute top-[18%] right-[-10%] w-[750px] h-[750px] rounded-full bg-gradient-to-bl from-[#DDD6FE]/40 via-[#FBCFE8]/30 to-transparent blur-[160px]" />
          <div className="absolute bottom-[-15%] left-[15%] w-[850px] h-[850px] rounded-full bg-gradient-to-tr from-[#C7D2FE]/35 via-[#E0E7FF]/25 to-transparent blur-[170px]" />
          <div className="absolute bottom-[25%] right-[8%] w-[580px] h-[580px] rounded-full bg-gradient-to-tl from-[#A7F3D0]/30 via-[#BAE6FD]/25 to-transparent blur-[150px]" />
        </div>

        <div className="relative z-10 min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}

