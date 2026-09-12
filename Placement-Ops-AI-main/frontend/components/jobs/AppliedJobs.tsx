import { JobCard } from '@/components/cards/JobCard'
import type { DashboardJob } from '@/lib/student-api'

export function AppliedJobs({ jobs }: { jobs: DashboardJob[] }) {
  if (jobs.length === 0) {
    return <div className="text-xs text-muted-foreground">You haven't applied to any drives yet.</div>
  }

  return (
    <div className="drive-list">
      {jobs.map((job) => <JobCard key={job.drive_id} job={job} />)}
    </div>
  )
}
