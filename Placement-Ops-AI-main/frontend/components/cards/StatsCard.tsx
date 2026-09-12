import type { LucideIcon } from 'lucide-react'

export function StatsCard({
  label, value, detail, icon: Icon, tone = 'blue',
}: {
  label: string
  value: string | number
  detail?: string
  icon: LucideIcon
  tone?: 'blue' | 'coral'
}) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <span className={`icon-box ${tone}`}><Icon size={16} /></span>
      </div>
      <div className="metric-value">{value}</div>
      {detail && <div className="metric-detail">{detail}</div>}
    </div>
  )
}
