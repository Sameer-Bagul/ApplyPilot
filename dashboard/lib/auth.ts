import type { AuthOptions } from 'next-auth';
import { getServerSession } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import CredentialsProvider from 'next-auth/providers/credentials';

export const authOptions: AuthOptions = {
  secret: process.env.NEXTAUTH_SECRET || 'fallback-secret-for-development-applypilot-2026',
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  cookies: {
    sessionToken: {
      name: process.env.NODE_ENV === 'production' ? '__Secure-next-auth.session-token' : 'next-auth.session-token',
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
  },
  providers: [
    ...(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
      ? [
          GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
          }),
        ]
      : []),
    CredentialsProvider({
      id: 'credentials',
      name: 'Admin Passcode',
      credentials: {
        passcode: { label: 'Admin Passcode', type: 'password' },
        email: { label: 'Account Email', type: 'email' },
      },
      async authorize(credentials) {
        const expectedPasscode = process.env.ADMIN_PASSCODE || 'sameer2004';
        const candidatePasscode = credentials?.passcode?.trim();
        const candidateEmail = credentials?.email?.trim().toLowerCase() || 'sameerbagul2004@gmail.com';

        if (candidatePasscode === expectedPasscode) {
          const allowedEmails = (process.env.ALLOWED_EMAILS || 'sameerbagul2004@gmail.com')
            .split(',')
            .map((e) => e.trim().toLowerCase());

          if (allowedEmails.includes(candidateEmail)) {
            return {
              id: 'sameer-owner-01',
              name: 'Sameer Bagul',
              email: candidateEmail,
              image: 'https://avatar.vercel.sh/sameerbagul2004',
            };
          }
        }
        return null;
      },
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      const allowedEmails = (process.env.ALLOWED_EMAILS || 'sameerbagul2004@gmail.com')
        .split(',')
        .map((e) => e.trim().toLowerCase());

      const email = user.email?.trim().toLowerCase();
      if (email && allowedEmails.includes(email)) {
        return true;
      }

      console.warn(`[ApplyPilot Security] Unauthorized sign-in attempt rejected for: ${email}`);
      return false;
    },
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.email = user.email;
        token.name = user.name;
        token.picture = user.image;
        token.role = 'owner';
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.email = token.email as string;
        session.user.name = token.name as string;
        session.user.image = token.picture as string;
        (session.user as any).role = token.role || 'owner';
      }
      return session;
    },
  },
  pages: {
    signIn: '/login',
    error: '/login',
  },
};

/**
 * Helper to retrieve the active server session in Server Components and API Routes
 */
export async function getServerAuth() {
  return await getServerSession(authOptions);
}

/**
 * Guard utility for API routes and Server Actions
 */
export async function requireApiAuth() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) {
    return { authorized: false, session: null, error: 'Unauthorized: No active session' };
  }
  const allowedEmails = (process.env.ALLOWED_EMAILS || 'sameerbagul2004@gmail.com')
    .split(',')
    .map((e) => e.trim().toLowerCase());
  const userEmail = session.user.email.toLowerCase().trim();
  if (!allowedEmails.includes(userEmail)) {
    return { authorized: false, session, error: 'Forbidden: Account is not authorized' };
  }
  return { authorized: true, session, error: null };
}

