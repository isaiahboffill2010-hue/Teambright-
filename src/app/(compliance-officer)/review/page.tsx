'use client';
import { useState } from 'react';
import { useComplianceStore } from '@/store/useComplianceStore';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { SubmissionStatusBadge, RiskBadge } from '@/components/ui/Badge';
import { ComplianceScoreCard } from '@/components/compliance/ComplianceScoreCard';
import { ComplianceSubmission } from '@/types';

function ReviewModal({ submission, onClose }: { submission: ComplianceSubmission; onClose: () => void }) {
  const { updateSubmissionStatus } = useComplianceStore();
  const [notes, setNotes] = useState('');
  const [action, setAction] = useState<'approve' | 'reject' | 'revision' | null>(null);

  const handleConfirm = () => {
    if (!action) return;
    const statusMap = { approve: 'approved', reject: 'rejected', revision: 'revision_requested' } as const;
    updateSubmissionStatus(submission.id, statusMap[action], notes);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-bold text-slate-900">Review Submission</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg">✕</button>
        </div>

        <div className="p-6 space-y-5">
          {/* Message info */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Message</h3>
            <p className="text-sm font-semibold text-slate-800 mb-1">{submission.subject}</p>
            <p className="text-xs text-slate-400">{submission.recipientCount} recipients</p>
          </div>

          {/* Compliance score */}
          <ComplianceScoreCard score={submission.complianceScore} />

          {/* Message content preview */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Content Preview</h3>
            <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-700 max-h-32 overflow-y-auto font-mono text-xs leading-relaxed">
              {submission.messageContent}
            </div>
          </div>

          {/* Officer decision */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Decision</h3>
            <div className="flex gap-2 mb-3">
              <button
                onClick={() => setAction('approve')}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium border transition-colors ${
                  action === 'approve' ? 'bg-green-600 text-white border-green-600' : 'border-slate-200 text-slate-700 hover:border-green-400'
                }`}
              >
                ✓ Approve
              </button>
              <button
                onClick={() => setAction('revision')}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium border transition-colors ${
                  action === 'revision' ? 'bg-amber-500 text-white border-amber-500' : 'border-slate-200 text-slate-700 hover:border-amber-400'
                }`}
              >
                ↩ Request Revision
              </button>
              <button
                onClick={() => setAction('reject')}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium border transition-colors ${
                  action === 'reject' ? 'bg-red-600 text-white border-red-600' : 'border-slate-200 text-slate-700 hover:border-red-400'
                }`}
              >
                ✕ Reject
              </button>
            </div>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Officer notes (optional for approval, required for rejection/revision)..."
              rows={3}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-200">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button
            onClick={handleConfirm}
            disabled={!action || (action !== 'approve' && !notes)}
            variant={action === 'reject' ? 'danger' : 'primary'}
          >
            Confirm {action === 'approve' ? 'Approval' : action === 'reject' ? 'Rejection' : 'Revision Request'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function ReviewQueuePage() {
  const { submissions } = useComplianceStore();
  const [reviewing, setReviewing] = useState<ComplianceSubmission | null>(null);

  const pending = submissions.filter((s) => s.status === 'pending_review' || s.status === 'under_review');
  const resolved = submissions.filter((s) => !['pending_review', 'under_review'].includes(s.status));

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Review Queue</h1>
          <p className="text-slate-500 text-sm mt-1">
            {pending.length} submission{pending.length !== 1 ? 's' : ''} awaiting review
          </p>
        </div>
        <form action="/auth/signout" method="POST">
          <button type="submit" className="text-xs text-slate-400 hover:text-slate-700 transition-colors">
            Sign out
          </button>
        </form>
      </div>

      {pending.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Pending Review</h2>
          <div className="space-y-3">
            {pending.map((s) => (
              <Card key={s.id} className="border-amber-200 bg-amber-50/30">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-slate-800">{s.subject}</h3>
                      <SubmissionStatusBadge status={s.status} />
                    </div>
                    <p className="text-xs text-slate-400 mb-2">
                      {s.recipientCount} recipients ·
                      Submitted {new Date(s.submittedAt).toLocaleDateString()}
                    </p>
                    <div className="flex items-center gap-3">
                      <RiskBadge level={s.complianceScore.riskLevel} />
                      <span className="text-xs font-mono text-slate-500">
                        P(lawful)={Math.round(s.complianceScore.projectedProbability * 100)}%
                      </span>
                      {s.complianceScore.triggeredRules.length > 0 && (
                        <span className="text-xs text-amber-700">
                          ⚠ {s.complianceScore.triggeredRules.length} rule{s.complianceScore.triggeredRules.length !== 1 ? 's' : ''} triggered
                        </span>
                      )}
                    </div>
                  </div>
                  <Button size="sm" onClick={() => setReviewing(s)} className="ml-4">
                    Review
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {resolved.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Resolved</h2>
          <div className="space-y-3">
            {resolved.map((s) => (
              <Card key={s.id}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-slate-800">{s.subject}</h3>
                      <SubmissionStatusBadge status={s.status} />
                      <RiskBadge level={s.complianceScore.riskLevel} />
                    </div>
                    <p className="text-xs text-slate-400">
                      {s.recipientCount} recipients ·
                      Reviewed {s.reviewedAt && new Date(s.reviewedAt).toLocaleDateString()}
                    </p>
                    {s.officerNotes && (
                      <p className="text-xs text-slate-600 mt-1.5 italic">&ldquo;{s.officerNotes}&rdquo;</p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {reviewing && <ReviewModal submission={reviewing} onClose={() => setReviewing(null)} />}
    </div>
  );
}
