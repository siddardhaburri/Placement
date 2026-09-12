import { CalendarDays, Users, Link as LinkIcon } from 'lucide-react'
import type { DashboardInterview } from '@/lib/student-api'

export function InterviewCard({ interview }: { interview: DashboardInterview }) {
  return (
    <div className="action-card">
      <div className="action-icon"><CalendarDays size={15} /></div>
      <div className="action-copy">
        <strong>{interview.company_name || 'Interview'}</strong>
        <span>{interview.time_slot}</span>
        {interview.panel_members?.length > 0 && (
          <span className="flex items-center gap-1"><Users size={10} /> {interview.panel_members.join(', ')}</span>
        )}
      </div>
      {interview.room_or_link && (
        <a href={interview.room_or_link} target="_blank" rel="noopener noreferrer" className="btn btn-outline text-xs">
          <LinkIcon size={12} /> Join
        </a>
      )}
    </div>
  )
}
