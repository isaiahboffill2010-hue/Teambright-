import { Prospect, Template, Campaign, ComplianceSubmission, TaxOpportunity } from '@/types';
import { IMPORTED_PROSPECTS } from './prospectData';

const SEED_PROSPECTS: Prospect[] = [
  {
    id: 'p1',
    advisorId: 'a1',
    firstName: 'Robert',
    lastName: 'Chen',
    email: 'robert.chen@goldenstate.com',
    phone: '+1 (415) 555-0182',
    status: 'engaged',
    source: 'referral',
    enrichment: {
      companyName: 'Golden State Capital Group',
      jobTitle: 'CFO',
      estimatedAUM: 4_200_000,
      investorType: 'accredited',
      stateOfResidence: 'CA',
      enrichedAt: '2024-11-10T14:22:00Z',
      confidenceScore: 0.91,
    },
    taxProfile: {
      estimatedIncome: 620_000,
      filingStatus: 'married_joint',
      capitalGainsExposure: 'high',
      hasRetirementAccounts: true,
      taxablePortfolioSize: 2_800_000,
    },
    tags: ['golf', 'high-net-worth', 'tech-exec'],
    notes: 'Met at Pebble Beach club event. Interested in tax-efficient strategies.',
    scoring: {
      icpScore: 91,
      urgencyScore: 87,
      icpCategory: 'Tech Executive',
      summary: 'CFO at Golden State Capital with $4.2M in investable assets and high capital gains exposure heading into year-end.',
      matchReasons: ['High AUM ($4.2M)', 'Accredited investor in CA', 'Senior finance exec', 'Married filing jointly — tax optimization upside'],
      whyNowReasons: ['Q4 year-end tax-loss harvesting window closes Dec 31', 'Unrealized losses of ~$180K available to harvest', 'Potential Roth conversion window before 2026 rate change'],
      potentialConcerns: ['Existing advisor relationship likely', 'High earner — sensitive to promissory language'],
      outreachAngle: 'Lead with year-end tax-loss harvesting deadline and the specific $180K opportunity. Keep CTA low-commitment — offer a 20-min year-end tax review call.',
    },
    hasExplicitConsent: true,
    hasOptedOut: false,
    lastContactedAt: '2024-12-01T09:00:00Z',
    createdAt: '2024-10-15T00:00:00Z',
    updatedAt: '2024-12-01T09:00:00Z',
  },
  {
    id: 'p2',
    advisorId: 'a1',
    firstName: 'Sarah',
    lastName: 'Nguyen',
    email: 's.nguyen@horizonventures.io',
    phone: '+1 (628) 555-0247',
    status: 'contacted',
    source: 'clay_enrichment',
    enrichment: {
      companyName: 'Horizon Ventures',
      jobTitle: 'Managing Partner',
      estimatedAUM: 8_500_000,
      investorType: 'institutional',
      stateOfResidence: 'CA',
      enrichedAt: '2024-11-20T10:00:00Z',
      confidenceScore: 0.84,
    },
    taxProfile: {
      estimatedIncome: 1_200_000,
      filingStatus: 'single',
      capitalGainsExposure: 'high',
      hasRetirementAccounts: false,
      taxablePortfolioSize: 5_200_000,
    },
    tags: ['vc', 'high-net-worth', 'female-exec'],
    notes: 'Found via LinkedIn. Runs a $85M fund. No prior relationship.',
    scoring: {
      icpScore: 88,
      urgencyScore: 92,
      icpCategory: 'Venture Capital / Fund Manager',
      summary: 'Managing Partner at Horizon Ventures running an $85M fund. High capital gains exposure with no retirement accounts — significant tax planning gap.',
      matchReasons: ['Very high AUM ($8.5M)', 'Institutional investor', 'No retirement accounts — SEP/IRA opportunity', 'Single filer with maximum capital gains exposure'],
      whyNowReasons: ['Year-end Qualified Opportunity Zone investment window closes Dec 31', '$340K in capital gains eligible for QOZ deferral', 'No existing retirement account structure — urgent gap for $1.2M income earner'],
      potentialConcerns: ['No prior relationship', 'Likely bombarded by financial advisors', 'No explicit consent — cold outreach compliance risk'],
      outreachAngle: 'Lead with QOZ investment opportunity specific to her fund\'s capital gains position. Mention the Dec 31 deadline to create urgency without being pushy.',
    },
    hasExplicitConsent: false,
    hasOptedOut: false,
    lastContactedAt: '2024-11-25T11:30:00Z',
    createdAt: '2024-11-15T00:00:00Z',
    updatedAt: '2024-11-25T11:30:00Z',
  },
  {
    id: 'p3',
    advisorId: 'a1',
    firstName: 'Marcus',
    lastName: 'Williams',
    email: 'marcus@mwilliamsconsulting.com',
    phone: '+1 (312) 555-0098',
    status: 'qualified',
    source: 'manual',
    enrichment: {
      companyName: 'MW Consulting LLC',
      jobTitle: 'Principal',
      estimatedAUM: 1_900_000,
      investorType: 'accredited',
      stateOfResidence: 'IL',
      enrichedAt: '2024-10-28T16:00:00Z',
      confidenceScore: 0.72,
    },
    taxProfile: {
      estimatedIncome: 380_000,
      filingStatus: 'married_joint',
      capitalGainsExposure: 'medium',
      hasRetirementAccounts: true,
      taxablePortfolioSize: 1_100_000,
    },
    tags: ['consulting', 'mid-market'],
    notes: 'Referral from Robert Chen. Looking to consolidate accounts.',
    scoring: {
      icpScore: 74,
      urgencyScore: 68,
      icpCategory: 'Independent Business Owner',
      summary: 'Principal at MW Consulting with $1.9M AUM and self-employment income eligible for a $69K SEP-IRA contribution.',
      matchReasons: ['Accredited investor', 'Self-employed — SEP-IRA eligible', 'Referral from existing client (Robert Chen)', 'Consolidating accounts — high conversion potential'],
      whyNowReasons: ['SEP-IRA contribution deadline is tax filing date (Apr 2025)', 'Looking to consolidate accounts — active evaluation mode', 'Referral relationship creates warm introduction opportunity'],
      potentialConcerns: ['Lower AUM relative to other prospects', 'Account consolidation may mean existing advisor'],
      outreachAngle: 'Warm introduction angle via Robert Chen. Lead with SEP-IRA opportunity and account consolidation simplification. Reference the shared connection.',
    },
    hasExplicitConsent: true,
    hasOptedOut: false,
    lastContactedAt: '2024-12-05T14:00:00Z',
    createdAt: '2024-10-20T00:00:00Z',
    updatedAt: '2024-12-05T14:00:00Z',
  },
  {
    id: 'p4',
    advisorId: 'a1',
    firstName: 'Jennifer',
    lastName: 'Park',
    email: 'jpark@parkmedical.org',
    status: 'new',
    source: 'csv_import',
    enrichment: {
      companyName: 'Park Medical Group',
      jobTitle: 'Chief of Surgery',
      estimatedAUM: 2_400_000,
      investorType: 'accredited',
      stateOfResidence: 'TX',
      enrichedAt: '2024-12-01T08:00:00Z',
      confidenceScore: 0.67,
    },
    taxProfile: {
      estimatedIncome: 750_000,
      filingStatus: 'married_joint',
      capitalGainsExposure: 'medium',
      hasRetirementAccounts: true,
      taxablePortfolioSize: 1_600_000,
    },
    tags: ['medical', 'high-income'],
    notes: 'Imported from Houston medical professionals list.',
    scoring: {
      icpScore: 79,
      urgencyScore: 61,
      icpCategory: 'Medical Professional',
      summary: 'Chief of Surgery with $750K income and $2.4M AUM. Estate planning opportunity via annual gift tax exclusion before year-end.',
      matchReasons: ['High income ($750K)', 'Accredited investor in TX', 'Medical professional — common wealth accumulation profile', 'No existing relationship — high potential'],
      whyNowReasons: ['Annual gift tax exclusion ($18K/recipient) expires Dec 31', 'Recently imported — early in outreach window', 'TX residency — no state income tax, focus on federal strategies'],
      potentialConcerns: ['No explicit consent — CSV import source', 'No prior relationship', 'Busy schedule as Chief of Surgery'],
      outreachAngle: 'Lead with year-end estate planning and gift tax exclusion. Keep brief and respectful of her time. Emphasize TX-specific strategies with no state income tax to add local relevance.',
    },
    hasExplicitConsent: false,
    hasOptedOut: false,
    createdAt: '2024-12-01T08:00:00Z',
    updatedAt: '2024-12-01T08:00:00Z',
  },
  {
    id: 'p5',
    advisorId: 'a1',
    firstName: 'David',
    lastName: 'Kowalski',
    email: 'd.kowalski@blueridge.com',
    status: 'closed_won',
    source: 'referral',
    enrichment: {
      companyName: 'Blue Ridge Manufacturing',
      jobTitle: 'CEO',
      estimatedAUM: 6_100_000,
      investorType: 'accredited',
      stateOfResidence: 'PA',
      enrichedAt: '2024-09-15T10:00:00Z',
      confidenceScore: 0.95,
    },
    tags: ['manufacturing', 'ceo', 'long-term-client'],
    notes: 'Converted client. Managing $4.2M AUM. Review meeting Q1.',
    scoring: {
      icpScore: 95,
      urgencyScore: 45,
      icpCategory: 'Manufacturing CEO / Existing Client',
      summary: 'Converted client managing $4.2M AUM. Q1 annual review due — opportunity to deepen relationship and expand wallet share.',
      matchReasons: ['Existing client — highest conversion certainty', 'CEO-level with $6.1M total AUM', 'Long-term relationship established', 'High confidence enrichment (95%)'],
      whyNowReasons: ['Q1 2025 annual review meeting due', 'Market rebalancing discussion needed after 2024 movements', 'Potential referral opportunity — satisfied long-term client'],
      potentialConcerns: ['Lower urgency — already a client', 'Q1 review is standard — not crisis-driven'],
      outreachAngle: 'Schedule Q1 annual review. Lead with 2024 portfolio performance and 2025 planning themes. Use as opportunity to discuss referrals from his business network.',
    },
    hasExplicitConsent: true,
    hasOptedOut: false,
    lastContactedAt: '2024-11-30T10:00:00Z',
    createdAt: '2024-05-10T00:00:00Z',
    updatedAt: '2024-11-30T10:00:00Z',
  },
];

