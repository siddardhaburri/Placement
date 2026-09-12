'use client'

import { useRouter } from 'next/navigation'
import { ArrowRight, CheckCircle2 } from 'lucide-react'
import type { StudentProfile } from '@/lib/student-api'

const FIELD_LABELS: { key: keyof StudentProfile; label: string }[] = [
  { key: 'skills', label: 'Skills' },
  { key: 'projects', label: 'Projects' },
  { key: 'certifications', label: 'Certifications' },
  { key: 'internship_history', label: 'Internships' },
  { key: 'hackathons', label: 'Hackathons' },
  { key: 'resume_url', label: 'Resume upload' },
  { key: 'profile_photo_url', label: 'Profile photo' },
  { key: 'github_url', label: 'GitHub link' },
  { key: 'linkedin_url', label: 'LinkedIn link' },
  { key: 'coding_profiles', label: 'Coding profiles' },
  { key: 'preferred_roles', label: 'Preferred roles' },
  { key: 'expected_salary', label: 'Expected salary' },
  { key: 'location_preference', label: 'Location preference' },
]

function isEmpty(value: unknown): boolean {
  if (value == null) return true
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value).length === 0
  if (typeof value === 'string') return value.trim() === ''
  return false
}

export function ProfileCompletionCard({ profile }: { profile: StudentProfile }) {
  const router = useRouter()
  const pct = profile.profile_completion_pct
  const missing = FIELD_LABELS.filter((f) => isEmpty(profile[f.key])).map((f) => f.label)

  if (pct >= 100) {
    return (
      <div className="panel">
        <div className="panel-head"><div><h2>Profile Complete</h2></div></div>
        <div className="status-badge good"><CheckCircle2 size={12} /> Your profile is 100% complete</div>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h2>Complete Your Profile</h2>
          <p>Recruiters and the matching engine rank complete profiles higher.</p>
        </div>
        <button onClick={() => router.push('/profile')} className="btn btn-primary">
          Complete Profile <ArrowRight size={13} />
        </button>
      </div>
      <div className="bar"><i style={{ width: `${pct}%` }} /></div>
      <div className="metric-detail mt-2">{pct}% complete</div>
      {missing.length > 0 && (
        <div className="skill-tags mt-3 flex-wrap">
          {missing.slice(0, 8).map((m) => <span key={m}>{m}</span>)}
        </div>
      )}
    </div>
  )
}
