'use client';

import React, { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';

interface Agent13Output {
  output_id: string;
  created_at: string;
  payload: {
    explainable_summary: string;
    hidden_talent_explanation: string | null;
    next_best_action: { action: string; reasoning: string };
    personalized_pathway: Array<{ phase: string; milestone: string }>;
    opportunity_explanations: Array<{ project_id: string; rationale: string }>;
    faculty_match_explanations: Array<{ faculty_id: number; rationale: string }>;
    confidence: number;
  };
  reasoning_summary: string;
  review_status: string;
}

export default function Agent13TalentCard({ studentId }: { studentId: number }) {
  const [data, setData] = useState<Agent13Output | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real app, you would fetch from the API.
    // For this demonstration, we'll simulate the data load.
    const fetchData = async () => {
      try {
        const res = await apiFetch(`/agents/13/student/${studentId}`);
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [studentId]);

  if (loading) return <div className="p-4 border rounded shadow-sm animate-pulse">Loading Talent Discovery Profile...</div>;
  if (!data) return <div className="p-4 border rounded shadow-sm">No Agent 13 recommendations available yet.</div>;

  return (
    <div className="p-6 bg-white border rounded-lg shadow-md space-y-6">
      <div className="flex justify-between items-center border-b pb-4">
        <h2 className="text-2xl font-semibold text-gray-800">Agent 13: Talent Profile</h2>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          data.review_status === 'APPROVED' ? 'bg-green-100 text-green-800' :
          data.review_status === 'REJECTED' ? 'bg-red-100 text-red-800' :
          'bg-yellow-100 text-yellow-800'
        }`}>
          {data.review_status}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-700">Next Best Action</h3>
          <div className="p-4 bg-blue-50 border border-blue-100 rounded-md">
            <p className="font-semibold text-blue-900">{data.payload.next_best_action?.action}</p>
            <p className="text-sm text-blue-700 mt-2">{data.payload.next_best_action?.reasoning}</p>
          </div>

          {data.payload.hidden_talent_explanation && (
            <div className="p-4 bg-purple-50 border border-purple-100 rounded-md">
              <h4 className="font-semibold text-purple-900 flex items-center gap-2">
                <span>🌟</span> Hidden Talent Detected
              </h4>
              <p className="text-sm text-purple-700 mt-2">{data.payload.hidden_talent_explanation}</p>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-700">Personalized Pathway</h3>
          <ul className="space-y-3">
            {data.payload.personalized_pathway?.map((step, idx) => (
              <li key={idx} className="flex gap-4 items-start">
                <span className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-sm font-bold">
                  {idx + 1}
                </span>
                <div>
                  <p className="text-sm font-semibold text-gray-800">{step.phase}</p>
                  <p className="text-sm text-gray-600">{step.milestone}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="pt-4 border-t">
        <h3 className="text-lg font-medium text-gray-700 mb-3">Explainable Summary</h3>
        <p className="text-sm text-gray-600 leading-relaxed bg-gray-50 p-4 rounded border">
          {data.payload.explainable_summary}
        </p>
      </div>
    </div>
  );
}
