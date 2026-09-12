import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Intentionally a no-op today. Real authorization happens in two places:
 *   1. The backend verifies the Supabase JWT and enforces role on every
 *      protected route (see backend/deps/supabase_auth.py).
 *   2. Each client page checks for a Supabase session on mount and
 *      redirects if missing (see app/page.tsx, app/profile/page.tsx).
 *
 * This file exists as the extension point for server-side redirects (e.g.
 * cookie-based session checks) if that's added later -- there is currently
 * no cookie-based session to check, so there's nothing for it to do yet.
 */
export function middleware(_request: NextRequest) {
  return NextResponse.next()
}

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
