'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Loader2, ArrowLeft, Sparkles, FileText, Search, Mail, RefreshCw, Copy, Check,
  AlertTriangle, Download, Target, RotateCcw,
} from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { downloadTextFile } from '@/lib/format'
import {
  getMyProfile, analyzeMyResume, getMyResumeAnalysis, generateResumeBullets,
  generateCoverLetter, generateColdEmail, matchResumeToDrive, getMyDashboard,
  type StudentProfile, type ResumeAnalysis, type DashboardJob, type JDMatchResult,
} from '@/lib/student-api'

const inputClass =
  'w-full bg-input border border-border rounded-lg p-2.5 text-foreground text-xs font-semibold focus:border-primary focus:outline-none input-focus'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      className="btn btn-outline text-xs"
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />} {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function DownloadButton({ filename, text }: { filename: string; text: string }) {
  return (
    <button type="button" className="btn btn-outline text-xs" onClick={() => downloadTextFile(filename, text)}>
      <Download size={12} /> Download
    </button>
  )
}

function SourceBadge({ source }: { source: string }) {
  if (source === 'huggingface') {
    return <span className="status-badge good"><Sparkles size={11} /> AI-generated</span>
  }
  if (source === 'heuristic') {
    return <span className="status-badge neutral">Rule-based analysis (no AI key configured)</span>
  }
  if (source === 'extraction_failed') {
    return <span className="status-badge danger"><AlertTriangle size={11} /> Couldn't read resume</span>
  }
  return <span className="status-badge neutral">Template (no AI key configured)</span>
}

function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="status-badge danger mb-4 flex items-center justify-between gap-3" style={{ width: '100%' }}>
      <span className="flex items-center gap-1.5"><AlertTriangle size={12} /> {message}</span>
      {onRetry && (
        <button onClick={onRetry} className="btn btn-outline text-xs" style={{ padding: '2px 8px' }}>
          <RotateCcw size={11} /> Retry
        </button>
      )}
    </div>
  )
}

const CATEGORY_LABELS: Record<string, string> = {
  skills: 'Skills',
  education: 'Education',
  projects: 'Projects',
  certifications: 'Certifications',
  experience: 'Experience',
  formatting: 'Formatting',
  keyword_match: 'Keyword Match',
}

