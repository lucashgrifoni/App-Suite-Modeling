/**
 * Strips HTML and trims user-provided diagram labels to reduce XSS risk.
 * The UI must never render raw HTML from these strings as `dangerouslySetInnerHTML`.
 */
const HTML_TAG = /<[^>]*>/g;

export function sanitizeDiagramLabel(raw: string, maxLen = 120): string {
  const s = raw.replace(HTML_TAG, "").replace(/\s+/g, " ").trim();
  if (s.length <= maxLen) return s;
  return `${s.slice(0, maxLen - 1)}…`;
}
