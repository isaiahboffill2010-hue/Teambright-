import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { MOCK_CAMPAIGNS, MOCK_PROSPECTS } from '@/lib/mockData';
import Link from 'next/link';

export default function OutreachPage() {
  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Outreach Campaigns</h1>
          <p className="text-slate-500 text-sm mt-1">{MOCK_CAMPAIGNS.length} campaigns</p>
        </div>
        <Link href="/outreach/compose">
          <Button>+ Compose New</Button>
        </Link>
      </div>

      <div className="space-y-4">
        {MOCK_CAMPAIGNS.map((c) => {
          const recipients = MOCK_PROSPECTS.filter((p) => c.recipientIds.includes(p.id));
          const openRate = c.metrics.totalSent > 0 ? Math.round((c.metrics.opened / c.metrics.totalSent) * 100) : 0;
          const clickRate = c.metrics.totalSent > 0 ? Math.round((c.metrics.clicked / c.metrics.totalSent) * 100) : 0;

          return (
            <Card key={c.id}>
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-slate-800">{c.name}</h3>
                    <Badge variant={c.status === 'sent' ? 'success' : c.status === 'draft' ? 'neutral' : 'info'}>
                      {c.status}
                    </Badge>
                    <Badge variant="default">{c.channel}</Badge>
                  </div>
                  <p className="text-sm text-slate-500 mb-3">{c.subject}</p>

                  <div className="flex items-center gap-4">
                    {/* Recipients */}
                    <div className="flex -space-x-1.5">
                      {recipients.slice(0, 3).map((p) => (
                        <div
                          key={p.id}
                          className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 border-2 border-white flex items-center justify-center text-white text-xs font-bold"
                          title={`${p.firstName} ${p.lastName}`}
                        >
                          {p.firstName[0]}
                        </div>
                      ))}
                      {recipients.length > 3 && (
                        <div className="w-6 h-6 rounded-full bg-slate-200 border-2 border-white flex items-center justify-center text-xs text-slate-600 font-medium">
                          +{recipients.length - 3}
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-slate-400">{recipients.length} recipients</span>
                  </div>
                </div>

                {/* Metrics */}
                {c.status === 'sent' && (
                  <div className="flex gap-6 shrink-0 ml-6">
                    <div className="text-center">
                      <p className="text-xl font-bold text-slate-900">{openRate}%</p>
                      <p className="text-xs text-slate-400">Open Rate</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xl font-bold text-slate-900">{clickRate}%</p>
                      <p className="text-xs text-slate-400">Click Rate</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xl font-bold text-slate-900">{c.metrics.totalSent}</p>
                      <p className="text-xs text-slate-400">Sent</p>
                    </div>
                  </div>
                )}

                {c.status === 'draft' && (
                  <Link href="/outreach/compose">
                    <Button variant="secondary" size="sm">Continue Draft</Button>
                  </Link>
                )}
              </div>
              {c.sentAt && (
                <p className="text-xs text-slate-400 mt-3">
                  Sent {new Date(c.sentAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </p>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
