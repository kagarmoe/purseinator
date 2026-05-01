/**
 * Humanize upload failure reasons from the server into user-friendly messages.
 * Used in partial upload responses where individual files fail.
 */
export function humanizeUploadReason(reason: string): string {
  const lower = reason.toLowerCase();
  if (lower.includes('unsupported format') || lower.includes('unsupported') || lower.includes('format')) {
    return "This file type isn't supported. Try JPEG, PNG, or HEIC.";
  }
  if (lower.includes('too large') || lower.includes('file too large')) {
    return "This photo is over 25 MB and was skipped.";
  }
  // Default: return server message verbatim
  return reason;
}
