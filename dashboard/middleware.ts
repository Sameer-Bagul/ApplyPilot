import { withAuth } from 'next-auth/middleware';
import { NextResponse } from 'next/server';

export default withAuth(
  function middleware(req) {
    return NextResponse.next();
  },
  {
    callbacks: {
      authorized({ req, token }) {
        const { pathname } = req.nextUrl;

        // Publicly accessible paths: landing/login, next-auth handlers, public platform stats, and proof media
        if (
          pathname === '/login' ||
          pathname.startsWith('/api/auth') ||
          pathname.startsWith('/api/stats') ||
          pathname.startsWith('/api/proofs') ||
          pathname.startsWith('/_next') ||
          pathname.includes('.')
        ) {
          return true;
        }

        // Check if token exists and belongs to whitelisted email
        if (!token?.email) {
          return false;
        }

        const allowedEmails = (process.env.ALLOWED_EMAILS || 'sameerbagul2004@gmail.com')
          .split(',')
          .map((e) => e.trim().toLowerCase());

        return allowedEmails.includes((token.email as string).toLowerCase());
      },
    },
    pages: {
      signIn: '/login',
    },
  }
);

export const config = {
  matcher: [
    /*
     * Protect dashboard subroutes and mutations:
     * Matches all paths except static assets, favicon, etc.
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};

