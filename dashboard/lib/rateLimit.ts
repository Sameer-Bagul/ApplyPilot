/**
 * Production In-Memory Sliding-Window Rate Limiter
 * Zero external dependencies. Designed for Next.js App Router API endpoints.
 */

interface RateLimitRecord {
  timestamps: number[];
}

const rateLimitMap = new Map<string, RateLimitRecord>();

// Clean up stale entries every 5 minutes to prevent memory leaks
if (typeof setInterval !== 'undefined') {
  setInterval(() => {
    const now = Date.now();
    for (const [key, record] of rateLimitMap.entries()) {
      record.timestamps = record.timestamps.filter((ts) => now - ts < 60000);
      if (record.timestamps.length === 0) {
        rateLimitMap.delete(key);
      }
    }
  }, 300000);
}

export interface RateLimitOptions {
  intervalMs?: number; // Time window (default: 60,000ms = 1 minute)
  maxRequests?: number; // Max requests within window (default: 30)
}

export interface RateLimitResult {
  success: boolean;
  limit: number;
  remaining: number;
  resetMs: number;
}

export function checkRateLimit(
  identifier: string,
  options: RateLimitOptions = {}
): RateLimitResult {
  const intervalMs = options.intervalMs || 60000;
  const maxRequests = options.maxRequests || 30;
  const now = Date.now();

  let record = rateLimitMap.get(identifier);
  if (!record) {
    record = { timestamps: [] };
    rateLimitMap.set(identifier, record);
  }

  // Filter timestamps within current window
  record.timestamps = record.timestamps.filter((ts) => now - ts < intervalMs);

  if (record.timestamps.length >= maxRequests) {
    const oldest = record.timestamps[0];
    const resetMs = Math.max(0, intervalMs - (now - oldest));
    return {
      success: false,
      limit: maxRequests,
      remaining: 0,
      resetMs,
    };
  }

  record.timestamps.push(now);
  return {
    success: true,
    limit: maxRequests,
    remaining: maxRequests - record.timestamps.length,
    resetMs: intervalMs,
  };
}

export function getClientIp(request: Request): string {
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  const realIp = request.headers.get('x-real-ip');
  if (realIp) {
    return realIp.trim();
  }
  return '127.0.0.1';
}
