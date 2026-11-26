import { getToken } from 'next-auth/jwt';
import { NextRequest, NextResponse } from 'next/server';

const secret = process.env.NEXTAUTH_SECRET || 'fallback-secret-for-development-applypilot-2026';

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // 1. Allow public routes
  if (
    pathname === '/login' ||
    pathname.startsWith('/api/auth') ||
    pathname.startsWith('/api/stats') ||
    pathname.startsWith('/api/proofs') ||
    pathname.startsWith('/api/health') ||
    pathname.startsWith('/_next') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // 2. Validate session token
  const token = await getToken({ req, secret });

  const allowedEmails = (process.env.ALLOWED_EMAILS || 'sameerbagul2004@gmail.com')
    .split(',')
    .map((e) => e.trim().toLowerCase());

  const isAuthorized = Boolean(
    token?.email && allowedEmails.includes((token.email as string).toLowerCase())
  );

  if (!isAuthorized) {
    // For API requests, return JSON 401 Unauthorized
    if (pathname.startsWith('/api/')) {
      return NextResponse.json(
        { success: false, error: 'Unauthorized: Active workspace session required.' },
        { status: 401 }
      );
    }

    // For browser page navigation, redirect to login with callback destination
    const loginUrl = new URL('/login', req.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except static assets and media files
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};

