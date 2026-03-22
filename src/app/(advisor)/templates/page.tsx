import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { MOCK_TEMPLATES } from '@/lib/mockData';
import Link from 'next/link';

const categoryColors: Record<string, string> = {
  introduction: 'bg-blue-100 text-blue-700',
  follow_up: 'bg-slate-100 text-slate-700',
  tax_planning: 'bg-green-100 text-green-700',
  market_update: 'bg-purple-100 text-purple-700',
  referral_request: 'bg-amber-100 text-amber-700',
  annual_review: 'bg-sky-100 text-sky-700',
};

export default function TemplatesPage() {
  const approved = MOCK_TEMPLATES.filter((t) => t.approvalStatus === 'approved');
  const pending = MOCK_TEMPLATES.filter((t) => t.approvalStatus === 'pending');

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Template Library</h1>
          <p className="text-slate-500 text-sm mt-1">{approved.length} approved templates ready to use</p>
        </div>
        <Button size="sm">Request New Template</Button>
      </div>

      {/* Compliance info banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex gap-3">
        <span className="text-blue-500 text-lg shrink-0">ℹ</span>
        <div>
          <p className="text-sm font-semibold text-blue-800">Pre-approved templates</p>
          <p className="text-xs text-blue-700 mt-0.5">
            These templates have been reviewed and approved by your compliance officer. Using an approved template provides the highest compliance confidence score when composing outreach.
          </p>
        </div>
      </div>

      {/* Approved */}
      <div className="mb-8">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Approved</h2>
        <div className="grid grid-cols-2 gap-4">
          {approved.map((t) => (
            <Card key={t.id} className="hover:border-blue-300 transition-colors cursor-pointer">
              <div className="flex items-start justify-between mb-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${categoryColors[t.category] ?? 'bg-slate-100 text-slate-700'}`}>
                  {t.category.replace('_', ' ')}
                </span>
                <Badge variant="success" size="sm">Approved</Badge>
              </div>
              <h3 className="font-semibold text-slate-800 mb-1 text-sm">{t.name}</h3>
              <p className="text-xs text-slate-500 mb-3 font-mono truncate">{t.subject}</p>

              {t.complianceNotes && (
                <p className="text-xs text-green-700 bg-green-50 rounded-lg px-2.5 py-1.5 mb-3">
                  ✓ {t.complianceNotes}
                </p>
              )}

              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">{t.usageCount} uses</span>
                <Link href="/outreach/compose">
                  <Button size="sm" variant="secondary">Use Template</Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Pending */}
      {pending.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Pending Review</h2>
          <div className="grid grid-cols-2 gap-4">
            {pending.map((t) => (
              <Card key={t.id} className="opacity-75">
                <div className="flex items-start justify-between mb-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${categoryColors[t.category] ?? 'bg-slate-100 text-slate-700'}`}>
                    {t.category.replace('_', ' ')}
                  </span>
                  <Badge variant="warning" size="sm">Pending</Badge>
                </div>
                <h3 className="font-semibold text-slate-800 mb-1 text-sm">{t.name}</h3>
                <p className="text-xs text-slate-500 mb-3 font-mono truncate">{t.subject}</p>
                <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-2.5 py-1.5">
                  ⏳ Awaiting compliance officer review
                </p>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
