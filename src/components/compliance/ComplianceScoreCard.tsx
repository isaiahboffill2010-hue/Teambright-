'use client';
import { ComplianceScore } from '@/types';
import { Card } from '@/components/ui/Card';
import { RiskBadge } from '@/components/ui/Badge';
import { clsx } from 'clsx';

interface Props {
  score: ComplianceScore;
  compact?: boolean;
}

const riskColors: Record<string, string> = {
  low: 'stroke-green-500',
  medium: 'stroke-amber-500',
  high: 'stroke-red-500',
  blocked: 'stroke-purple-600',
};

const riskBg: Record<string, string> = {
  low: 'bg-green-50 border-green-200',
  medium: 'bg-amber-50 border-amber-200',
  high: 'bg-red-50 border-red-200',
  blocked: 'bg-purple-50 border-purple-200',
};

function OpinionBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>{label}</span>
        <span className="font-mono font-medium text-slate-700">{(value * 100).toFixed(1)}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={clsx('h-full rounded-full transition-all', color)} style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  );
}

export function ComplianceScoreCard({ score, compact }: Props) {
  const { opinion, riskLevel, projectedProbability, triggeredRules } = score;

  const gaugePercent = projectedProbability * 100;
  // SVG arc gauge — path radius is 40, circumference of half-circle = π * 40 ≈ 125.6
  const arcCircumference = Math.PI * 40;

  return (
    <Card className={clsx('border', riskBg[riskLevel])}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Compliance Score</h3>
          <p className="text-xs text-slate-500 mt-0.5">Subjective Logic Assessment</p>
        </div>
        <RiskBadge level={riskLevel} />
      </div>

      {/* Gauge */}
      {!compact && (
        <div className="flex justify-center my-3">
          <svg width="100" height="58" viewBox="0 0 100 58">
            <path
              d="M 10 50 A 40 40 0 0 1 90 50"
              fill="none"
              stroke="#e2e8f0"
              strokeWidth="8"
              strokeLinecap="round"
            />
            <path
              d="M 10 50 A 40 40 0 0 1 90 50"
              fill="none"
              className={riskColors[riskLevel]}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${(gaugePercent / 100) * arcCircumference} ${arcCircumference}`}
            />
            <text x="50" y="52" textAnchor="middle" className="text-slate-800" fontSize="14" fontWeight="bold" fill="currentColor">
              {Math.round(gaugePercent)}%
            </text>
          </svg>
        </div>
      )}

      {/* Opinion components */}
      <div className="space-y-2 mb-4">
        <OpinionBar label="Lawfulness (b)" value={opinion.b} color="bg-green-500" />
        <OpinionBar label="Violation (d)" value={opinion.d} color="bg-red-500" />
        <OpinionBar label="Uncertainty (u)" value={opinion.u} color="bg-amber-400" />
      </div>

      <div className="text-xs text-slate-500 font-mono mb-3 bg-white/60 rounded-lg px-3 py-2 border border-slate-200">
        ω = (b={opinion.b.toFixed(3)}, d={opinion.d.toFixed(3)}, u={opinion.u.toFixed(3)}, a={opinion.a.toFixed(3)})
      </div>

      {/* Triggered rules */}
      {triggeredRules.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-700">Triggered Rules</p>
          {triggeredRules.map((rule) => (
            <div
              key={rule.ruleId}
              className={clsx(
                'flex items-start gap-2 text-xs rounded-lg px-3 py-2',
                rule.severity === 'critical' && 'bg-red-100 text-red-800',
                rule.severity === 'warning' && 'bg-amber-100 text-amber-800',
                rule.severity === 'info' && 'bg-sky-100 text-sky-800',
              )}
            >
              <span className="font-semibold shrink-0 mt-px">
                {rule.severity === 'critical' ? '✗' : rule.severity === 'warning' ? '⚠' : 'ℹ'}
              </span>
              <div>
                <span className="font-semibold">{rule.ruleId}</span>
                {' — '}
                {rule.description}
              </div>
            </div>
          ))}
        </div>
      )}

      {score.autoBlocked && (
        <div className="mt-3 bg-purple-100 text-purple-800 text-xs rounded-lg px-3 py-2 font-medium">
          ⛔ This message is blocked from sending. Contact your compliance officer.
        </div>
      )}
      {score.requiresReview && !score.autoBlocked && (
        <div className="mt-3 bg-amber-100 text-amber-800 text-xs rounded-lg px-3 py-2 font-medium">
          ⚠ Compliance review required before sending.
        </div>
      )}
    </Card>
  );
}