export const MOCK_PROSPECTS: Prospect[] = [...IMPORTED_PROSPECTS, ...SEED_PROSPECTS];

export const MOCK_TEMPLATES: Template[] = [
  {
    id: 't1',
    name: 'Initial Introduction — Tax Planning',
    category: 'tax_planning',
    subject: 'Helping {{first_name}} reduce your 2024 tax burden',
    bodyHtml: `<p>Hi {{first_name}},</p>
<p>My name is {{advisor_name}}, and I specialize in helping {{industry}} professionals like yourself build tax-efficient investment strategies.</p>
<p>Given your career stage and income profile, there may be meaningful opportunities to reduce your tax liability through strategies such as:</p>
<ul>
  <li>Maximizing retirement account contributions (SEP-IRA, Solo 401k)</li>
  <li>Qualified Opportunity Zone investments</li>
  <li>Charitable Remainder Trusts for appreciated assets</li>
</ul>
<p>I'd love to share a few ideas specific to your situation — no obligations, just a 20-minute conversation.</p>
<p>Past performance is not indicative of future results. Investment strategies involve risk and may lose value. This message is for informational purposes only and does not constitute investment advice.</p>
<p>Best regards,<br>{{advisor_name}}<br>{{advisor_title}} | {{firm_name}}<br>{{firm_address}}</p>
<p><a href="{{unsubscribe_link}}">Unsubscribe</a></p>`,
    approvalStatus: 'approved',
    complianceNotes: 'Approved 2024-10-01. Includes required disclosures and CAN-SPAM elements.',
    usageCount: 47,
    createdAt: '2024-09-15T00:00:00Z',
  },
  {
    id: 't2',
    name: 'Annual Review — Existing Clients',
    category: 'annual_review',
    subject: 'Your 2024 portfolio review — let\'s connect',
    bodyHtml: `<p>Hi {{first_name}},</p>
<p>As we approach year-end, I'd like to schedule your annual portfolio review to ensure your investment strategy continues to align with your goals and circumstances.</p>
<p>In particular, I'd like to discuss:</p>
<ul>
  <li>Year-end tax-loss harvesting opportunities</li>
  <li>Rebalancing your allocation given 2024 market movements</li>
  <li>Any changes to your financial goals or timeline</li>
</ul>
<p>Please note: Past performance does not guarantee future results. All investments involve risk, including possible loss of principal.</p>
<p>Best,<br>{{advisor_name}}<br>{{firm_address}}</p>
<p><a href="{{unsubscribe_link}}">Unsubscribe</a></p>`,
    approvalStatus: 'approved',
    usageCount: 112,
    createdAt: '2024-10-01T00:00:00Z',
  },
  {
    id: 't3',
    name: 'Referral Request — Post-Meeting',
    category: 'referral_request',
    subject: 'Thank you + a quick favor',
    bodyHtml: `<p>Hi {{first_name}},</p>
<p>Thank you for the time we spent together recently. I genuinely enjoy working with professionals in your network and helping them navigate the complexity of managing significant wealth.</p>
<p>If you know anyone who might benefit from a conversation — whether they're managing a business exit, concentrated equity position, or simply looking for a second opinion — I'd be grateful for an introduction.</p>
<p>Investment advice is provided through {{firm_name}}, a registered investment adviser. This email does not constitute a solicitation in any jurisdiction where such communication is prohibited.</p>
<p>Warm regards,<br>{{advisor_name}}<br>{{firm_address}}</p>
<p><a href="{{unsubscribe_link}}">Unsubscribe</a></p>`,
    approvalStatus: 'approved',
    usageCount: 28,
    createdAt: '2024-08-20T00:00:00Z',
  },
  {
    id: 't4',
    name: 'Follow-Up — No Response',
    category: 'follow_up',
    subject: 'Following up — {{first_name}}',
    bodyHtml: `<p>Hi {{first_name}},</p>
<p>I wanted to follow up on my previous note. I understand you're busy, so I'll keep this brief.</p>
<p>I work with {{industry}} executives who are often looking for smarter ways to structure their investments from a tax perspective. If the timing isn't right, no worries — happy to reconnect when it makes more sense.</p>
<p>This message is for informational purposes only. Investment strategies involve risk. Past results do not guarantee future performance.</p>
<p>Best,<br>{{advisor_name}}<br>{{firm_address}}</p>
<p><a href="{{unsubscribe_link}}">Unsubscribe</a></p>`,
    approvalStatus: 'approved',
    usageCount: 63,
    createdAt: '2024-09-01T00:00:00Z',
  },
  {
    id: 't5',
    name: 'Market Update — Q4 2024',
    category: 'market_update',
    subject: 'Q4 Market Insights from {{firm_name}}',
    bodyHtml: `<p>Hi {{first_name}},</p>
<p>As we close out Q4, I wanted to share a few observations relevant to high-net-worth investors heading into 2025:</p>
<ul>
  <li>Rate environment shifts and fixed income positioning</li>
  <li>Municipal bond opportunities for high-income earners</li>
  <li>Year-end Roth conversion windows</li>
</ul>
<p><strong>Important disclosures:</strong> This communication is for informational purposes only and does not constitute investment, tax, or legal advice. All investments carry risk including loss of principal. Past performance does not indicate future results. Please consult with your tax advisor regarding your specific situation.</p>
<p>Best,<br>{{advisor_name}}<br>{{firm_address}}</p>
<p><a href="{{unsubscribe_link}}">Unsubscribe</a></p>`,
    approvalStatus: 'pending',
    usageCount: 0,
    createdAt: '2024-12-01T00:00:00Z',
  },
];

