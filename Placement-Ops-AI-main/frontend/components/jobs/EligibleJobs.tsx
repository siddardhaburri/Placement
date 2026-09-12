'use client'

import { useState } from 'react'
import { JobCard } from '@/components/cards/JobCard'
import { applyToDrive, type DashboardJob } from '@/lib/student-api'

export function EligibleJobs({ jobs, onApplied }: { jobs: DashboardJob[]; onApplied: () => void }) {
  const [applyingId, setApplyingId] = useState<number | null>(null)
  const [error, setError] = useState('')

  const handleApply = async (driveId: number) => {
    setApplyingId(driveId)
    setError('')
    try {
      await applyToDrive(driveId)
      onApplied()
    } catch (e: any) {
      setError(e.message || 'Failed to apply.')
    } finally {
      setApplyingId(null)
    }
  }

  if (jobs.length === 0) {
    return <div className="text-xs text-muted-foreground">No eligible drives right now. Check back once new drives are published.</div>
  }

  return (
    <div className="drive-list">
      {error && <div className="status-badge danger mb-2">{error}</div>}
      {jobs.map((job) => (
        <JobCard
          key={job.drive_id}
          job={job}
          actionLabel={applyingId === job.drive_id ? 'Applying…' : 'Apply'}
          actionDisabled={applyingId === job.drive_id}
          onAction={() => handleApply(job.drive_id)}
        />
      ))}
    </div>
  )
}
