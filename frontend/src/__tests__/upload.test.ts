import { describe, it, expect } from 'vitest';
import { humanizeUploadReason } from '../lib/upload';

describe('humanizeUploadReason', () => {
  it('humanizes "unsupported format" to user-friendly message', () => {
    expect(humanizeUploadReason('unsupported format')).toBe(
      "This file type isn't supported. Try JPEG, PNG, or HEIC."
    );
  });

  it('humanizes "too large" to user-friendly message', () => {
    expect(humanizeUploadReason('too large')).toBe(
      "This photo is over 25 MB and was skipped."
    );
  });

  it('returns server message verbatim for unknown reasons', () => {
    expect(humanizeUploadReason('some unknown error')).toBe('some unknown error');
  });
});
