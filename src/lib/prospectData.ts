import { Prospect } from '@/types';

function parseNameParts(name: string): { firstName: string; lastName: string } {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return { firstName: parts[0], lastName: '' };
  return { firstName: parts[0], lastName: parts.slice(1).join(' ') };
}

function parseCompany(currentRole: string): string {
  const atIdx = currentRole.lastIndexOf(' at ');
  return atIdx !== -1 ? currentRole.slice(atIdx + 4).trim() : '';
}

function parseTitle(currentRole: string): string {
  const atIdx = currentRole.lastIndexOf(' at ');
  return atIdx !== -1 ? currentRole.slice(0, atIdx).trim() : currentRole;
}

function deriveState(location: string): string {
  if (/new york|ny/i.test(location)) return 'NY';
  if (/new jersey|nj/i.test(location)) return 'NJ';
  if (/california|ca|san francisco|los angeles/i.test(location)) return 'CA';
  if (/florida|fl/i.test(location)) return 'FL';
  if (/illinois|chicago/i.test(location)) return 'IL';
  if (/connecticut|ct/i.test(location)) return 'CT';
  if (/texas|tx/i.test(location)) return 'TX';
  return 'NY';
}

function icpLabel(matched_icp: string): string {
  const map: Record<string, string> = {
    high_income_professional: 'High Income Professional',
    business_owners_exits: 'Business Owner – Exit',
    business_owners_succession: 'Business Owner – Succession',
    business_owner: 'Business Owner',
    business_owner_and_high_income_professional: 'Business Owner + HIP',
    none: 'Unqualified',
  };
  return map[matched_icp] ?? matched_icp;
}

function estimateAUM(icpScore: number, urgencyScore: number): number {
  if (icpScore >= 88) return Math.round((icpScore * 80_000 + urgencyScore * 40_000));
  if (icpScore >= 70) return Math.round((icpScore * 30_000 + urgencyScore * 15_000));
  if (icpScore >= 50) return Math.round((icpScore * 12_000));
  return 0;
}

function statusFromScores(icp: number, urgency: number): Prospect['status'] {
  if (urgency >= 80 && icp >= 80) return 'qualified';
  if (urgency >= 60) return 'engaged';
  if (urgency >= 40) return 'contacted';
  return 'new';
}

