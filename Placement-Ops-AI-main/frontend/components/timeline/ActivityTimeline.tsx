import { Activity, FileText, UserCheck, Send } from 'lucide-react'
import type { DashboardActivity } from '@/lib/student-api'
import { timeAgo } from '@/lib/format'

const ACTION_ICON: Record<string, React.ElementType> = {
  applied: Send,
  resume_uploaded: FileText,
  profile_updated: UserCheck,
}

const ACTION_LABEL: Record<string, string> = {
  applied: 'Applied to a drive',
  resume_uploaded: 'Uploaded resume',
  profile_updated: 'Updated profile',
}

export function ActivityTimeline({ activity }: { activity: DashboardActivity[] }) {
  if (activity.length === 0) {
    return (
      <div className="text-xs text-muted-foreground">
        No recent activity yet. Actions you take from here on (applying to jobs, updating your profile, uploading a resume) will show up here.
      </div>
    )
  }

  return (
    <div className="action-list">
      {activity.map((a, i) => {
        const Icon = ACTION_ICON[a.action] || Activity
        return (
          <div key={i} className="action-card">
            <div className="action-icon"><Icon size={15} /></div>
            <div className="action-copy">
              <strong>{ACTION_LABEL[a.action] || a.action}</strong>
              <span>{a.details} · {timeAgo(a.timestamp)}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
