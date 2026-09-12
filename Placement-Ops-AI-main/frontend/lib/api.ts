import { supabase } from './supabase'
import type { Role } from './auth'

export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  (process.env.NODE_ENV === 'production' ? 'https://placement-ops-ai.onrender.com' : 'http://localhost:8000')

/**
 * Drop-in replacement for `fetch(`${BACKEND_URL}...`)` that attaches the
 * current Supabase session's access token as a Bearer header. The backend
 * now verifies this token on every protected route (see
 * backend/deps/supabase_auth.py) -- calls made without it will get a 401.
 */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession()

  const headers = new Headers(options.headers || {})
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`)
  }

  return fetch(`${BACKEND_URL}${path}`, { ...options, headers })
}

export type SyncedProfile =
  | { role: 'student'; profile_id: string; student_id: number; email: string; name: string; profile_complete: boolean }
  | { role: 'recruiter'; profile_id: string; email: string }
  | { role: 'tpo'; profile_id: string; email: string }

/**
 * Call once right after a successful Supabase sign-in/sign-up. Idempotent --
 * safe to call on every login. `role` is only honored the first time this
 * is ever called for this account; after that the backend's own
 * `profile_roles` record wins, so this call can't be used to change an
 * existing account's role.
 */
export async function syncProfile(role: Role): Promise<SyncedProfile> {
  const res = await apiFetch('/auth/sync-profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail?.detail || 'Failed to sync profile with backend.')
  }
  return res.json()
}
