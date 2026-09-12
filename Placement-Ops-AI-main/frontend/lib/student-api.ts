import { apiFetch, syncProfile, BACKEND_URL } from './api'

export interface StudentProfile {
  id: number
  profile_id: string | null
  name: string
  email: string
  branch: string
  cgpa: number
  tenth_pct: number
  twelfth_pct: number
  semester_marks: Record<string, number>
  backlog_count: number
  skills: { skill: string; level: string }[]
  certifications: { name: string; issuer: string }[]
  projects: { title: string; tech_stack: string[]; description?: string; link?: string }[]
  internship_history: { company: string; duration_months: number; role?: string }[]
  hackathons: { name: string; result?: string }[]
  current_best_offer: number | null
  applied_drives: number[]
  profile_photo_url: string | null
  resume_url: string | null
  resume_filename: string | null
  github_url: string | null
  linkedin_url: string | null
  portfolio_url: string | null
  coding_profiles: { leetcode?: string; codeforces?: string; hackerrank?: string }
  preferred_roles: string[]
  expected_salary: number | null
  location_preference: string[]
  languages: string[]
  resume_ats_score: number | null
  api_score: number
  ssi_score: number
  prs_score: number
  profile_completion_pct: number
}

export type StudentProfileUpdate = Partial<
  Omit<
    StudentProfile,
    | 'id'
    | 'profile_id'
    | 'email'
    | 'current_best_offer'
    | 'applied_drives'
    | 'profile_photo_url'
    | 'resume_url'
    | 'resume_filename'
    | 'resume_ats_score'
    | 'api_score'
    | 'ssi_score'
    | 'prs_score'
    | 'profile_completion_pct'
  >
>

/** Translate an HTTP response into a meaningful error. Never throws a raw
 *  "Failed to fetch" — that only happens at the network level and is caught
 *  by the wrapFetch() helper below. */
async function handle<T>(res: Response): Promise<T> {
  if (res.ok) return res.json()

  let detail = ''
  try { detail = (await res.json())?.detail ?? '' } catch {}

  switch (res.status) {
    case 401:
      throw new Error(
        detail || 'Not authenticated. Please log in with a real account to access your profile.'
      )
    case 403:
      throw new Error(
        detail ||
          'No student profile is linked to this account. ' +
          'Make sure you signed up as a Student and call /auth/sync-profile first.'
      )
    case 404:
      throw new Error(detail || 'Profile not found on the server.')
    case 422:
      throw new Error(detail || `Validation error (${res.status}).`)
    case 500:
      throw new Error(detail || 'Internal server error. Check backend logs.')
    default:
      throw new Error(detail || `Server returned ${res.status}.`)
  }
}

/** Wraps apiFetch so that a network-level failure (backend unreachable,
 *  CORS pre-flight blocked, DNS failure) becomes a clear user-facing message
 *  instead of the raw browser "TypeError: Failed to fetch". */
async function safeFetch(path: string, options?: RequestInit, retryOnSync = true): Promise<Response> {
  try {
    const res = await apiFetch(path, options)
    if (res.status === 403 && retryOnSync) {
      let detail = ''
      try {
        const cloned = res.clone()
        detail = (await cloned.json())?.detail ?? ''
      } catch {}
      
      if (detail.includes('sync-profile') || detail.includes('No profile on file')) {
        try {
          await syncProfile('student')
          return await safeFetch(path, options, false)
        } catch (syncErr) {
          console.warn('Auto-sync failed in safeFetch:', syncErr)
        }
      }
    }
    return res
  } catch (err: any) {
    // TypeError is what browsers throw when fetch itself can't reach the server
    if (err instanceof TypeError) {
      throw new Error(
        `Backend server is unreachable (${path}). ` +
        `Make sure the FastAPI server is running at ${BACKEND_URL}.`
      )
    }
    throw err
  }
}

export async function getMyProfile(): Promise<StudentProfile> {
  return handle(await safeFetch('/students/me'))
}

