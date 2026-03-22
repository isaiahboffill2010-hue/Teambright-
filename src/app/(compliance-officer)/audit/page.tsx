import { Card } from '@/components/ui/Card';
import { SubmissionStatusBadge, RiskBadge } from '@/components/ui/Badge';
import { MOCK_SUBMISSIONS } from '@/lib/mockData';

export default function AuditPage() {
  const allSubmissions = [...MOCK_SUBMISSIONS].sort(
    (a, b) => new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime(),
  );

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Audit Log</h1>
        <p className="text-slate-500 text-sm mt-1">Complete record of all compliance submissions and decisions</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Submissions', value: allSubmissions.length, color: 'text-slate-900' },
          { label: 'Approved', value: allSubmissions.filter((s) => s.status === 'approved').length, color: 'text-green-600' },
          { label: 'Rejected', value: allSubmissions.filter((s) => s.status === 'rejected').length, color: 'text-red-600' },
          { label: 'Pending', value: allSubmissions.filter((s) => s.status === 'pending_review').length, color: 'text-amber-600' },
        ].map((stat) => (
          <Card key={stat.label}>
            <p className="text-xs text-slate-500 mb-1">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </Card>
        ))}
      </div>

      {/* Compliance algebra explanation */}
      <Card className="mb-6 bg-slate-900 text-slate-100 border-slate-800">
        <h3 className="text-sm font-semibold text-blue-400 mb-2">Compliance Algebra — Subjective Logic Engine</h3>
        <p className="text-xs text-slate-300 leading-relaxed mb-3">
          Each submission is scored using Jøsang Subjective Logic. The compliance opinion ω = (b, d, u, a) models epistemic uncertainty about regulatory compliance:
        </p>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <p className="text-slate-400"><span className="text-green-400 font-mono">b</span> = belief (lawfulness evidence)</p>
            <p className="text-slate-400"><span className="text-red-400 font-mono">d</span> = disbelief (violation evidence)</p>
          </div>
          <div>
            <p className="text-slate-400"><span className="text-amber-400 font-mono">u</span> = uncertainty (absence of evidence)</p>
            <p className="text-slate-400"><span className="text-blue-400 font-mono">P(ω) = b + a·u</span> — projected probability</p>
          </div>
        </div>
        <div className="mt-3 text-xs text-slate-400">
          Operators applied: <span className="font-mono text-blue-300">jurisdictionalMeet</span> (FINRA × Consent),{' '}
          <span className="font-mono text-blue-300">cumulativeFusion</span> (rule aggregation),{' '}
          <span className="font-mono text-blue-300">consentValidity</span> (per Art. 7 GDPR semantics)
        </div>
      </Card>

      {/* Audit table */}
      <Card padding="none">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/50">
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Subject</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Submitted</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Risk</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 font-mono">ω opinion</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Status</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Reviewed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {allSubmissions.map((s) => (
              <tr key={s.id} className="hover:bg-slate-50">
                <td className="px-5 py-3.5 font-medium text-slate-800 max-w-xs truncate">{s.subject}</td>
                <td className="px-5 py-3.5 text-slate-500 text-xs">
                  {new Date(s.submittedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </td>
                <td className="px-5 py-3.5"><RiskBadge level={s.complianceScore.riskLevel} /></td>
                <td className="px-5 py-3.5 font-mono text-xs text-slate-500">
                  b={s.complianceScore.opinion.b.toFixed(2)} d={s.complianceScore.opinion.d.toFixed(2)} u={s.complianceScore.opinion.u.toFixed(2)}
                </td>
                <td className="px-5 py-3.5"><SubmissionStatusBadge status={s.status} /></td>
                <td className="px-5 py-3.5 text-slate-500 text-xs">
                  {s.reviewedAt
                    ? new Date(s.reviewedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
