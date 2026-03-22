// ─── User & Session ────────────────────────────────────────────────────────

export type UserRole = 'advisor' | 'compliance_officer' | 'admin';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  firmId: string;
  crdNumber?: string;
  avatarUrl?: string;
}

// ─── Prospect ──────────────────────────────────────────────────────────────

export type ProspectStatus =
  | 'new'
  | 'contacted'
  | 'engaged'
  | 'qualified'
  | 'closed_won'
  | 'closed_lost';

export interface EnrichmentData {
  linkedinUrl?: string;
  location?: string;
  companyName?: string;
  jobTitle?: string;
  estimatedAUM?: number;
  investorType?: 'retail' | 'accredited' | 'institutional';
  stateOfResidence?: string;
  enrichedAt: string;
  confidenceScore: number;
}

export interface TaxProfile {
  estimatedIncome?: number;
  filingStatus?: 'single' | 'married_joint' | 'married_separate' | 'head_of_household';
  capitalGainsExposure?: 'low' | 'medium' | 'high';
  hasRetirementAccounts?: boolean;
  taxablePortfolioSize?: number;
}

export interface ProspectScoring {
  icpScore: number;           // 0–100 ICP match score
  urgencyScore: number;       // 0–100 urgency / "why now" score
  icpCategory: string;        // e.g. "Tech Executive", "Medical Professional"
  summary: string;            // 1-2 sentence overview
  matchReasons: string[];     // why they match ICP
  whyNowReasons: string[];    // life events / signals
  potentialConcerns: string[];
  outreachAngle: string;      // recommended personalized angle
}

export interface Prospect {
  id: string;
  advisorId: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  status: ProspectStatus;
  source: 'manual' | 'csv_import' | 'clay_enrichment' | 'referral';
  enrichment?: EnrichmentData;
  taxProfile?: TaxProfile;
  scoring?: ProspectScoring;
  tags: string[];
  notes: string;
  lastContactedAt?: string;
  hasOptedOut?: boolean;
  hasExplicitConsent?: boolean;
  createdAt: string;
  updatedAt: string;
}

// ─── Compliance ────────────────────────────────────────────────────────────

export interface ComplianceOpinion {
  b: number;   // belief / lawfulness evidence
  d: number;   // disbelief / violation evidence
  u: number;   // uncertainty
  a: number;   // base rate (prior)
}

export type RiskLevel = 'low' | 'medium' | 'high' | 'blocked';

export interface TriggeredRule {
  ruleId: string;
  ruleName: string;
  description: string;
  severity: 'info' | 'warning' | 'critical';
  regulation: string;
}

export interface ComplianceScore {
  opinion: ComplianceOpinion;
  riskLevel: RiskLevel;
  projectedProbability: number;
  triggeredRules: TriggeredRule[];
  requiresReview: boolean;
  autoBlocked: boolean;
  scoredAt: string;
}

export type SubmissionStatus =
  | 'draft'
  | 'pending_review'
  | 'under_review'
  | 'approved'
  | 'rejected'
  | 'revision_requested';

export interface ComplianceSubmission {
  id: string;
  advisorId: string;
  officerId?: string;
  subject: string;
  messageContent: string;
  templateId?: string;
  recipientCount: number;
  complianceScore: ComplianceScore;
  status: SubmissionStatus;
  officerNotes?: string;
  submittedAt: string;
  reviewedAt?: string;
}

// ─── Template ──────────────────────────────────────────────────────────────

export type TemplateCategory =
  | 'introduction'
  | 'follow_up'
  | 'tax_planning'
  | 'market_update'
  | 'referral_request'
  | 'annual_review';

export interface Template {
  id: string;
  name: string;
  category: TemplateCategory;
  subject: string;
  bodyHtml: string;
  approvalStatus: 'approved' | 'pending' | 'rejected';
  complianceNotes?: string;
  usageCount: number;
  createdAt: string;
}

// ─── Campaign / Outreach ───────────────────────────────────────────────────

export type CampaignStatus = 'draft' | 'scheduled' | 'sent' | 'paused';

export interface Campaign {
  id: string;
  advisorId: string;
  name: string;
  subject: string;
  bodyHtml: string;
  channel: 'resend' | 'gmail';
  recipientIds: string[];
  complianceSubmissionId?: string;
  status: CampaignStatus;
  sentAt?: string;
  metrics: {
    totalSent: number;
    opened: number;
    clicked: number;
    bounced: number;
  };
  createdAt: string;
}

// ─── Tax ───────────────────────────────────────────────────────────────────

export type TaxStrategyType =
  | 'tax_loss_harvesting'
  | 'roth_conversion'
  | 'charitable_giving'
  | 'retirement_contribution'
  | 'estate_planning';

export interface TaxOpportunity {
  id: string;
  prospectId: string;
  strategyType: TaxStrategyType;
  title: string;
  description: string;
  estimatedSavings?: number;
  urgency: 'low' | 'medium' | 'high';
  deadline?: string;
  suggestedTemplateId?: string;
}