export const MOCK_SUBMISSIONS: ComplianceSubmission[] = [
  {
    id: 's1',
    advisorId: 'a1',
    subject: 'Helping Robert reduce your 2024 tax burden',
    messageContent: 'Hi Robert, My name is Alex Johnson...',
    templateId: 't1',
    recipientCount: 1,
    complianceScore: {
      opinion: { b: 0.76, d: 0.06, u: 0.18, a: 0.78 },
      riskLevel: 'low',
      projectedProbability: 0.794,
      triggeredRules: [],
      requiresReview: false,
      autoBlocked: false,
      scoredAt: '2024-12-01T10:00:00Z',
    },
    status: 'approved',
    officerNotes: 'Content reviewed. Disclosures present and accurate.',
    submittedAt: '2024-12-01T10:05:00Z',
    reviewedAt: '2024-12-01T14:30:00Z',
  },
  {
    id: 's2',
    advisorId: 'a1',
    subject: 'Q4 Market Insights — Action Items',
    messageContent: 'Hi Sarah, Given the current rate environment...',
    recipientCount: 3,
    complianceScore: {
      opinion: { b: 0.51, d: 0.18, u: 0.31, a: 0.62 },
      riskLevel: 'medium',
      projectedProbability: 0.702,
      triggeredRules: [
        {
          ruleId: 'FINRA-2210',
          ruleName: 'Fair and Balanced Communication',
          description: 'Longer content without required risk disclosures.',
          severity: 'warning',
          regulation: 'FINRA Rule 2210',
        },
      ],
      requiresReview: true,
      autoBlocked: false,
      scoredAt: '2024-12-03T09:00:00Z',
    },
    status: 'pending_review',
    submittedAt: '2024-12-03T09:10:00Z',
  },
];

