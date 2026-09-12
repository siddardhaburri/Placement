import { Building2, MapPin } from 'lucide-react'
import type { DashboardJob } from '@/lib/student-api'

const STATUS_TONE: Record<string, 'good' | 'warn' | 'danger' | 'neutral'> = {
  Applied: 'neutral',
  Shortlisted: 'good',
  'Interview Scheduled': 'good',
  'Interview Completed': 'good',
  Offer: 'good',
  Rejected: 'danger',
}

export function JobCard({
  job, actionLabel, onAction, actionDisabled,
}: {
  job: DashboardJob
  actionLabel?: string
  onAction?: () => void
  actionDisabled?: boolean
}) {
  return (
    <div className="drive-row">
      <div className="company-avatar">{job.company_name.slice(0, 2).toUpperCase()}</div>
      <div>
        <strong>{job.role_title}</strong>
        <span className="flex items-center gap-2">
          <span className="flex items-center gap-1"><Building2 size={11} /> {job.company_name}</span>
          {job.location && <span className="flex items-center gap-1"><MapPin size={11} /> {job.location}</span>}
          <span>₹{job.package_min}–{job.package_max} LPA</span>
        </span>
      </div>
      <div className="drive-stage">
        {job.status ? (
          <span className={`status-badge ${STATUS_TONE[job.status] || 'neutral'}`}><span className="status-dot" />{job.status}</span>
        ) : job.match_pct != null ? (
          <span className="status-badge good"><span className="status-dot" />{job.match_pct}% match</span>
        ) : null}
        {actionLabel && onAction && (
          <button onClick={onAction} disabled={actionDisabled} className="btn btn-primary text-xs mt-1">
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  )
}
