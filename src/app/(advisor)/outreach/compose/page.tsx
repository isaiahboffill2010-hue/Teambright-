'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { useComplianceStore } from '@/store/useComplianceStore';
import { useOutreachStore } from '@/store/useOutreachStore';
import { useProspectStore } from '@/store/useProspectStore';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { RiskBadge, Badge } from '@/components/ui/Badge';
import { ComplianceScoreCard } from '@/components/compliance/ComplianceScoreCard';
import { ComplianceScore } from '@/types';
import { scoreContent } from '@/lib/compliance/scorer';
import Link from 'next/link';

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

const MERGE_FIELDS = ['{{first_name}}', '{{last_name}}', '{{advisor_name}}', '{{firm_name}}', '{{industry}}', '{{firm_address}}', '{{unsubscribe_link}}'];

export default function ComposePage() {
  const { prospects } = useProspectStore();
  const {
    composerSubject, setComposerSubject,
    composerBody, setComposerBody,
    selectedRecipientIds, setRecipients,
    selectedTemplateId, setTemplate,
    templates,
  } = useOutreachStore();
  const { currentScore, setScore, setScoringInProgress } = useComplianceStore();

  const [hasUnsubLink, setHasUnsubLink] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);

  const debouncedSubject = useDebounce(composerSubject, 700);
  const debouncedBody = useDebounce(composerBody, 700);

  // Score content whenever it changes
  useEffect(() => {
    if (!debouncedSubject && !debouncedBody) {
      setScore(null);
      return;
    }
    setScoringInProgress(true);
    const firstRecipient = prospects.find((p) => selectedRecipientIds.includes(p.id));
    const score = scoreContent({
      subject: debouncedSubject,
      content: debouncedBody,
      hasUnsubscribeLink: hasUnsubLink || debouncedBody.includes('unsubscribe'),
      consent: {
        hasExplicitConsent: firstRecipient?.hasExplicitConsent ?? false,
        isOptOut: firstRecipient?.hasOptedOut ?? false,
      },
    });
    setScore(score);
    setScoringInProgress(false);
  }, [debouncedSubject, debouncedBody, hasUnsubLink, selectedRecipientIds, prospects, setScore, setScoringInProgress]);

  const loadTemplate = (templateId: string) => {
    const t = templates.find((t) => t.id === templateId);
    if (!t) return;
    setTemplate(templateId);
    setComposerSubject(t.subject);
    setComposerBody(t.bodyHtml.replace(/<[^>]+>/g, ''));
    setShowTemplates(false);
  };

  const insertMergeField = (field: string) => {
    setComposerBody(composerBody + field);
  };

  const handleSend = async () => {
    if (!currentScore || currentScore.autoBlocked) return;
    if (currentScore.requiresReview) {
      alert('This message requires compliance review before sending. Please submit for review.');
      return;
    }
    setIsSending(true);
    await new Promise((r) => setTimeout(r, 1500)); // simulate send
    setIsSending(false);
    setSent(true);
  };

  if (sent) {
    return (
      <div className="p-8 max-w-4xl mx-auto flex flex-col items-center justify-center min-h-64">
        <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center text-2xl mb-4">✓</div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Email Sent</h2>
        <p className="text-slate-500 mb-6">Your outreach has been sent to {selectedRecipientIds.length} recipient{selectedRecipientIds.length !== 1 ? 's' : ''}.</p>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => { setSent(false); setComposerSubject(''); setComposerBody(''); setRecipients([]); }}>
            New Email
          </Button>
          <Link href="/outreach"><Button>View Campaigns</Button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Compose Outreach</h1>
          <p className="text-slate-500 text-sm mt-1">Real-time compliance scoring powered by Subjective Logic</p>
        </div>
        <Link href="/outreach"><Button variant="ghost" size="sm">← Back</Button></Link>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Composer — left 2/3 */}
        <div className="col-span-2 space-y-4">
          {/* Template picker */}
          <Card>
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-slate-700">Template Library</p>
              <Button variant="ghost" size="sm" onClick={() => setShowTemplates(!showTemplates)}>
                {showTemplates ? 'Hide' : 'Browse Templates'}
              </Button>
            </div>
            {showTemplates && (
              <div className="grid grid-cols-2 gap-2">
                {templates.filter((t) => t.approvalStatus === 'approved').map((t) => (
                  <button
                    key={t.id}
                    onClick={() => loadTemplate(t.id)}
                    className="text-left p-3 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                  >
                    <p className="text-xs font-semibold text-slate-800">{t.name}</p>
                    <p className="text-xs text-slate-400 capitalize">{t.category.replace('_', ' ')}</p>
                    <p className="text-xs text-green-600 mt-1">✓ Approved · {t.usageCount} uses</p>
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Recipients */}
          <Card>
            <p className="text-sm font-semibold text-slate-700 mb-3">Recipients</p>
            <div className="grid grid-cols-2 gap-2 max-h-36 overflow-y-auto">
              {prospects.map((p) => (
                <label key={p.id} className="flex items-center gap-2 cursor-pointer p-2 rounded-lg hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={selectedRecipientIds.includes(p.id)}
                    onChange={() => {
                      const next = selectedRecipientIds.includes(p.id)
                        ? selectedRecipientIds.filter((id) => id !== p.id)
                        : [...selectedRecipientIds, p.id];
                      setRecipients(next);
                    }}
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-700 truncate">{p.firstName} {p.lastName}</p>
                    <p className="text-xs text-slate-400 truncate">{p.email}</p>
                  </div>
                  {p.hasOptedOut && <Badge variant="danger" size="sm">OPT-OUT</Badge>}
                </label>
              ))}
            </div>
            {selectedRecipientIds.length > 0 && (
              <p className="text-xs text-slate-500 mt-2">{selectedRecipientIds.length} selected</p>
            )}
          </Card>

          {/* Email composer */}
          <Card>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Subject</label>
                <input
                  type="text"
                  value={composerSubject}
                  onChange={(e) => setComposerSubject(e.target.value)}
                  placeholder="Enter subject line..."
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Merge field toolbar */}
              <div>
                <p className="text-xs text-slate-400 mb-1.5">Insert merge field:</p>
                <div className="flex flex-wrap gap-1.5">
                  {MERGE_FIELDS.map((f) => (
                    <button
                      key={f}
                      onClick={() => insertMergeField(f)}
                      className="text-xs px-2 py-1 bg-slate-100 hover:bg-blue-100 hover:text-blue-700 rounded text-slate-600 font-mono transition-colors"
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Message</label>
                <textarea
                  value={composerBody}
                  onChange={(e) => setComposerBody(e.target.value)}
                  placeholder="Compose your message..."
                  rows={12}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-none leading-relaxed"
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={hasUnsubLink}
                  onChange={(e) => setHasUnsubLink(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600"
                />
                Include unsubscribe link (required by CAN-SPAM)
              </label>
            </div>
          </Card>
        </div>

        {/* Right sidebar — compliance */}
        <div className="space-y-4">
          {/* Score card */}
          {currentScore ? (
            <ComplianceScoreCard score={currentScore} />
          ) : (
            <Card className="border border-slate-200">
              <p className="text-sm font-semibold text-slate-700 mb-1">Compliance Score</p>
              <p className="text-xs text-slate-400">Start typing to see real-time compliance analysis.</p>
              <div className="mt-4 h-12 bg-slate-100 rounded-lg animate-pulse" />
            </Card>
          )}

          {/* Send panel */}
          <Card>
            <p className="text-sm font-semibold text-slate-700 mb-3">Send Options</p>
            <div className="space-y-3">
              {currentScore && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Risk Level</span>
                  <RiskBadge level={currentScore.riskLevel} />
                </div>
              )}
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">Recipients</span>
                <span className="font-medium text-slate-700">{selectedRecipientIds.length}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">Channel</span>
                <span className="font-medium text-slate-700">Resend</span>
              </div>

              {currentScore?.autoBlocked ? (
                <div className="bg-purple-100 text-purple-800 text-xs rounded-lg px-3 py-2 text-center font-medium">
                  ⛔ Blocked — compliance review required
                </div>
              ) : currentScore?.requiresReview ? (
                <Link href="/compliance/submit">
                  <Button variant="secondary" className="w-full" size="sm">
                    Submit for Review
                  </Button>
                </Link>
              ) : (
                <Button
                  onClick={handleSend}
                  loading={isSending}
                  disabled={!composerSubject || !composerBody || selectedRecipientIds.length === 0}
                  className="w-full"
                  size="sm"
                >
                  Send via Resend
                </Button>
              )}
              {currentScore?.riskLevel === 'low' && (
                <p className="text-xs text-green-600 text-center">✓ Cleared for direct send</p>
              )}
            </div>
          </Card>

          {/* FINRA reminder */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-xs font-semibold text-blue-800 mb-1">FINRA Rule 2210</p>
            <p className="text-xs text-blue-700 leading-relaxed">
              All client communications must be fair, balanced, and not misleading. Medium and high-risk messages require compliance officer approval.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
