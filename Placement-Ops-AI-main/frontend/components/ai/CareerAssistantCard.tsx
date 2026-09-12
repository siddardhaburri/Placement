'use client'

import { Sparkles, FileText, Search, Mic, TrendingUp, Compass } from 'lucide-react'

const QUICK_ACTIONS = [
  { label: 'Improve Resume', icon: FileText, prompt: 'How can I improve my resume for placements?' },
  { label: 'Find Matching Jobs', icon: Search, prompt: 'What kinds of jobs am I a good fit for based on my profile?' },
  { label: 'Interview Preparation', icon: Mic, prompt: 'How should I prepare for upcoming placement interviews?' },
  { label: 'Skill Roadmap', icon: TrendingUp, prompt: 'What skills should I learn next to improve my placement readiness?' },
  { label: 'Career Advice', icon: Compass, prompt: 'What career path should I consider given my branch and interests?' },
]

function askAI(prompt: string) {
  window.dispatchEvent(new CustomEvent('placement-ops:ask-ai', { detail: prompt }))
}

export function CareerAssistantCard() {
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h2 className="flex items-center gap-2"><Sparkles size={16} className="text-primary" /> AI Career Assistant</h2>
          <p>Ask anything about your placement journey.</p>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        {QUICK_ACTIONS.map(({ label, icon: Icon, prompt }) => (
          <button
            key={label}
            onClick={() => askAI(prompt)}
            className="action-card"
            style={{ width: '100%', textAlign: 'left', cursor: 'pointer', border: 0, background: 'transparent' }}
          >
            <div className="action-icon"><Icon size={15} /></div>
            <div className="action-copy"><strong>{label}</strong></div>
          </button>
        ))}
      </div>
    </div>
  )
}