export default function ResumeAIPage() {
  const router = useRouter()
  const [profile, setProfile] = useState<StudentProfile | null>(null)
  const [jobs, setJobs] = useState<DashboardJob[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState('')

  const [bulletTitle, setBulletTitle] = useState('')
  const [bulletDesc, setBulletDesc] = useState('')
  const [bullets, setBullets] = useState<{ bullets: string[]; source: string } | null>(null)
  const [bulletsLoading, setBulletsLoading] = useState(false)
  const [bulletsError, setBulletsError] = useState('')

  const [selectedDriveId, setSelectedDriveId] = useState<number | null>(null)

  const [jdMatch, setJdMatch] = useState<JDMatchResult | null>(null)
  const [jdMatchLoading, setJdMatchLoading] = useState(false)
  const [jdMatchError, setJdMatchError] = useState('')

  const [coverLetter, setCoverLetter] = useState<{ cover_letter: string; source: string } | null>(null)
  const [coverLetterLoading, setCoverLetterLoading] = useState(false)
  const [coverLetterError, setCoverLetterError] = useState('')

  const [coldEmail, setColdEmail] = useState<{ cold_email: string; source: string } | null>(null)
  const [coldEmailLoading, setColdEmailLoading] = useState(false)
  const [coldEmailError, setColdEmailError] = useState('')

  const loadEverything = () => {
    setLoading(true)
    setLoadError('')
    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) { router.push('/'); return }
      try {
        const [prof, dashboard, existingAnalysis] = await Promise.all([
          getMyProfile(), getMyDashboard(), getMyResumeAnalysis(),
        ])
        setProfile(prof)
        const allJobs = [...dashboard.applied_jobs, ...dashboard.eligible_jobs]
        setJobs(allJobs)
        if (allJobs.length > 0) setSelectedDriveId(allJobs[0].drive_id)
        if (existingAnalysis) setAnalysis(existingAnalysis)
      } catch (e: any) {
        setLoadError(e.message || 'Could not load Resume AI.')
      } finally {
        setLoading(false)
      }
    })
  }

  useEffect(() => { loadEverything() }, [])

  const runAnalysis = async () => {
    setAnalyzing(true)
    setAnalysisError('')
    try {
      setAnalysis(await analyzeMyResume())
    } catch (e: any) {
      setAnalysisError(e.message || 'Analysis failed. Check your connection and try again.')
    } finally {
      setAnalyzing(false)
    }
  }

  const runBullets = async () => {
    if (!bulletTitle.trim() || !bulletDesc.trim()) {
      setBulletsError('Fill in both the project title and description.')
      return
    }
    setBulletsLoading(true)
    setBulletsError('')
    try {
      setBullets(await generateResumeBullets(bulletTitle, bulletDesc))
    } catch (e: any) {
      setBulletsError(e.message || 'Failed to generate bullets.')
    } finally {
      setBulletsLoading(false)
    }
  }

  const runJdMatch = async () => {
    if (!selectedDriveId) return
    setJdMatchLoading(true)
    setJdMatchError('')
    try {
      setJdMatch(await matchResumeToDrive(selectedDriveId))
    } catch (e: any) {
      setJdMatchError(e.message || 'Failed to check match.')
    } finally {
      setJdMatchLoading(false)
    }
  }

  const runCoverLetter = async () => {
    if (!selectedDriveId) return
    setCoverLetterLoading(true)
    setCoverLetterError('')
    try {
      setCoverLetter(await generateCoverLetter(selectedDriveId))
    } catch (e: any) {
      setCoverLetterError(e.message || 'Failed to generate cover letter.')
    } finally {
      setCoverLetterLoading(false)
    }
  }

  const runColdEmail = async () => {
    if (!selectedDriveId) return
    setColdEmailLoading(true)
    setColdEmailError('')
    try {
      setColdEmail(await generateColdEmail(selectedDriveId))
    } catch (e: any) {
      setColdEmailError(e.message || 'Failed to generate cold email.')
    } finally {
      setColdEmailLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="animate-spin text-primary" size={28} />
          <span className="text-xs font-mono uppercase tracking-wide text-muted-foreground">Loading Resume AI…</span>
        </div>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center text-center p-6">
        <div className="flex flex-col items-center gap-3">
          <p className="text-sm text-muted-foreground">{loadError || 'Could not load your profile.'}</p>
          <button onClick={loadEverything} className="btn btn-outline text-xs"><RotateCcw size={12} /> Retry</button>
        </div>
      </div>
    )
  }

  const selectedJob = jobs.find((j) => j.drive_id === selectedDriveId)

  return (
    <div className="min-h-screen bg-background">
      <div className="dashboard-main motion-page">
        <div className="section-title">
          <div>
            <button onClick={() => router.push('/')} className="quiet-link mb-3">
              <ArrowLeft size={13} /> Back to dashboard
            </button>
            <div className="eyebrow">Resume AI</div>
            <h1>Resume analysis & application tools</h1>
            <p>Analyze your uploaded resume, check your match against a specific drive, improve bullet points, and draft outreach.</p>
          </div>
        </div>

        {loadError && <ErrorBanner message={loadError} onRetry={loadEverything} />}

        {!profile.resume_url ? (
          <div className="panel">
            <div className="panel-head"><div><h2>No resume uploaded yet</h2><p>Upload a PDF resume on your profile page before running analysis.</p></div></div>
            <button onClick={() => router.push('/profile')} className="btn btn-primary">Go to Profile</button>
          </div>
        ) : (
          <div className="panel">
            <div className="panel-head">
              <div><h2 className="flex items-center gap-2"><Search size={16} className="text-primary" /> ATS Analysis</h2><p>{profile.resume_filename}</p></div>
              <button onClick={runAnalysis} disabled={analyzing} className="btn btn-primary">
                {analyzing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                {analyzing ? 'Analyzing…' : analysis ? 'Re-analyze' : 'Analyze Resume'}
              </button>
            </div>

            {analysisError && <ErrorBanner message={analysisError} onRetry={runAnalysis} />}

            {analyzing && !analysis && (
              <div className="text-xs text-muted-foreground">Reading your resume and scoring it across 7 categories…</div>
            )}

            {analysis && (
              <div className="flex flex-col gap-5">
                <SourceBadge source={analysis.source} />

                {analysis.ats_score != null && (
                  <div className="metric-card">
                    <div className="metric-top"><span>Overall ATS Score</span></div>
                    <div className="metric-value">{analysis.ats_score}/100</div>
                    <div className="bar mt-2"><i style={{ width: `${analysis.ats_score}%` }} /></div>
                  </div>
                )}

                {Object.keys(analysis.score_breakdown || {}).length > 0 && (
                  <div>
                    <div className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-3">Score breakdown</div>
                    <div className="flex flex-col gap-3">
                      {Object.entries(analysis.score_breakdown).map(([key, entry]) => (
                        <div key={key}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="font-semibold">{CATEGORY_LABELS[key] || key}</span>
                            <span className="text-muted-foreground">{entry.score}/{entry.max}</span>
                          </div>
                          <div className="bar"><i style={{ width: `${(entry.score / entry.max) * 100}%` }} /></div>
                          <div className="text-[11px] text-muted-foreground mt-1">{entry.detail}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {Object.keys(analysis.extracted_skills || {}).length > 0 && (
                  <div>
                    <div className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-2">Skills detected in your resume</div>
                    <div className="flex flex-col gap-2">
                      {Object.entries(analysis.extracted_skills).map(([category, skills]) => (
                        <div key={category}>
                          <div className="text-[11px] text-muted-foreground mb-1">{category}</div>
                          <div className="skill-tags flex-wrap">
                            {skills.map((s) => <span key={s}>{s}</span>)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.missing_skills.length > 0 && (
                  <div>
                    <div className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-2">Missing keywords vs. your profile's target skills</div>
                    <div className="skill-tags flex-wrap">
                      {analysis.missing_skills.map((s) => <span key={s} className="text-red-400">{s}</span>)}
                    </div>
                  </div>
                )}

                {analysis.suggestions.length > 0 && (
                  <div>
                    <div className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-2">Suggestions</div>
                    <ul className="flex flex-col gap-2">
                      {analysis.suggestions.map((s, i) => (
                        <li key={i} className="text-xs text-muted-foreground">• {s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Bullet point generator */}
        <div className="panel mt-4">
          <div className="panel-head"><div><h2 className="flex items-center gap-2"><FileText size={16} className="text-primary" /> Improve a Resume Bullet</h2><p>Turn a rough project description into polished bullet points.</p></div></div>
          <div className="flex flex-col gap-2">
            <input className={inputClass} value={bulletTitle} placeholder="Project title" onChange={(e) => setBulletTitle(e.target.value)} />
            <textarea className={inputClass} rows={3} value={bulletDesc} placeholder="Rough description of what you did" onChange={(e) => setBulletDesc(e.target.value)} />
            <button onClick={runBullets} disabled={bulletsLoading} className="btn btn-primary self-start">
              {bulletsLoading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {bulletsLoading ? 'Generating…' : 'Generate Bullets'}
            </button>
          </div>
          {bulletsError && <div className="mt-3"><ErrorBanner message={bulletsError} onRetry={runBullets} /></div>}
          {bullets && (
            <div className="mt-4 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <SourceBadge source={bullets.source} />
                <DownloadButton filename="resume-bullets.txt" text={bullets.bullets.join('\n')} />
              </div>
              {bullets.bullets.map((b, i) => (
                <div key={i} className="file-row">
                  <div><span>{b}</span></div>
                  <CopyButton text={b} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* JD match + cover letter + cold email */}
        {jobs.length > 0 && (
          <div className="panel mt-4">
            <div className="panel-head"><div><h2 className="flex items-center gap-2"><Mail size={16} className="text-primary" /> Match, Cover Letter & Cold Email</h2><p>Tailored to a specific drive you're eligible for or applied to.</p></div></div>
            <select
              className={inputClass}
              value={selectedDriveId ?? ''}
              onChange={(e) => {
                setSelectedDriveId(parseInt(e.target.value))
                setJdMatch(null)
                setCoverLetter(null)
                setColdEmail(null)
              }}
            >
              {jobs.map((j) => (
                <option key={j.drive_id} value={j.drive_id}>{j.company_name} · {j.role_title}</option>
              ))}
            </select>

            <div className="flex gap-2 mt-3 flex-wrap">
              <button onClick={runJdMatch} disabled={jdMatchLoading} className="btn btn-outline">
                {jdMatchLoading ? <Loader2 size={13} className="animate-spin" /> : <Target size={13} />} Check Match
              </button>
              <button onClick={runCoverLetter} disabled={coverLetterLoading} className="btn btn-outline">
                {coverLetterLoading ? <Loader2 size={13} className="animate-spin" /> : null} Generate Cover Letter
              </button>
              <button onClick={runColdEmail} disabled={coldEmailLoading} className="btn btn-outline">
                {coldEmailLoading ? <Loader2 size={13} className="animate-spin" /> : null} Generate Cold Email
              </button>
            </div>

            {jdMatchError && <div className="mt-3"><ErrorBanner message={jdMatchError} onRetry={runJdMatch} /></div>}
            {jdMatch && (
              <div className="mt-4 flex flex-col gap-3">
                <SourceBadge source={jdMatch.source} />
                {jdMatch.match_pct != null && (
                  <div className="metric-card">
                    <div className="metric-top"><span>Match with {selectedJob?.company_name}</span></div>
                    <div className="metric-value">{jdMatch.match_pct}%</div>
                    <div className="bar mt-2"><i style={{ width: `${jdMatch.match_pct}%` }} /></div>
                  </div>
                )}
                <p className="text-xs text-muted-foreground">{jdMatch.explanation}</p>
                {jdMatch.matched_skills.length > 0 && (
                  <div>
                    <div className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-2">Matched skills</div>
                    <div className="skill-tags flex-wrap">
                      {jdMatch.matched_skills.map((s) => <span key={s} className="text-green-400">{s}</span>)}
                    </div>
                  </div>
                )}
                {jdMatch.missing_skills.length > 0 && (
                  <div>
                    <div className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-2">Missing skills</div>
                    <div className="skill-tags flex-wrap">
                      {jdMatch.missing_skills.map((s) => <span key={s} className="text-red-400">{s}</span>)}
                    </div>
                  </div>
                )}
              </div>
            )}

            {coverLetterError && <div className="mt-3"><ErrorBanner message={coverLetterError} onRetry={runCoverLetter} /></div>}
            {coverLetter && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <SourceBadge source={coverLetter.source} />
                  <div className="flex gap-2">
                    <CopyButton text={coverLetter.cover_letter} />
                    <DownloadButton filename="cover-letter.txt" text={coverLetter.cover_letter} />
                  </div>
                </div>
                <textarea className={inputClass} rows={8} readOnly value={coverLetter.cover_letter} />
              </div>
            )}

            {coldEmailError && <div className="mt-3"><ErrorBanner message={coldEmailError} onRetry={runColdEmail} /></div>}
            {coldEmail && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <SourceBadge source={coldEmail.source} />
                  <div className="flex gap-2">
                    <CopyButton text={coldEmail.cold_email} />
                    <DownloadButton filename="cold-email.txt" text={coldEmail.cold_email} />
                  </div>
                </div>
                <textarea className={inputClass} rows={6} readOnly value={coldEmail.cold_email} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
