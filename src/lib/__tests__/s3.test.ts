import { describe, it, expect } from 'vitest';
import { parseS3Uri, S3FetchError } from '../s3';

// ─── parseS3Uri ───────────────────────────────────────────────────────────────

describe('parseS3Uri', () => {
  it('parses a well-formed URI', () => {
    const ref = parseS3Uri('s3://my-bucket/path/to/object.txt');
    expect(ref.bucket).toBe('my-bucket');
    expect(ref.key).toBe('path/to/object.txt');
  });

  it('parses a URI with a single-segment key', () => {
    const ref = parseS3Uri('s3://compliance-uploads/draft.txt');
    expect(ref.bucket).toBe('compliance-uploads');
    expect(ref.key).toBe('draft.txt');
  });

  it('parses a URI with deeply nested key', () => {
    const ref = parseS3Uri('s3://acme/advisors/a1/emails/2026/03/draft-abc.txt');
    expect(ref.bucket).toBe('acme');
    expect(ref.key).toBe('advisors/a1/emails/2026/03/draft-abc.txt');
  });

  it('throws on missing s3:// scheme', () => {
    expect(() => parseS3Uri('https://s3.amazonaws.com/bucket/key')).toThrow(/must start with s3:\/\//);
  });

  it('throws when there is no key after bucket', () => {
    expect(() => parseS3Uri('s3://bucket-only')).toThrow(/bucket and key/);
  });

  it('throws when bucket is empty (leading slash after scheme)', () => {
    expect(() => parseS3Uri('s3:///key-only')).toThrow(/cannot parse bucket and key/);
  });

  it('throws on bare s3:// with no path', () => {
    expect(() => parseS3Uri('s3://')).toThrow();
  });
});

// ─── S3FetchError ─────────────────────────────────────────────────────────────

describe('S3FetchError', () => {
  it('is an instance of Error', () => {
    const err = new S3FetchError('oops');
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe('S3FetchError');
    expect(err.message).toBe('oops');
  });
});
