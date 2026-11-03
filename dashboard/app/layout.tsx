import type { Metadata } from 'next';
import './globals.css';

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
      <body className="antialiased selection:bg-rose-100 selection:text-rose-900">
        {/* Soft atmospheric background glow spheres */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
          <div className="absolute top-[-10%] left-[-5%] w-[600px] h-[600px] rounded-full bg-rose-200/30 blur-[130px]" />
          <div className="absolute top-[20%] right-[-10%] w-[700px] h-[700px] rounded-full bg-amber-100/35 blur-[150px]" />
          <div className="absolute bottom-[-10%] left-[20%] w-[800px] h-[800px] rounded-full bg-indigo-100/30 blur-[160px]" />
          <div className="absolute bottom-[20%] right-[10%] w-[500px] h-[500px] rounded-full bg-emerald-100/25 blur-[140px]" />
        </div>

        <div className="relative z-10 min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}