// Raw data from dataset
const RAW: Array<{
  name: string;
  current_role: string;
  location: string;
  linkedin_url: string;
  icp_match_score: number;
  urgency_score: number;
  matched_icp: string;
  summary: string;
  match_reasons: string[];
  why_now_reasons: string[];
  concerns: string[];
  recommended_outreach_angle: string;
}> = [
  {
    name: 'Aaron Bauhs',
    current_role: 'Partner - IBM Consulting at IBM',
    location: 'New York, New York (working Greater Chicago Area)',
    linkedin_url: 'https://linkedin.com/in/aaronbauhs',
    icp_match_score: 60,
    urgency_score: 40,
    matched_icp: 'high_income_professional',
    summary: 'IBM Consulting Partner with 20+ years of experience in digital strategy and business transformation for Fortune 500 clients. MBA from NYU Stern. Currently based in Greater Chicago Area despite NYC residence, limiting geographic fit for NYC-focused wealth management firm.',
    match_reasons: [
      'Partner-level position at IBM Consulting — estimated income $400K-$1M+',
      '20+ years total experience demonstrates seniority',
      'MBA from NYU Stern indicates strong educational background',
      'Consulting background aligns with high-income professional profile',
    ],
    why_now_reasons: [],
    concerns: [
      'Current work location is Greater Chicago Area, not NYC metro — geographic mismatch',
      'Partner role since Aug 2015 (10+ years ago) — no recent promotion or transition trigger',
      'No signals of equity compensation or wealth trigger events',
    ],
    recommended_outreach_angle: 'Not recommended for outreach at this time; geographic mismatch to NYC requirement is a disqualifying factor per ICP criteria.',
  },
  {
    name: 'Aaron Hancock',
    current_role: 'Senior Vice President Co-Portfolio Manager at Artemis Real Estate Partners',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/taaronh1906',
    icp_match_score: 78,
    urgency_score: 65,
    matched_icp: 'high_income_professional',
    summary: 'SVP and Co-Portfolio Manager at Artemis Real Estate Partners with 14+ years of experience spanning real estate private equity, investment banking, and capital raising. Harvard MBA graduate currently based in NYC.',
    match_reasons: [
      'SVP at alternative investment firm — estimated income $300K-$750K+',
      'NYC-based, confirmed in profile',
      '14+ years experience in investment and real estate finance',
      'Harvard MBA and strong educational pedigree',
    ],
    why_now_reasons: [
      '3+ years as SVP at Artemis suggests equity/carried interest potential',
      'Founder/CEO of own consulting firm since 2019 indicates entrepreneurial income diversification',
      'Director role at Wall Street Prep managing teams at Blackstone, KKR, Ares',
    ],
    concerns: [
      'No explicit promotion or recent liquidity event triggering immediate need',
      'No clear indication of carried interest or equity stakes typical of PE partners',
      'Multiple concurrent roles suggests complex compensation but exact wealth level unclear',
    ],
    recommended_outreach_angle: 'Position as expert in wealth structuring for alternative investment professionals; offer insights on optimizing compensation across multiple income streams.',
  },
  {
    name: 'Aarti Kapoor',
    current_role: 'Managing Director, Consumer & Retail Investment Banking at Cascadia Capital',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/aarti-kapoor1',
    icp_match_score: 94,
    urgency_score: 92,
    matched_icp: 'high_income_professional',
    summary: 'Managing Director of Consumer & Retail Investment Banking at Cascadia Capital with 18+ years of experience. Recently promoted to MD in November 2025, bringing prestigious Wall Street background from Goldman Sachs and Moelis. Harvard graduate, Forbes 30 Under 30.',
    match_reasons: [
      'NYC-based (New York, New York confirmed)',
      'Managing Director role at boutique investment bank — estimated income $500K-$2M+ annually',
      '18+ years of experience in elite finance roles (Citi, Moelis, Goldman Sachs)',
      'Previous Partner role at VMG Partners (PE/VC) and CEO of SPAC demonstrates equity exposure',
      'Harvard education and elite firm backgrounds signal high earning potential',
    ],
    why_now_reasons: [
      'Promoted to Managing Director at Cascadia Capital in November 2025 — recent title elevation',
      'MD role means increased partnership economics and compensation structure change',
      'Recent transition from Partner at VMG (Aug 2025) to MD role suggests active career progression',
      'SPAC CEO experience indicates familiarity with liquidity events and equity compensation',
    ],
    concerns: [
      'Recent job transitions (Partner → MD within ~3 months) could indicate restructuring',
      'No explicit mention of personal wealth or net worth indicators beyond role',
    ],
    recommended_outreach_angle: 'Congratulate on MD appointment at Cascadia; offer specialized insights on investment banking compensation structuring and partner tax strategies.',
  },
  {
    name: 'Adam Bergman',
    current_role: 'Founder at IRA Financial',
    location: 'Miami Beach, Florida',
    linkedin_url: 'https://linkedin.com/in/adambergman1',
    icp_match_score: 42,
    urgency_score: 35,
    matched_icp: 'business_owners_exits',
    summary: 'Founder of IRA Financial, a financial services company with 51-200 employees founded in 2010. Tax and ERISA attorney with 23+ years of experience. Currently based in Miami Beach, Florida, not NYC.',
    match_reasons: [
      'Founder and CEO of established business (15+ years operating)',
      'Business size (51-200 employees) fits ICP target range',
      'Financial services industry aligns with wealth management needs',
    ],
    why_now_reasons: [
      'Recent hiring activity suggests growth and potential equity appreciation',
    ],
    concerns: [
      'Based in Miami Beach, Florida, not NYC — fails geographic requirement',
      'No exit signals in profile — company appears stable and growing, not transitioning',
      'Business is in financial services/advisor space with existing retirement planning expertise',
    ],
    recommended_outreach_angle: 'Not recommended for outreach at this time — geographic mismatch disqualifies prospect despite strong business owner credentials.',
  },
  {
    name: 'Adam Cooperman',
    current_role: 'Regional Vice President Of Sales at Tanium',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/adamcooperman',
    icp_match_score: 72,
    urgency_score: 55,
    matched_icp: 'business_owners_exits',
    summary: 'Accomplished executive with 28+ years of experience and a track record of founding and scaling businesses. Currently VP of Sales at Tanium, previously founded The NorthPark Group (exited/sold). Active startup advisor and angel investor based in NYC.',
    match_reasons: [
      'NYC-based confirmed in profile (New York, New York)',
      'Entrepreneurial background: Founded and built The NorthPark Group (2007-2011)',
      'Attracted PE interest during his tenure, suggesting business value creation',
      'Active startup advisor and angel investor since 2018',
    ],
    why_now_reasons: [
      'Recently transitioned to VP role at Tanium (Oct 2024), suggesting potential equity from previous role',
      'Active angel investor managing investment portfolios requiring wealth management',
    ],
    concerns: [
      'Current role is employee/VP at Tanium rather than owner of established business',
      'Business exit was in 2011, not recent',
      'No explicit signals of retirement planning or active exit in process',
    ],
    recommended_outreach_angle: 'Acknowledge his exit experience with NorthPark Group and current investment portfolio; position as expert in post-exit wealth optimization.',
  },
  {
    name: 'Adam Gotterer',
    current_role: 'Senior Vice President Of Engineering at HouseAccount',
    location: 'New York City Metropolitan Area',
    linkedin_url: 'https://linkedin.com/in/agotterer',
    icp_match_score: 72,
    urgency_score: 58,
    matched_icp: 'high_income_professional',
    summary: 'Engineering executive with 18+ years of experience leading technical teams at multiple high-growth startups. Currently SVP of Engineering at HouseAccount (11-50 employees). NYC-based with proven track record scaling engineering organizations.',
    match_reasons: [
      'SVP/C-suite level role with significant compensation typical of high-income professionals',
      'NYC-based confirmed in profile',
      '18 years of engineering experience with consistent progression to executive roles',
      'Multiple senior roles at venture-backed startups suggest equity compensation',
    ],
    why_now_reasons: [
      'Joined HouseAccount as SVP in Jun 2024 — recent enough to be building wealth at new company',
      '18 years of cumulative experience indicates peak earning years',
      'Track record of equity participation through multiple startup roles (Shopalytic acquired)',
    ],
    concerns: [
      'HouseAccount is early-stage (11-50 employees) with no confirmed Series funding',
      'No visible signs of imminent promotion or immediate liquidity event',
    ],
    recommended_outreach_angle: 'Approach with focus on equity diversification strategy for tech executives and tax optimization for former founders/executives.',
  },
  {
    name: 'Adam Guild',
    current_role: 'Co-founder & CEO at Owner',
    location: 'San Francisco Bay Area, California',
    linkedin_url: 'https://linkedin.com/in/adamharrisonguild',
    icp_match_score: 45,
    urgency_score: 35,
    matched_icp: 'business_owners',
    summary: 'Young founder and CEO of Owner.com, a restaurant tech platform that has raised $25M+ in funding. Forbes 30 Under 30 honoree and Thiel Fellow. Currently focused on scaling the company rather than exit planning.',
    match_reasons: [
      'Founder and CEO of established company with 201-500 employees',
      'Company has raised significant funding ($25M+)',
    ],
    why_now_reasons: [
      'Company is actively growing with ongoing capital raises',
    ],
    concerns: [
      'Based in San Francisco Bay Area, NOT NYC — critical disqualifier',
      'Age appears to be early 30s or younger, outside typical ICP age range',
      'No liquidity event signals',
    ],
    recommended_outreach_angle: 'Not recommended for immediate outreach due to geographic mismatch; consider re-engaging if Owner is acquired or if founder relocates to NYC area.',
  },
  {
    name: 'Adam Hade',
    current_role: 'Licensed Associate Broker at Compass',
    location: 'Chappaqua, New York',
    linkedin_url: 'https://linkedin.com/in/adam-hade-33b23440',
    icp_match_score: 35,
    urgency_score: 25,
    matched_icp: 'none',
    summary: 'Real estate broker with 35 years of experience, currently at Compass. Based in Westchester County, NY with a track record of selling high-value properties in the region.',
    match_reasons: [
      'Located in Westchester County, within commuting distance to NYC metro area',
      '35 years of experience suggests age 60+, potentially approaching retirement',
    ],
    why_now_reasons: [],
    concerns: [
      'Does not match any ICP profile — real estate broker, not business owner or high-income professional',
      'Commission-based income typically less consistent than target ICP income levels',
      'No indicators of $2M+ net worth sufficient for premium wealth management',
    ],
    recommended_outreach_angle: 'Not recommended for outreach — profile does not match any ICP criteria.',
  },
  {
    name: 'Adam Hanski',
    current_role: 'Partner at Parker Hanski LLC',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/adam-hanski-165999a',
    icp_match_score: 65,
    urgency_score: 42,
    matched_icp: 'high_income_professional',
    summary: 'Real estate professional with legal background currently operating as Partner at Parker Hanski LLC in NYC. Profile shows 10 years 11 months of documented experience with earlier roles in acquisitions at capital firms.',
    match_reasons: [
      'Partner designation at Parker Hanski LLC suggests partnership stake and ownership',
      'NYC-based, confirmed in profile',
      'Real estate acquisitions background in capital management sector',
      'Legal education (JD from USC) and real estate development expertise (MS from Columbia)',
    ],
    why_now_reasons: [
      'Currently listed as Partner — indicates existing or recent partnership equity stake',
    ],
    concerns: [
      'Parker Hanski LLC appears to be boutique/small firm with unclear size and AUM',
      'Unexplained gap in profile between 2011 and current Parker Hanski partnership',
      'No recent promotion or activity signals triggering urgency',
    ],
    recommended_outreach_angle: 'Research Parker Hanski LLC background; if viable boutique firm, approach with real estate-specific wealth planning focused on partnership distributions.',
  },
  {
    name: 'Adam Hirsh',
    current_role: 'VP, Capital Markets Consult Partner at Kyndryl',
    location: 'Westfield, New Jersey',
    linkedin_url: 'https://linkedin.com/in/adamhirsh',
    icp_match_score: 55,
    urgency_score: 45,
    matched_icp: 'high_income_professional',
    summary: '30+ year capital markets technology veteran with recent transition from EY Managing Director to VP at Kyndryl. Based in Westfield, NJ. Specializes in financial services consulting and platform modernization.',
    match_reasons: [
      'VP-level title at large public company suggests senior leadership role',
      '30+ years experience in capital markets and financial services consulting',
      'Career trajectory includes roles at JP Morgan, Citi, Lazard, EY, KPMG',
    ],
    why_now_reasons: [
      'Recent job change October 2025 may involve equity compensation or deferred arrangements',
      'Career inflection point from consulting (EY MD) to tech services (Kyndryl VP)',
    ],
    concerns: [
      'Located in Westfield, New Jersey — geographic penalty for not being NYC proper',
      'No explicit wealth signals: no equity compensation, carried interest, or partner distributions',
    ],
    recommended_outreach_angle: 'Recognize his 30-year capital markets expertise and recent leadership transition; position around structuring deferred comp and equity options.',
  },
  {
    name: 'Adam Leitman Bailey',
    current_role: 'Partner at Adam Leitman Bailey, P.C.',
    location: 'New York City Metropolitan Area',
    linkedin_url: 'https://linkedin.com/in/adamleitmanbailey',
    icp_match_score: 88,
    urgency_score: 62,
    matched_icp: 'business_owner',
    summary: 'Adam Leitman Bailey is the founding partner of his eponymous NYC real estate law firm (11-50 employees), founded in 2000. With 26 years of experience, he is one of New York\'s most prominent real estate attorneys, recognized by Chambers & Partners, Super Lawyers Top 100, and LawDragon 500.',
    match_reasons: [
      'Founder and named partner of his own law firm — classic business owner ICP',
      'NYC-based, confirmed in profile',
      '26 years of experience with extensive recognition (Chambers, Super Lawyers Top 100)',
      'Estimated age ~65, fitting both Business Owner and Pre-Retiree ICPs',
    ],
    why_now_reasons: [
      'At estimated age ~65, at upper end of Business Owner ICP — succession planning likely top of mind',
      '25+ years running his own firm means significant accumulated wealth',
      'Recent high-profile awards in 2025 suggest continued peak activity but approaching transition years',
    ],
    concerns: [
      'As founder, may already have established financial advisory relationships',
      'High public profile means he is likely heavily solicited by financial advisors already',
      'No recent role change or immediate liquidity event detected',
    ],
    recommended_outreach_angle: 'Approach with a focus on business succession planning and exit strategy for his eponymous law firm, emphasizing wealth preservation and transition.',
  },
  {
    name: 'Adam Lippin',
    current_role: 'Founder at HearMe',
    location: 'New York City Metropolitan Area, New York',
    linkedin_url: 'https://linkedin.com/in/adam-lippin-ab1a655',
    icp_match_score: 78,
    urgency_score: 72,
    matched_icp: 'business_owners_succession',
    summary: 'Serial entrepreneur and founder with 21+ years of business experience. Successfully exited Cuddlist (2022) and Atomic Wings (2017). Currently founding GayMenSupport and operating HearMe (1-10 employees). NYC-based with demonstrated track record of building and scaling ventures.',
    match_reasons: [
      'Multiple successful exits demonstrate founder/business owner status',
      'NYC-based confirmed in profile',
      '21+ years total entrepreneurial experience',
      'Previous exits in 2022 and 2017 show pattern of building and monetizing ventures',
    ],
    why_now_reasons: [
      'Recent exit of Cuddlist in 2022 — likely received proceeds and managing post-exit wealth',
      'Prior Atomic Wings exit in 2017 — potentially sitting on accumulated capital from multiple exits',
      'Currently building two ventures — potential for future liquidity events',
    ],
    concerns: [
      'HearMe appears to be early-stage (1-10 employees)',
      'GayMenSupport is very recent (Jun 2025) — too early stage for immediate succession planning',
      'Ventures appear to be passion projects rather than high-revenue businesses',
    ],
    recommended_outreach_angle: 'Acknowledge successful track record of building and exiting ventures; position wealth management services around maximizing returns from previous exits.',
  },
  {
    name: 'Adam Schaack',
    current_role: 'Partner at McKinsey & Company',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/adam-schaack-10a1b928',
    icp_match_score: 88,
    urgency_score: 82,
    matched_icp: 'high_income_professional',
    summary: 'McKinsey Partner with 12+ years of consulting experience, promoted to Partner in January 2024. NYC-based with Harvard MBA. Represents top-tier consulting talent at peak earning years.',
    match_reasons: [
      'Partner at McKinsey & Company — estimated income $500K-$1.5M+ with profit sharing',
      'NYC-based (New York, New York confirmed)',
      '12 years experience demonstrates significant seniority',
      'Harvard MBA graduate',
    ],
    why_now_reasons: [
      'Promoted to Partner in January 2024 — past initial adjustment phase with new equity/profit-sharing',
      '12+ years at firm suggests loyalty; likely in peak earning and wealth accumulation phase',
      'Partnership income includes bonus structures and profit distributions creating tax complexity',
    ],
    concerns: [
      'Partner promotion was over 1 year ago — not as immediate as 6-month trigger window',
      'No indication of business ownership, exit planning, or transition signals',
    ],
    recommended_outreach_angle: 'Position as wealth optimization specialist for senior consulting partners navigating tax-efficient compensation structures and profit distributions post-partnership.',
  },
  {
    name: 'Adam Singolda',
    current_role: 'Founder & CEO at Taboola',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/adamsingolda',
    icp_match_score: 88,
    urgency_score: 65,
    matched_icp: 'business_owners_exits',
    summary: 'Founder and CEO of Taboola, a content discovery and personalization platform. 18+ years building the company from inception to scale. NYC-based founder with strong executive pedigree and industry influence.',
    match_reasons: [
      'Founder & CEO of established technology company (Taboola) — matches Business Owner ICP exactly',
      'NYC-based (New York, New York confirmed)',
      '18+ years of total experience indicates significant wealth accumulation',
    ],
    why_now_reasons: [
      '18+ year tenure suggests founder at stage of considering legacy, succession, or wealth optimization',
      'High-profile status with speaking engagements at MIT, Bloomberg suggests peak earning years',
    ],
    concerns: [
      'No active exit, acquisition, or recent liquidity event',
      'Current role as active CEO suggests founder may not yet be in transition mode',
    ],
    recommended_outreach_angle: 'Approach with insight on succession planning and concentrated wealth strategies for long-tenure founders entering potential exit or legacy planning phase.',
  },
  {
    name: 'Adam Weinstein',
    current_role: 'Partner at Sidley Austin LLP',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/adam-weinstein-3b1857b',
    icp_match_score: 88,
    urgency_score: 62,
    matched_icp: 'high_income_professional',
    summary: 'Long-tenured law partner with 36+ years of experience and 7+ years at Sidley Austin LLP, one of the world\'s largest law firms. NYC-based with significant board involvement and likely high six-figure to multi-million dollar income.',
    match_reasons: [
      'Partner at AmLaw #1 firm (Sidley Austin) — estimated income $1-3M+',
      'NYC-based, confirmed in profile',
      '36+ years of legal experience puts him in prime wealth accumulation and preservation phase',
      'Board member at TEAK Fellowship suggests philanthropic wealth and estate planning mindset',
    ],
    why_now_reasons: [
      '36+ years experience suggests approaching wealth transition planning',
      'Board involvement with nonprofit suggests estate and giving strategy considerations',
    ],
    concerns: [
      'No recent promotion or major trigger event — partnership role started October 2018',
      'No indication of recent job change or immediate liquidity catalyst',
    ],
    recommended_outreach_angle: 'Reach out regarding wealth transition planning and tax optimization for senior partners with 30+ year careers and substantial accumulated assets.',
  },
  {
    name: 'Adele Hogan',
    current_role: 'Partner at Broadfield',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/adele-hogan',
    icp_match_score: 95,
    urgency_score: 85,
    matched_icp: 'high_income_professional',
    summary: 'Accomplished transactional attorney with 26+ years of experience in mergers, capital markets, securities, and regulatory law. Recently promoted to Partner at Broadfield (June 2025) while maintaining director roles at two Nasdaq-listed companies. NYC-based with substantial partnership compensation.',
    match_reasons: [
      'Partner at law firm with AmLaw-tier experience — estimated income well above $500K-$1M+',
      'NYC-based, confirmed in profile',
      '26+ years of experience in high-value legal practice (mergers, IPOs, SPACs, securities)',
      'Director at two Nasdaq public companies with director compensation and equity stakes',
    ],
    why_now_reasons: [
      'Promoted to Partner at Broadfield (June 2025) — recent career transition with new equity stake',
      'Active director roles at public companies create concentrated equity exposure requiring diversification',
      '26 years of accumulated wealth from multiple partnership positions at top-tier firms',
    ],
    concerns: [],
    recommended_outreach_angle: 'Congratulate Adele on her partnership elevation at Broadfield; offer specialized tax optimization and wealth diversification strategies for accomplished legal professionals.',
  },
  {
    name: 'Adino Shimunova',
    current_role: 'Director of Partner Recruiting at Troutman Pepper Locke LLP',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/adino-shimunova-ba075a6',
    icp_match_score: 28,
    urgency_score: 15,
    matched_icp: 'none',
    summary: 'Recruiting professional with 29+ years of experience in talent management and partner recruiting at major law firms. Currently Director of Partner Recruiting — works in HR/Recruiting function, not a legal partner.',
    match_reasons: [],
    why_now_reasons: [],
    concerns: [
      'Not a lawyer or legal partner — works in HR/Recruiting function at law firms',
      'Income likely in $150K-300K range, below high-income professional threshold',
      'Does not match any ICP profile',
    ],
    recommended_outreach_angle: 'Not a qualified prospect for wealth management services.',
  },
  {
    name: 'Adriana Miller',
    current_role: 'Business Development Representative at Millennium Geomatics Ltd',
    location: 'Calgary, Alberta, Canada',
    linkedin_url: 'https://linkedin.com/in/adriana-miller',
    icp_match_score: 15,
    urgency_score: 5,
    matched_icp: 'none',
    summary: 'Early-career marketing and business development professional based in Calgary, Canada with diverse experience across marketing, accounting, and sales roles.',
    match_reasons: [],
    why_now_reasons: [],
    concerns: [
      'Based in Calgary, Alberta, Canada — does not meet NYC geographic requirement',
      'Junior specialist-level position, not partner/MD/VP/C-suite',
      'Does not match any of the three ICPs',
    ],
    recommended_outreach_angle: 'Not recommended for outreach. This prospect does not qualify for target market due to geographic location and insufficient income/wealth indicators.',
  },
  {
    name: 'Aizaz Akhtar',
    current_role: 'Strategist at Morgan Stanley',
    location: 'New York, United States',
    linkedin_url: 'https://linkedin.com/in/aizaz-akhtar-b6766916',
    icp_match_score: 88,
    urgency_score: 62,
    matched_icp: 'high_income_professional',
    summary: 'Senior strategist at Morgan Stanley with 20+ years of experience in financial services. Previously held executive roles at Goldman Sachs and Morgan Stanley London. Currently based in NYC.',
    match_reasons: [
      'NYC-based, confirmed in profile',
      '20+ years experience in finance puts him in prime wealth accumulation phase',
      'Progression from Goldman Sachs VP to Morgan Stanley Executive Director demonstrates senior-level income',
      'Work at tier-1 financial institutions indicates significant compensation',
    ],
    why_now_reasons: [
      '20+ years in financial services indicates approaching peak earning years with wealth concentration questions',
    ],
    concerns: [
      'Profile shows current title as "Strategist" (specialist level) rather than Managing Director',
      'No recent promotion signals or career transition indicators',
    ],
    recommended_outreach_angle: 'Approach as wealth preservation and diversification opportunity for senior finance executive with 20+ years at premier institutions.',
  },
  {
    name: 'Ajai Thomas',
    current_role: 'Partner - Head of Business Development at Trevally Capital LLC',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/ajaithomas',
    icp_match_score: 95,
    urgency_score: 92,
    matched_icp: 'high_income_professional',
    summary: 'Finance industry veteran with 30+ years experience, recently promoted to Partner at newly-founded Trevally Capital LLC (September 2024). NYC-based hedge fund operator specializing in structured products and mortgage-backed securities. Proven ability to raise $1.25B+ in capital.',
    match_reasons: [
      'Partner-level role at alternative asset management firm — estimated income $500K-$2M+ with carried interest',
      'NYC-based, confirmed in profile',
      '30+ years experience in finance with seniority progression from analyst to Partner',
      'Head of Business Development role managing institutional investor relationships',
      'Founded/co-founded Trevally Capital in 2024 as minority-run, 100% employee-owned partnership',
    ],
    why_now_reasons: [
      'Promoted to Partner at newly-founded Trevally Capital in September 2024 — very recent with new equity stake',
      'New partnership likely comes with K-1 income, carried interest distributions, and complex tax situations',
      'Transitioning from 10+ year tenure at Hollis Park to new entity signals inflection point',
    ],
    concerns: [],
    recommended_outreach_angle: 'Congratulate on partnership launch at Trevally Capital; offer specialized tax optimization and wealth planning for partners with carried interest exposure and K-1 income complexity.',
  },
  {
    name: 'Akarin Gaw',
    current_role: 'Managing Partner at Portlock Group, LLC',
    location: 'New York City Metropolitan Area, New York',
    linkedin_url: 'https://linkedin.com/in/akaringaw',
    icp_match_score: 82,
    urgency_score: 65,
    matched_icp: 'business_owner_and_high_income_professional',
    summary: 'Seasoned investor and entrepreneur with 19+ years of experience in private equity and renewable energy. Currently holds multiple senior roles including Partner Advisor at Renewable Energy, Managing Partner of Portlock Group, and Co-Founder of GrtWines. Based in NYC metro area.',
    match_reasons: [
      '19+ years of experience in private equity and C-suite roles',
      'Multiple concurrent Partner-level and Founder positions',
      'NYC metro area based',
      'Private equity background suggests exposure to carried interest and equity compensation',
    ],
    why_now_reasons: [
      'Managing multiple early-stage ventures (GrtWines launched 2022) — potential liquidity events',
      'Recent activity shows engagement with portfolio companies and wind energy investments',
    ],
    concerns: [
      'Multiple concurrent roles with overlapping timelines — unclear employment status',
      'No clear indication of recent promotion or major transition event',
    ],
    recommended_outreach_angle: 'Highlight expertise in tax optimization for PE operating partners managing multiple equity positions across renewable energy and consumer ventures.',
  },
  {
    name: 'Alan Brody',
    current_role: 'Managing Partner at Benbridge Capital',
    location: 'New York, New York',
    linkedin_url: 'https://linkedin.com/in/alan-brody-70622a131',
    icp_match_score: 94,
    urgency_score: 68,
    matched_icp: 'high_income_professional',
    summary: 'Managing Partner and CEO/CIO of Benbridge Capital, a multi-family office serving ultra-high-net-worth clients. With 35+ years in finance and investment management, Alan has held senior leadership roles at J.P. Morgan, Deutsche Bank, and other top-tier financial institutions. NYC-based.',
    match_reasons: [
      'Managing Partner/CEO status at own firm (multi-family office)',
      'NYC-based, confirmed in profile',
      '35+ years total experience puts him at peak earning and wealth accumulation phase',
      'Managing Partner role in finance indicates annual income well above $500K, likely $1M+',
      'Services ultra-high-net-worth families — positioned at top of wealth management industry',
    ],
    why_now_reasons: [
      'Currently managing partner of growth-stage multi-family office (Benbridge Capital since Mar 2020)',
      '35+ years career at peak suggests wealth transition and retirement planning considerations',
    ],
    concerns: [
      'Profile lacks recent promotion signals (current role started Mar 2020, over 5 years ago)',
      'No explicit "open to work" or career transition signals',
    ],
    recommended_outreach_angle: 'Position as peer-to-peer conversation on wealth transition strategies for senior finance executives managing their own family office.',
  },
];

