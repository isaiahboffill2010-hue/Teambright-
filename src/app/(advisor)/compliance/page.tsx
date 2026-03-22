import { Card } from '@/components/ui/Card';
import { SubmissionStatusBadge, RiskBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { MOCK_SUBMISSIONS } from '@/lib/mockData';
import Link from 'next/link';

export default function CompliancePage() {
  const submissions = MOCK_SUBMISSIONS;
  const pending = submissions.filter((s) => s.status === 'pending_review').length;
  const approved = submissions.filter((s) => s.status === 'approved').length;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Compliance Submissions</h1>
          <p className="text-slate-500 text-sm mt-1">Track your outreach through the compliance review workflow</p>
        </div>
        <Link href="/compliance/submit">
          <Button>+ New Submission</Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card>
          <p className="text-xs text-slate-500 mb-1">Total Submitted</p>
          <p className="text-2xl font-bold text-slate-900">{submissions.length}</p>
        </Card>
        <Card>
          <p className="text-xs text-slate-500 mb-1">Pending Review</p>
          <p className={`text-2xl font-bold ${pending > 0 ? 'text-amber-600' : 'text-slate-900'}`}>{pending}</p>
        </Card>
        <Card>
          <p className="text-xs text-slate-500 mb-1">Approved</p>
          <p className="text-2xl font-bold text-green-600">{approved}</p>
        </Card>
      </div>

      {/* How it works */}
      <Card className="mb-6 bg-slate-50 border-slate-200">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Compliance Workflow</h3>
        <div className="flex items-center gap-2 text-xs text-slate-600">
          {['Compose', 'Score', 'Submit', 'Officer Review', 'Approved / Send'].map((step, i, arr) => (
            <>
              <span key={step} className="px-2.5 py-1 bg-white border border-slate-200 rounded-full font-medium">
                {i + 1}. {step}
              </span>
              {i < arr.length - 1 && <span className="text-slate-300">→</span>}
            </>
          ))}
        </div>
        <p className="text-xs text-slate-500 mt-3">
          Medium and high-risk messages require officer review. Low-risk messages can be sent directly after scoring.
        </p>
      </Card>

      {/* Submissions list */}
      <div className="space-y-3">
        {submissions.map((s) => (
          <Card key={s.id} className="hover:border-blue-200 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-slate-800 truncate">{s.subject}</h3>
                  <SubmissionStatusBadge status={s.status} />
                </div>
                <p className="text-xs text-slate-400 mb-2">
                  {s.recipientCount} recipient{s.recipientCount !== 1 ? 's' : ''} ·{' '}
                  Submitted {new Date(s.submittedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  {s.reviewedAt && ` · Reviewed ${new Date(s.reviewedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`}
                </p>

                {/* Score snapshot */}
                <div className="flex items-center gap-3">
                  <RiskBadge level={s.complianceScore.riskLevel} />
                  <span className="text-xs text-slate-400 font-mono">
                    P(lawful) = {(s.complianceScore.projectedProbability * 100).toFixed(1)}%
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    ω.b={s.complianceScore.opinion.b.toFixed(3)} d={s.complianceScore.opinion.d.toFixed(3)} u={s.complianceScore.opinion.u.toFixed(3)}
                  </span>
                </div>

                {s.officerNotes && (
                  <div className="mt-2 text-xs bg-green-50 text-green-800 rounded-lg px-3 py-2">
                    Officer note: {s.officerNotes}
                  </div>
                )}
              </div>

              {s.status === 'approved' && (
                <Link href="/outreach/compose">
                  <Button size="sm" className="ml-4">Send</Button>
                </Link>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