export const MOCK_TAX_OPPORTUNITIES: TaxOpportunity[] = [
  {
    id: 'tx1',
    prospectId: 'p1',
    strategyType: 'tax_loss_harvesting',
    title: 'Year-End Tax-Loss Harvesting',
    description: 'Portfolio has $180K in unrealized losses that could offset capital gains. Deadline: Dec 31.',
    estimatedSavings: 45_000,
    urgency: 'high',
    deadline: '2024-12-31',
    suggestedTemplateId: 't1',
  },
  {
    id: 'tx2',
    prospectId: 'p1',
    strategyType: 'roth_conversion',
    title: 'Roth Conversion Opportunity',
    description: 'Current marginal rate of 37% may drop in 2026. Window for partial Roth conversion at current rates.',
    estimatedSavings: 28_000,
    urgency: 'medium',
    suggestedTemplateId: 't5',
  },
  {
    id: 'tx3',
    prospectId: 'p2',
    strategyType: 'charitable_giving',
    title: 'Qualified Opportunity Zone Investment',
    description: 'Pre-year-end QOZ investment can defer $340K capital gains into 2026.',
    estimatedSavings: 120_000,
    urgency: 'high',
    deadline: '2024-12-31',
  },
  {
    id: 'tx4',
    prospectId: 'p3',
    strategyType: 'retirement_contribution',
    title: 'Maximize SEP-IRA Contribution',
    description: 'Self-employed income qualifies for $69,000 SEP-IRA contribution, reducing AGI significantly.',
    estimatedSavings: 26_220,
    urgency: 'medium',
    suggestedTemplateId: 't1',
  },
  {
    id: 'tx5',
    prospectId: 'p4',
    strategyType: 'estate_planning',
    title: 'Annual Gift Tax Exclusion',
    description: 'Utilize $18,000/recipient annual exclusion before year-end to reduce taxable estate.',
    estimatedSavings: 14_000,
    urgency: 'low',
    deadline: '2024-12-31',
  },
];

export const MOCK_CAMPAIGNS: Campaign[] = [
  {
    id: 'c1',
    advisorId: 'a1',
    name: 'Q4 Tax Planning Outreach',
    subject: 'Helping you reduce your 2024 tax burden',
    bodyHtml: '<p>Hi {{first_name}}...</p>',
    channel: 'resend',
    recipientIds: ['p1', 'p3'],
    complianceSubmissionId: 's1',
    status: 'sent',
    sentAt: '2024-12-02T09:00:00Z',
    metrics: { totalSent: 2, opened: 2, clicked: 1, bounced: 0 },
    createdAt: '2024-12-01T10:00:00Z',
  },
  {
    id: 'c2',
    advisorId: 'a1',
    name: 'Year-End Market Update',
    subject: 'Q4 Market Insights from Meridian Wealth',
    bodyHtml: '<p>Hi {{first_name}}...</p>',
    channel: 'resend',
    recipientIds: ['p1', 'p2', 'p3'],
    status: 'draft',
    metrics: { totalSent: 0, opened: 0, clicked: 0, bounced: 0 },
    createdAt: '2024-12-03T09:00:00Z',
  },
];
