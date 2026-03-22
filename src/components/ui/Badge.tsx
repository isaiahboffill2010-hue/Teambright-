'use client';
import { clsx } from 'clsx';
import { RiskLevel, ProspectStatus, SubmissionStatus } from '@/types';

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'neutral';

const variantClasses: Record<Variant, string> = {
  default: 'bg-blue-100 text-blue-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-amber-100 text-amber-800',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-sky-100 text-sky-800',
  purple: 'bg-purple-100 text-purple-800',
  neutral: 'bg-slate-100 text-slate-700',
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
  size?: 'sm' | 'md';
}

export function Badge({ children, variant = 'default', className, size = 'md' }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  const map: Record<RiskLevel, { label: string; variant: Variant }> = {
    low: { label: 'Low Risk', variant: 'success' },
    medium: { label: 'Medium Risk', variant: 'warning' },
    high: { label: 'High Risk', variant: 'danger' },
    blocked: { label: 'Blocked', variant: 'purple' },
  };
  const { label, variant } = map[level];
  return <Badge variant={variant}>{label}</Badge>;
}

export function StatusBadge({ status }: { status: ProspectStatus }) {
  const map: Record<ProspectStatus, { label: string; variant: Variant }> = {
    new: { label: 'New', variant: 'info' },
    contacted: { label: 'Contacted', variant: 'default' },
    engaged: { label: 'Engaged', variant: 'warning' },
    qualified: { label: 'Qualified', variant: 'purple' },
    closed_won: { label: 'Won', variant: 'success' },
    closed_lost: { label: 'Lost', variant: 'neutral' },
  };
  const { label, variant } = map[status];
  return <Badge variant={variant}>{label}</Badge>;
}

export function SubmissionStatusBadge({ status }: { status: SubmissionStatus }) {
  const map: Record<SubmissionStatus, { label: string; variant: Variant }> = {
    draft: { label: 'Draft', variant: 'neutral' },
    pending_review: { label: 'Pending Review', variant: 'warning' },
    under_review: { label: 'Under Review', variant: 'info' },
    approved: { label: 'Approved', variant: 'success' },
    rejected: { label: 'Rejected', variant: 'danger' },
    revision_requested: { label: 'Revision Requested', variant: 'purple' },
  };
  const { label, variant } = map[status];
  return <Badge variant={variant}>{label}</Badge>;
}
