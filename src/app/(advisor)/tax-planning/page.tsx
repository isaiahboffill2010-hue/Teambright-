import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { MOCK_TAX_OPPORTUNITIES, MOCK_PROSPECTS, MOCK_TEMPLATES } from '@/lib/mockData';
import Link from 'next/link';

const strategyLabels: Record<string, string> = {
  tax_loss_harvesting: 'Tax-Loss Harvesting',
  roth_conversion: 'Roth Conversion',
  charitable_giving: 'Charitable Giving / QOZ',
  retirement_contribution: 'Retirement Contribution',
  estate_planning: 'Estate Planning',
};

const strategyIcons: Record<string, string> = {
  tax_loss_harvesting: '📉',
  roth_conversion: '🔄',
  charitable_giving: '🎁',
  retirement_contribution: '💰',
  estate_planning: '🏛',
};

export default function TaxPlanningPage() {
  const totalSavings = MOCK_TAX_OPPORTUNITIES.reduce((s, t) => s + (t.estimatedSavings ?? 0), 0);
  const highUrgency = MOCK_TAX_OPPORTUNITIES.filter((t) => t.urgency === 'high');

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Tax Planning</h1>
          <p className="text-slate-500 text-sm mt-1">
            Identified ${totalSavings.toLocaleString()} in potential client tax savings
          </p>
        </div>
      </div>

      {/* High urgency banner */}
      {highUrgency.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex gap-3">
          <span className="text-red-500 text-lg shrink-0">⚡</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-800">
              {highUrgency.length} High-Urgency Opportunity{highUrgency.length > 1 ? 'ies' : 'y'} — Year-End Deadline
            </p>
            <p className="text-xs text-red-700 mt-0.5">
              Act before December 31, 2024 to capture these savings for clients.
            </p>
          </div>
          <Link href="/outreach/compose">
            <Button size="sm" variant="danger">Reach Out Now</Button>
          </Link>
        </div>
      )}

      {/* Opportunities by prospect */}
      <div className="space-y-6">
        {MOCK_PROSPECTS.map((prospect) => {
          const opps = MOCK_TAX_OPPORTUNITIES.filter((t) => t.prospectId === prospect.id);
          if (opps.length === 0) return null;
          const prospectSavings = opps.reduce((s, t) => s + (t.estimatedSavings ?? 0), 0);

          return (
            <div key={prospect.id}>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-sm font-bold">
                  {prospect.firstName[0]}{prospect.lastName[0]}
                </div>
                <div>
                  <h3 className="font-semibold text-slate-800">{prospect.firstName} {prospect.lastName}</h3>
                  <p className="text-xs text-slate-400">{prospect.enrichment?.jobTitle} · {prospect.enrichment?.companyName}</p>
                </div>
                <div className="ml-auto flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-sm font-bold text-green-600">${prospectSavings.toLocaleString()}</p>
                    <p className="text-xs text-slate-400">potential savings</p>
                  </div>
                  <Link href="/outreach/compose">
                    <Button size="sm" variant="secondary">Reach Out</Button>
                  </Link>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 ml-11">
                {opps.map((opp) => {
                  const suggestedTemplate = opp.suggestedTemplateId
                    ? MOCK_TEMPLATES.find((t) => t.id === opp.suggestedTemplateId)
                    : null;

                  return (
                    <Card key={opp.id} className="border border-slate-200">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span>{strategyIcons[opp.strategyType]}</span>
                          <span className="text-xs font-medium text-slate-600">
                            {strategyLabels[opp.strategyType]}
                          </span>
                        </div>
                        <Badge
                          size="sm"
                          variant={opp.urgency === 'high' ? 'danger' : opp.urgency === 'medium' ? 'warning' : 'success'}
                        >
                          {opp.urgency}
                        </Badge>
                      </div>
                      <h4 className="text-sm font-semibold text-slate-800 mb-1">{opp.title}</h4>
                      <p className="text-xs text-slate-500 leading-relaxed mb-2">{opp.description}</p>
                      <div className="flex items-center justify-between">
                        {opp.estimatedSavings && (
                          <span className="text-sm font-bold text-green-600">
                            ~${opp.estimatedSavings.toLocaleString()}
                          </span>
                        )}
                        {opp.deadline && (
                          <span className="text-xs text-red-600 font-medium">
                            ⏰ Due {new Date(opp.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                        )}
                      </div>
                      {suggestedTemplate && (
                        <div className="mt-2 pt-2 border-t border-slate-100">
                          <p className="text-xs text-slate-400">
                            Suggested template:{' '}
                            <span className="text-blue-600 font-medium">{suggestedTemplate.name}</span>
                          </p>
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Disclaimer */}
      <div className="mt-8 bg-slate-100 rounded-xl p-4">
        <p className="text-xs text-slate-500 leading-relaxed">
          <strong>Important Disclosure:</strong> Tax planning opportunities shown are for illustrative purposes only and are based on estimated prospect data. AdvisorFlow does not provide tax advice. All tax strategies should be reviewed by a qualified tax professional. Advisors must ensure all client communications comply with FINRA Rule 2210 and applicable regulations.
        </p>
      </div>
    </div>
  );
}
