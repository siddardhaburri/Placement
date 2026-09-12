'use client';

import React, { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';

interface Recommendation {
  output_id: string;
  student_id: number;
  created_at: string;
  reasoning_summary: string;
  decision: string;
  payload?: {
    opportunity_explanations: Array<{ project_id: string; rationale: string }>;
  };
}

export default function FacultyDiscoveryDashboard() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProjects, setSelectedProjects] = useState<Record<string, string>>({});

  useEffect(() => {
    // In a real app, you would fetch from the API.
    const fetchData = async () => {
      try {
        const res = await apiFetch('/agents/13/faculty/discover');
        if (res.ok) {
          const json = await res.json();
          const recs = json.recommendations || [];
          setRecommendations(recs);
          
          // Initialize selected projects with the first available option
          const initialSelections: Record<string, string> = {};
          recs.forEach((rec: Recommendation) => {
            if (rec.payload?.opportunity_explanations?.length) {
              initialSelections[rec.output_id] = rec.payload.opportunity_explanations[0].project_id;
            }
          });
          setSelectedProjects(initialSelections);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleReview = async (output_id: string, decision: string) => {
    try {
      const res = await apiFetch(`/agents/13/recommendation/${output_id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, comments: '' })
      });
      if (res.ok) {
        // Optimistic update
        setRecommendations(prev => prev.map(r => r.output_id === output_id ? { ...r, decision } : r));
      }
    } catch (err) {
      console.error("Review failed", err);
    }
  };

  const handleExecute = async (output_id: string, project_id: string) => {
    if (!project_id) {
      alert("Please select a project first.");
      return;
    }
    try {
      const res = await apiFetch(`/agents/13/recommendation/${output_id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id })
      });
      if (res.ok) {
        alert("Execution successful. Student assigned to project.");
      } else {
        const err = await res.json();
        alert(`Execution failed: ${err.detail}`);
      }
    } catch (err) {
      console.error("Execution failed", err);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading Faculty Discovery Dashboard...</div>;

  return (
    <div className="p-6 bg-white border rounded-lg shadow-md max-w-6xl mx-auto mt-6">
      <div className="mb-8 border-b pb-4">
        <h2 className="text-3xl font-bold text-gray-800">Agent 13: Talent Discovery</h2>
        <p className="text-gray-600 mt-2">Review and approve high-potential student matches for your research projects.</p>
      </div>

      <div className="space-y-4">
        {recommendations.map((rec) => (
          <div key={rec.output_id} className="p-4 border rounded-lg shadow-sm hover:shadow-md transition bg-gray-50 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="font-semibold text-lg text-gray-800">Student #{rec.student_id}</span>
                <span className={`px-2 py-1 text-xs font-bold rounded-full ${
                  rec.decision === 'APPROVED' ? 'bg-green-100 text-green-800' :
                  rec.decision === 'REJECTED' ? 'bg-red-100 text-red-800' :
                  rec.decision === 'EXPIRED' ? 'bg-gray-200 text-gray-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  {rec.decision}
                </span>
              </div>
              <p className="text-sm text-gray-700">{rec.reasoning_summary}</p>
            </div>
            
            <div className="flex flex-col gap-2 min-w-[150px]">
              {rec.decision === 'PENDING' && (
                <>
                  <button onClick={() => handleReview(rec.output_id, 'APPROVED')} className="w-full px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition">Approve Match</button>
                  <button onClick={() => handleReview(rec.output_id, 'REJECTED')} className="w-full px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition">Reject</button>
                </>
              )}
              {rec.decision === 'APPROVED' && (
                <div className="flex flex-col gap-2">
                  <select 
                    className="w-full border border-gray-300 rounded p-1.5 text-xs text-gray-700"
                    value={selectedProjects[rec.output_id] || ''}
                    onChange={(e) => setSelectedProjects(prev => ({...prev, [rec.output_id]: e.target.value}))}
                  >
                    {rec.payload?.opportunity_explanations?.length ? (
                      rec.payload.opportunity_explanations.map(opt => (
                        <option key={opt.project_id} value={opt.project_id}>{opt.project_id}</option>
                      ))
                    ) : (
                      <option value="">No projects found</option>
                    )}
                  </select>
                  <button onClick={() => handleExecute(rec.output_id, selectedProjects[rec.output_id])} className="w-full px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition shadow-sm font-semibold">
                    Execute Assignment
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {recommendations.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No pending recommendations found.
          </div>
        )}
      </div>
    </div>
  );
}
