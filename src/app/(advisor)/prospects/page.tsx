'use client';
import { useState } from 'react';
import { useProspectStore } from '@/store/useProspectStore';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusBadge, Badge } from '@/components/ui/Badge';
import { Prospect } from '@/types';
import Link from 'next/link';

function ProspectDrawer({ prospect, onClose }: { prospect: Prospect; onClose: () => void }) {
  const taxP = prospect.taxProfile;
  const enrich = prospect.enrichment;

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-96 bg-white shadow-xl overflow-y-auto">
        {/* Header */}
        <div className="bg-slate-900 px-5 py-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white font-bold">
                {prospect.firstName[0]}{prospect.lastName[0]}
              </div>
              <div>
                <h2 className="text-white font-semibold">{prospect.firstName} {prospect.lastName}</h2>
                <p className="text-slate-400 text-xs">{enrich?.jobTitle} · {enrich?.companyName}</p>
              </div>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
          </div>
          <div className="flex gap-2 mt-3">
            <StatusBadge status={prospect.status} />
            {prospect.hasExplicitConsent && <Badge variant="success" size="sm">Consent ✓</Badge>}
            {prospect.hasOptedOut && <Badge variant="danger" size="sm">Opted Out</Badge>}
          </div>
        </div>

        <div className="p-5 space-y-5">
          {/* Contact */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Contact</h3>
            <div className="space-y-1.5 text-sm text-slate-700">
              <p>✉ {prospect.email}</p>
              {prospect.phone && <p>📞 {prospect.phone}</p>}
            </div>
          </div>

          {/* Enrichment */}
          {enrich && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Enrichment</h3>
                <Badge variant="info" size="sm">{Math.round(enrich.confidenceScore * 100)}% confidence</Badge>
              </div>
              <div className="space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Est. AUM</span>
                  <span className="font-semibold text-slate-800">
                    ${(enrich.estimatedAUM! / 1_000_000).toFixed(1)}M
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Investor Type</span>
                  <span className="text-slate-700 capitalize">{enrich.investorType}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">State</span>
                  <span className="text-slate-700">{enrich.stateOfResidence}</span>
                </div>
                {enrich.linkedinUrl && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">LinkedIn</span>
                    <span className="text-blue-600 text-xs truncate max-w-32">View Profile</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tax Profile */}
          {taxP && (
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Tax Profile</h3>
              <div className="space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Est. Income</span>
                  <span className="font-semibold text-slate-800">
                    ${(taxP.estimatedIncome! / 1000).toFixed(0)}K/yr
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Filing Status</span>
                  <span className="text-slate-700 capitalize">{taxP.filingStatus?.replace('_', ' ')}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Cap. Gains Exposure</span>
                  <Badge
                    size="sm"
                    variant={taxP.capitalGainsExposure === 'high' ? 'danger' : taxP.capitalGainsExposure === 'medium' ? 'warning' : 'success'}
                  >
                    {taxP.capitalGainsExposure}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Taxable Portfolio</span>
                  <span className="text-slate-700">
                    ${(taxP.taxablePortfolioSize! / 1_000_000).toFixed(1)}M
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Notes */}
          {prospect.notes && (
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Notes</h3>
              <p className="text-sm text-slate-600 leading-relaxed">{prospect.notes}</p>
            </div>
          )}

          {/* Tags */}
          {prospect.tags.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Tags</h3>
              <div className="flex flex-wrap gap-1.5">
                {prospect.tags.map((t) => (
                  <Badge key={t} variant="neutral" size="sm">{t}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <Link href="/outreach/compose" className="flex-1">
              <Button variant="primary" size="sm" className="w-full">Send Email</Button>
            </Link>
            <Link href="/tax-planning">
              <Button variant="secondary" size="sm">Tax Opps</Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ProspectsPage() {
  const { filteredProspects, filters, setFilters } = useProspectStore();
  const [activeProspect, setActiveProspect] = useState<Prospect | null>(null);

  const prospects = filteredProspects();

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Prospects</h1>
          <p className="text-slate-500 text-sm mt-1">{prospects.length} contacts in your pipeline</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm">Import CSV</Button>
          <Button size="sm">+ Add Prospect</Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <input
          type="text"
          placeholder="Search by name, email, company..."
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value })}
          className="flex-1 max-w-xs px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={filters.status}
          onChange={(e) => setFilters({ status: e.target.value as typeof filters.status })}
          className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="engaged">Engaged</option>
          <option value="qualified">Qualified</option>
          <option value="closed_won">Won</option>
          <option value="closed_lost">Lost</option>
        </select>
      </div>

      {/* Table */}
      <Card padding="none">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/50">
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Name</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Company</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Est. AUM</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Status</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Consent</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Tax Exposure</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {prospects.map((p) => (
              <tr
                key={p.id}
                className="hover:bg-slate-50 cursor-pointer transition-colors"
                onClick={() => setActiveProspect(p)}
              >
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
                      {p.firstName[0]}{p.lastName[0]}
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">{p.firstName} {p.lastName}</p>
                      <p className="text-xs text-slate-400">{p.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3.5 text-slate-600">
                  <p>{p.enrichment?.companyName ?? '—'}</p>
                  <p className="text-xs text-slate-400">{p.enrichment?.jobTitle}</p>
                </td>
                <td className="px-5 py-3.5 font-semibold text-slate-800">
                  {p.enrichment?.estimatedAUM
                    ? `$${(p.enrichment.estimatedAUM / 1_000_000).toFixed(1)}M`
                    : '—'}
                </td>
                <td className="px-5 py-3.5"><StatusBadge status={p.status} /></td>
                <td className="px-5 py-3.5">
                  {p.hasOptedOut ? (
                    <Badge variant="danger" size="sm">Opted Out</Badge>
                  ) : p.hasExplicitConsent ? (
                    <Badge variant="success" size="sm">Consented</Badge>
                  ) : (
                    <Badge variant="neutral" size="sm">Unknown</Badge>
                  )}
                </td>
                <td className="px-5 py-3.5">
                  {p.taxProfile?.capitalGainsExposure ? (
                    <Badge
                      size="sm"
                      variant={p.taxProfile.capitalGainsExposure === 'high' ? 'danger' : p.taxProfile.capitalGainsExposure === 'medium' ? 'warning' : 'success'}
                    >
                      {p.taxProfile.capitalGainsExposure}
                    </Badge>
                  ) : '—'}
                </td>
                <td className="px-5 py-3.5 text-slate-400 text-xs capitalize">{p.source.replace('_', ' ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {prospects.length === 0 && (
          <div className="text-center py-12 text-slate-400 text-sm">No prospects match your filters.</div>
        )}
      </Card>

      {activeProspect && (
        <ProspectDrawer prospect={activeProspect} onClose={() => setActiveProspect(null)} />
      )}
    </div>
  );
}
