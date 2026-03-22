-- Create prospects table
CREATE TABLE IF NOT EXISTS prospects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  advisor_id UUID NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT,
  status TEXT NOT NULL DEFAULT 'new'
    CHECK (status IN ('new', 'contacted', 'engaged', 'qualified', 'closed_won', 'closed_lost')),
  source TEXT NOT NULL DEFAULT 'manual'
    CHECK (source IN ('manual', 'csv_import', 'clay_enrichment', 'referral')),
  tags TEXT[] DEFAULT '{}',
  notes TEXT DEFAULT '',
  has_opted_out BOOLEAN DEFAULT FALSE,
  has_explicit_consent BOOLEAN DEFAULT FALSE,
  last_contacted_at TIMESTAMPTZ,
  enrichment JSONB,
  tax_profile JSONB,
  scoring JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT prospects_email_advisor_unique UNIQUE (email, advisor_id)
);

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prospects_updated_at
  BEFORE UPDATE ON prospects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row-Level Security
ALTER TABLE prospects ENABLE ROW LEVEL SECURITY;

-- Advisors can only access their own prospects
CREATE POLICY "Advisors access own prospects" ON prospects
  FOR ALL
  USING (auth.uid() = advisor_id);

-- Compliance officers can read all prospects
CREATE POLICY "Compliance officers read all prospects" ON prospects
  FOR SELECT
  USING (
    (auth.jwt() -> 'user_metadata' ->> 'role') = 'compliance_officer'
  );
