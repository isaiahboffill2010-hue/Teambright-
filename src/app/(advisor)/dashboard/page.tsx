import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import Link from 'next/link';
import { MOCK_PROSPECTS, MOCK_CAMPAIGNS, MOCK_SUBMISSIONS, MOCK_TAX_OPPORTUNITIES } from '@/lib/mockData';

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color: string }) {
  return (
    <Card>
      <p className="text-xs font-medium text-slate-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </Card>
  );
}

export default function DashboardPage() {
  const totalAUM = MOCK_PROSPECTS.reduce((s, p) => s + (p.enrichment?.estimatedAUM ?? 0), 0);
  const taxOpps = MOCK_TAX_OPPORTUNITIES;
  const totalSavings = taxOpps.reduce((s, t) => s + (t.estimatedSavings ?? 0), 0);
  const pendingReviews = MOCK_SUBMISSIONS.filter((s) => s.status === 'pending_review').length;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Good morning, Alex</h1>
        <p className="text-slate-500 mt-1">Here's your pipeline overview for December 2024.</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Prospects"
          value={MOCK_PROSPECTS.length}
          sub={`${MOCK_PROSPECTS.filter((p) => p.status === 'qualified').length} qualified`}
          color="text-slate-900"
        />
        <StatCard
          label="Est. AUM Opportunity"
          value={`$${(totalAUM / 1_000_000).toFixed(1)}M`}
          sub="across active prospects"
          color="text-blue-600"
        />
        <StatCard
          label="Tax Savings Identified"
          value={`$${(totalSavings / 1000).toFixed(0)}K`}
          sub={`${taxOpps.filter((t) => t.urgency === 'high').length} high-urgency`}
          color="text-green-600"
        />
        <StatCard
          label="Compliance Queue"
          value={pendingReviews}
          sub="pending officer review"
          color={pendingReviews > 0 ? 'text-amber-600' : 'text-slate-900'}
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Recent Prospects */}
        <div className="col-span-2">
          <Card padding="none">
            <CardHeader className="px-5 pt-5 pb-0">
              <CardTitle>Recent Prospects</CardTitle>
              <Link href="/prospects" className="text-xs text-blue-600 hover:underline">View all</Link>
            </CardHeader>
            <div className="divide-y divide-slate-100">
              {MOCK_PROSPECTS.slice(0, 4).map((p) => (
                <Link key={p.id} href={`/prospects`} className="flex items-center gap-3 px-5 py-3.5 hover:bg-slate-50 transition-colors">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
                    {p.firstName[0]}{p.lastName[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800">{p.firstName} {p.lastName}</p>
                    <p className="text-xs text-slate-400 truncate">{p.enrichment?.companyName} · {p.enrichment?.jobTitle}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs font-semibold text-slate-700">
                      ${((p.enrichment?.estimatedAUM ?? 0) / 1_000_000).toFixed(1)}M
                    </p>
                    <p className="text-xs text-slate-400 capitalize">{p.status.replace('_', ' ')}</p>
                  </div>
                </Link>
              ))}
            </div>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Tax opportunities */}
          <Card>
            <CardHeader>
              <CardTitle>Top Tax Opportunities</CardTitle>
              <Link href="/tax-planning" className="text-xs text-blue-600 hover:underline">View all</Link>
            </CardHeader>
            <div className="space-y-3">
              {taxOpps.slice(0, 3).map((opp) => {
                const prospect = MOCK_PROSPECTS.find((p) => p.id === opp.prospectId);
                return (
                  <div key={opp.id} className="flex items-start gap-2.5">
                    <div className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${
                      opp.urgency === 'high' ? 'bg-red-500' : opp.urgency === 'medium' ? 'bg-amber-500' : 'bg-green-500'
                    }`} />
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-slate-700 leading-tight">{opp.title}</p>
                      <p className="text-xs text-slate-400">{prospect?.firstName} {prospect?.lastName}</p>
                      {opp.estimatedSavings && (
                        <p className="text-xs font-semibold text-green-600">
                          ~${opp.estimatedSavings.toLocaleString()} savings
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Quick actions */}
          <Card>
            <CardTitle className="mb-3">Quick Actions</CardTitle>
            <div className="space-y-2">
              <Link href="/outreach/compose" className="flex items-center gap-2 text-sm text-slate-700 hover:text-blue-600 p-2 hover:bg-slate-50 rounded-lg transition-colors">
                <span className="text-base">✉</span> Compose Outreach
              </Link>
              <Link href="/prospects" className="flex items-center gap-2 text-sm text-slate-700 hover:text-blue-600 p-2 hover:bg-slate-50 rounded-lg transition-colors">
                <span className="text-base">+</span> Add Prospect
              </Link>
              <Link href="/compliance" className="flex items-center gap-2 text-sm text-slate-700 hover:text-blue-600 p-2 hover:bg-slate-50 rounded-lg transition-colors">
                <span className="text-base">⚖</span> Compliance Status
              </Link>
              <Link href="/templates" className="flex items-center gap-2 text-sm text-slate-700 hover:text-blue-600 p-2 hover:bg-slate-50 rounded-lg transition-colors">
                <span className="text-base">📋</span> Template Library
              </Link>
            </div>
          </Card>
        </div>
      </div>

      {/* Recent campaigns */}
      <div className="mt-6">
        <Card padding="none">
          <CardHeader className="px-5 pt-5 pb-0">
            <CardTitle>Recent Campaigns</CardTitle>
            <Link href="/outreach" className="text-xs text-blue-600 hover:underline">View all</Link>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Campaign</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Recipients</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Status</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Opens</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Clicks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {MOCK_CAMPAIGNS.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-5 py-3 font-medium text-slate-800">{c.name}</td>
                    <td className="px-5 py-3 text-slate-500">{c.recipientIds.length}</td>
                    <td className="px-5 py-3">
                      <Badge variant={c.status === 'sent' ? 'success' : 'neutral'}>
                        {c.status}
                      </Badge>
                    </td>
                    <td className="px-5 py-3 text-slate-500">{c.metrics.opened}</td>
                    <td className="px-5 py-3 text-slate-500">{c.metrics.clicked}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
