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

function UrgencyBar({ score }: { score: number }) {
  const color = score >= 85 ? 'bg-red-500' : score >= 70 ? 'bg-amber-500' : 'bg-green-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-semibold text-slate-600 w-6 text-right">{score}</span>
    </div>
  );
}

export default function DashboardPage() {
  const totalAUM = MOCK_PROSPECTS.reduce((s, p) => s + (p.enrichment?.estimatedAUM ?? 0), 0);
  const taxOpps = MOCK_TAX_OPPORTUNITIES;
  const totalSavings = taxOpps.reduce((s, t) => s + (t.estimatedSavings ?? 0), 0);
  const pendingReviews = MOCK_SUBMISSIONS.filter((s) => s.status === 'pending_review').length;

  // Hot leads: sorted by urgency score descending, top 4
  const hotLeads = [...MOCK_PROSPECTS]
    .filter((p) => p.scoring)
    .sort((a, b) => (b.scoring?.urgencyScore ?? 0) - (a.scoring?.urgencyScore ?? 0))
    .slice(0, 4);

  const now = new Date();
  const greeting = now.getHours() < 12 ? 'Good morning' : now.getHours() < 17 ? 'Good afternoon' : 'Good evening';
  const dateLabel = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <Link href="/" className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors">
            ← Back
          </Link>
          <form action="/auth/signout" method="POST">
            <button type="submit" className="text-xs text-slate-400 hover:text-slate-700 transition-colors">
              Sign out
            </button>
          </form>
        </div>
        <h1 className="text-2xl font-bold text-slate-900">{greeting}, Alex</h1>
        <p className="text-slate-500 mt-1">Here&apos;s your pipeline overview for {dateLabel}.</p>
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
        {/* Hot Leads — sorted by urgency */}
        <div className="col-span-2">
          <Card padding="none">
            <CardHeader className="px-5 pt-5 pb-0">
              <div>
                <CardTitle>Hot Leads</CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">Ranked by urgency score — act before the window closes</p>
              </div>
              <Link href="/prospects" className="text-xs text-blue-600 hover:underline shrink-0">View all</Link>
            </CardHeader>
            <div className="divide-y divide-slate-100">
              {hotLeads.map((p) => (
                <div key={p.id} className="flex items-center gap-3 px-5 py-3.5 hover:bg-slate-50 transition-colors">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
                    {p.firstName[0]}{p.lastName[0]}
                  </div>
                  <Link href="/prospects" className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <p className="text-sm font-medium text-slate-800">{p.firstName} {p.lastName}</p>
                      {p.scoring && (
                        <span className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded font-medium">
                          {p.scoring.icpCategory}
                        </span>
                      )}
                    </div>
                    {p.scoring?.whyNowReasons[0] && (
                      <p className="text-xs text-amber-700 font-medium truncate">
                        ⚡ {p.scoring.whyNowReasons[0]}
                      </p>
                    )}
                    {p.scoring && (
                      <div className="mt-1.5 max-w-48">
                        <UrgencyBar score={p.scoring.urgencyScore} />
                      </div>
                    )}
                  </Link>
                  <div className="text-right shrink-0">
                    <p className="text-xs font-semibold text-slate-700">
                      ${((p.enrichment?.estimatedAUM ?? 0) / 1_000_000).toFixed(1)}M
                    </p>
                    {p.scoring && (
                      <p className="text-xs text-slate-400">ICP {p.scoring.icpScore}</p>
                    )}
                    <Link
                      href="/outreach/compose"
                      className="mt-1 inline-block text-xs px-2 py-0.5 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                    >
                      Draft →
                    </Link>
                  </div>
                </div>
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