// Map raw data → Prospect type
export const IMPORTED_PROSPECTS: Prospect[] = RAW.map((r, i) => {
  const { firstName, lastName } = parseNameParts(r.name);
  const company = parseCompany(r.current_role);
  const title = parseTitle(r.current_role);
  const state = deriveState(r.location);
  const aum = estimateAUM(r.icp_match_score, r.urgency_score);

  return {
    id: `ip${String(i + 1).padStart(3, '0')}`,
    advisorId: 'a1',
    firstName,
    lastName,
    email: '',
    status: statusFromScores(r.icp_match_score, r.urgency_score),
    source: 'clay_enrichment',
    enrichment: {
      linkedinUrl: r.linkedin_url,
      location: r.location,
      companyName: company,
      jobTitle: title,
      estimatedAUM: aum,
      investorType: r.icp_match_score >= 70 ? 'accredited' : 'retail',
      stateOfResidence: state,
      enrichedAt: '2025-11-01T00:00:00Z',
      confidenceScore: Math.round((r.icp_match_score / 100) * 100) / 100,
    },
    scoring: {
      icpScore: r.icp_match_score,
      urgencyScore: r.urgency_score,
      icpCategory: icpLabel(r.matched_icp),
      summary: r.summary,
      matchReasons: r.match_reasons,
      whyNowReasons: r.why_now_reasons,
      potentialConcerns: r.concerns,
      outreachAngle: r.recommended_outreach_angle,
    },
    tags: [r.matched_icp.replace(/_/g, '-'), state.toLowerCase()],
    notes: '',
    hasExplicitConsent: false,
    hasOptedOut: false,
    createdAt: '2025-11-01T00:00:00Z',
    updatedAt: '2025-11-01T00:00:00Z',
  };
});
