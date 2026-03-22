'use client';
import { useState } from 'react';
import { useComplianceStore } from '@/store/useComplianceStore';
import { useProspectStore } from '@/store/useProspectStore';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge, RiskBadge } from '@/components/ui/Badge';
import { ComplianceScoreCard } from '@/components/compliance/ComplianceScoreCard';
import { scoreContent } from '@/lib/compliance/scorer';
import Link from 'next/link';

const STEPS = ['Message Review', 'Recipients', 'Certify', 'Submit'];

export default function SubmitCompliancePage() {
  const { prospects } = useProspectStore();
  const { addSubmission } = useComplianceStore();

  const [step, setStep] = useState(0);
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [certified, setCertified] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submissionId, setSubmissionId] = useState('');

  const score = subject || content
    ? scoreContent({
        subject,
        content,
        hasUnsubscribeLink: content.includes('unsubscribe'),
        consent: { hasExplicitConsent: false, isOptOut: false },
      })
    : null;

  const handleSubmit = () => {
    const id = `s${Date.now()}`;
    addSubmission({
      id,
      advisorId: 'a1',
      subject,
      messageContent: content,
      recipientCount: selectedIds.length,
      complianceScore: score!,
      status: 'pending_review',
      submittedAt: new Date().toISOString(),
    });
    setSubmissionId(id);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="p-8 max-w-2xl mx-auto flex flex-col items-center text-center pt-20">
        <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center text-3xl mb-4">⚖</div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Submitted for Review</h2>
        <p className="text-slate-500 mb-2">Your submission has been sent to your compliance officer.</p>
        <p className="text-xs font-mono text-slate-400 mb-6">Tracking ID: {submissionId}</p>
        <p className="text-xs text-slate-400 mb-8 max-w-xs">
          You&apos;ll be notified once your compliance officer has reviewed and approved or rejected the submission. Review typically takes 1&ndash;2 business days.
        </p>
        <div className="flex gap-3">
          <Link href="/compliance"><Button variant="secondary">View Submissions</Button></Link>
          <Link href="/outreach/compose"><Button>Compose New</Button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Submit for Compliance Review</h1>
          <p className="text-slate-500 text-sm mt-1">Step {step + 1} of {STEPS.length}</p>
        </div>
        <Link href="/compliance"><Button variant="ghost" size="sm">Cancel</Button></Link>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              i < step ? 'bg-green-500 text-white' : i === step ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'
            }`}>
              {i < step ? '✓' : i + 1}
            </div>
            <span className={`text-xs ${i === step ? 'font-semibold text-slate-800' : 'text-slate-400'}`}>{s}</span>
            {i < STEPS.length - 1 && <div className="h-px w-8 bg-slate-200" />}
          </div>
        ))}
      </div>

      {/* Step 0: Message Review */}
      {step === 0 && (
        <div className="grid grid-cols-5 gap-6">
          <div className="col-span-3 space-y-4">
            <Card>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Subject</label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="Email subject..."
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Message Content</label>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Paste your message content here..."
                    rows={10}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-none"
                  />
                </div>
              </div>
            </Card>
          </div>
          <div className="col-span-2">
            {score ? (
              <ComplianceScoreCard score={score} />
            ) : (
              <Card className="text-center py-8">
                <p className="text-slate-400 text-sm">Enter content to see compliance score</p>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Step 1: Recipients */}
      {step === 1 && (
        <Card>
          <h3 className="font-semibold text-slate-800 mb-3">Select Recipients</h3>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {prospects.map((p) => (
              <label key={p.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 cursor-pointer border border-transparent hover:border-slate-200">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(p.id)}
                  onChange={() => {
                    const next = selectedIds.includes(p.id)
                      ? selectedIds.filter((id) => id !== p.id)
                      : [...selectedIds, p.id];
                    setSelectedIds(next);
                  }}
                  className="rounded border-slate-300 text-blue-600"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800">{p.firstName} {p.lastName}</p>
                  <p className="text-xs text-slate-400">{p.email} · {p.enrichment?.companyName}</p>
                </div>
                <div className="flex gap-1.5">
                  {p.hasOptedOut && <Badge variant="danger" size="sm">Opted Out</Badge>}
                  {p.hasExplicitConsent && <Badge variant="success" size="sm">Consent</Badge>}
                </div>
              </label>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-3">{selectedIds.length} selected</p>
        </Card>
      )}

      {/* Step 2: Certify */}
      {step === 2 && (
        <Card>
          <h3 className="font-semibold text-slate-800 mb-4">Advisor Certification</h3>
          {score && (
            <div className="mb-4">
              <RiskBadge level={score.riskLevel} />
              <p className="text-xs text-slate-500 mt-2 font-mono">
                Compliance Opinion ω = (b={score.opinion.b.toFixed(3)}, d={score.opinion.d.toFixed(3)}, u={score.opinion.u.toFixed(3)})
              </p>
            </div>
          )}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
            <p className="text-sm font-semibold text-amber-800 mb-2">FINRA Certification Required</p>
            <p className="text-xs text-amber-700 leading-relaxed">
              By submitting this message for compliance review, I certify that: (1) the content is accurate and not misleading; (2) I have not made any guarantees of investment performance; (3) all required disclosures are included; (4) I am authorized to send this communication under FINRA Rule 2210 and applicable firm policies.
            </p>
          </div>
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={certified}
              onChange={(e) => setCertified(e.target.checked)}
              className="mt-0.5 rounded border-slate-300 text-blue-600"
            />
            <span className="text-sm text-slate-700">
              I certify that the above statements are true and accurate, and I understand that false certifications may constitute a violation of FINRA rules.
            </span>
          </label>
        </Card>
      )}

      {/* Step 3: Review & Submit */}
      {step === 3 && (
        <Card>
          <h3 className="font-semibold text-slate-800 mb-4">Review Submission</h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Subject</span>
              <span className="font-medium text-slate-800 max-w-xs truncate">{subject}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Recipients</span>
              <span className="font-medium text-slate-800">{selectedIds.length} contacts</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Risk Level</span>
              {score && <RiskBadge level={score.riskLevel} />}
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Triggered Rules</span>
              <span className="font-medium text-slate-800">{score?.triggeredRules.length ?? 0}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-500">Certification</span>
              <Badge variant="success" size="sm">Certified ✓</Badge>
            </div>
          </div>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex justify-between mt-6">
        <Button variant="secondary" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
          Back
        </Button>
        {step < STEPS.length - 1 ? (
          <Button
            onClick={() => setStep(step + 1)}
            disabled={
              (step === 0 && (!subject || !content)) ||
              (step === 1 && selectedIds.length === 0) ||
              (step === 2 && !certified)
            }
          >
            Continue →
          </Button>
        ) : (
          <Button onClick={handleSubmit}>Submit for Review</Button>
        )}
      </div>
    </div>
  );
}
