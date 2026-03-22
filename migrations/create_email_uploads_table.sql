-- Create email_uploads table
CREATE TABLE email_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID REFERENCES compliance_submissions(id) ON DELETE CASCADE,
  advisor_id UUID NOT NULL,
  file_name TEXT NOT NULL,
  file_size_bytes BIGINT,
  content_type TEXT,
  storage_path TEXT NOT NULL,
  signed_url TEXT,
  signed_url_expires_at TIMESTAMP,
  uploaded_at TIMESTAMP DEFAULT now(),
  created_at TIMESTAMP DEFAULT now(),
  CONSTRAINT unique_storage_path UNIQUE (storage_path)
);

-- Create outreach_submissions table
CREATE TABLE outreach_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  advisor_id UUID NOT NULL,
  prospect_id UUID REFERENCES prospects(id),
  email_upload_id UUID REFERENCES email_uploads(id),
  recipients TEXT[],
  recipient_count INT,
  status TEXT DEFAULT 'sent',
  sent_at TIMESTAMP DEFAULT now(),
  created_at TIMESTAMP DEFAULT now()
);

-- Enable Row-Level Security (RLS) on email_uploads
ALTER TABLE email_uploads ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Advisors can only access their own uploads
CREATE POLICY "Allow advisors to access their uploads" ON email_uploads
  FOR ALL
  USING (auth.uid() = advisor_id);

-- RLS Policy: Compliance officers can access all uploads
CREATE POLICY "Allow compliance officers to access all uploads" ON email_uploads
  FOR ALL
  USING (auth.role() = 'compliance_officer');