export async function updateMyProfile(updates: StudentProfileUpdate): Promise<StudentProfile> {
  return handle(
    await safeFetch('/students/me', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
  )
}

export async function uploadMyResume(file: File): Promise<{ resume_url: string; resume_filename: string }> {
  const formData = new FormData()
  formData.append('file', file)
  // Note: don't set Content-Type manually -- the browser needs to set the
  // multipart boundary itself. apiFetch only adds the Authorization header.
  return handle(await safeFetch('/students/me/resume', { method: 'POST', body: formData }))
}

export interface ExtractedProfileData {
  name?: string
  email?: string
  phone?: string
  branch?: string
  cgpa?: number
  tenth_pct?: number
  twelfth_pct?: number
  linkedin_url?: string
  github_url?: string
  portfolio_url?: string
  skills?: { skill: string; level: string }[]
  projects?: { title: string; tech_stack: string[]; description?: string; link?: string }[]
  certifications?: { name: string; issuer: string }[]
  internship_history?: { company: string; role?: string; duration_months: number }[]
  hackathons?: { name: string; result?: string }[]
  preferred_roles?: string[]
  languages?: string[]
  source?: 'huggingface' | 'heuristic'
}

export async function extractProfileFromResume(): Promise<ExtractedProfileData> {
  return handle(await safeFetch('/students/me/resume/extract', { method: 'POST' }))
}

export interface DashboardJob {
  drive_id: number
  company_name: string
  role_title: string
  package_min: number
  package_max: number
  location: string | null
  status?: string
  match_pct?: number | null
}

export interface DashboardInterview {
  interview_id: number
  drive_id: number
  company_name: string | null
  time_slot: string
  room_or_link: string | null
  panel_members: string[]
}

export interface DashboardNotification {
  id: number
  message: string
  sent_at: string
  delivery_status: string
}

export interface DashboardActivity {
  action: string
  target_type: string
  details: string | null
  timestamp: string
}

export interface StudentDashboardData {
  profile: {
    name: string
    branch: string
    cgpa: number
    placement_readiness_score: number
    profile_completion_pct: number
    resume_ats_score: number | null
  }
  stats: {
    profile_completion_pct: number
    placement_readiness_score: number
    resume_ats_score: number | null
    applied_jobs_count: number
    eligible_jobs_count: number
    upcoming_interviews_count: number
    notifications_count: number
  }
  eligible_jobs: DashboardJob[]
  applied_jobs: DashboardJob[]
  upcoming_interviews: DashboardInterview[]
  notifications: DashboardNotification[]
  recent_activity: DashboardActivity[]
  skill_gap: {
    current_skills: { skill: string; level: string }[]
    missing_skills: string[]
    recommendations: string[]
  }
}

export async function getMyDashboard(): Promise<StudentDashboardData> {
  return handle(await safeFetch('/students/me/dashboard'))
}

export async function applyToDrive(driveId: number): Promise<{ drive_id: number; status: string }> {
  return handle(await safeFetch(`/students/me/apply/${driveId}`, { method: 'POST' }))
}

export interface ScoreBreakdownEntry {
  score: number
  max: number
  detail: string
}

export interface ResumeAnalysis {
  ats_score: number | null
  score_breakdown: Record<string, ScoreBreakdownEntry>
  extracted_skills: Record<string, string[]>
  missing_skills: string[]
  suggestions: string[]
  missing_keywords: string[]
  source: 'huggingface' | 'heuristic' | 'extraction_failed'
  analyzed_at?: string
}

export async function analyzeMyResume(): Promise<ResumeAnalysis> {
  return handle(await safeFetch('/students/me/resume/analyze', { method: 'POST' }))
}

export async function getMyResumeAnalysis(): Promise<ResumeAnalysis | null> {
  try {
    return await handle(await safeFetch('/students/me/resume/analysis'))
  } catch {
    return null
  }
}

export async function generateResumeBullets(
  projectTitle: string, description: string
): Promise<{ bullets: string[]; source: string }> {
  return handle(await safeFetch('/students/me/resume/bullets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_title: projectTitle, description }),
  }))
}

export async function generateCoverLetter(driveId: number): Promise<{ cover_letter: string; source: string }> {
  return handle(await safeFetch('/students/me/resume/cover-letter', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drive_id: driveId }),
  }))
}

export async function generateColdEmail(driveId: number): Promise<{ cold_email: string; source: string }> {
  return handle(await safeFetch('/students/me/resume/cold-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drive_id: driveId }),
  }))
}

export interface JDMatchResult {
  match_pct: number | null
  matched_skills: string[]
  missing_skills: string[]
  explanation: string
  source: 'huggingface' | 'heuristic' | 'extraction_failed'
}

export async function matchResumeToDrive(driveId: number): Promise<JDMatchResult> {
  return handle(await safeFetch('/students/me/resume/match-drive', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drive_id: driveId }),
  }))
}
