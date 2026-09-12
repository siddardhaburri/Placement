import { Bell } from 'lucide-react'
import type { DashboardNotification } from '@/lib/student-api'
import { timeAgo } from '@/lib/format'

export function NotificationCard({ notification }: { notification: DashboardNotification }) {
  return (
    <div className="action-card">
      <div className="action-icon"><Bell size={15} /></div>
      <div className="action-copy">
        <strong>{notification.message}</strong>
        <span>{timeAgo(notification.sent_at)}</span>
      </div>
    </div>
  )
}
