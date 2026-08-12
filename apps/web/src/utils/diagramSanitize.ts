/**
 * Strips HTML and trims user-provided diagram labels to reduce XSS risk.
 * The UI must never render raw HTML from these strings as `dangerouslySetInnerHTML`.
 */

/** Collapses every run of whitespace. Linear: `\s+` is greedy with nothing after it to backtrack for. */
const WHITESPACE_RUN = /\s+/g;

/**
 * Removes every `<…>` span. Behaviour is identical to the `/<[^>]*>/g` this replaces,
 * including the greedy case — in `"<a<b>"` the whole `"<a<b>"` goes, because the run
 * between the first `<` and the first `>` may itself contain `<` — and an unterminated
 * trailing `<` is kept verbatim.
 *
 * The regex was quadratic, and reachable: `[^>]*` cannot cross a `>`, so a `<` with no
 * `>` after it costs a scan to the end of the input and the engine then retries at the
 * next `<`. A label of `<` characters pasted into the wizard's component name measured
 * 62 ms at 16k chars, 233 ms at 32k and 948 ms at 64k — a frozen main thread, since the
 * length cap is applied only after this strip. An atomic-group rewrite does not help:
 * the cost is the restart at every `<`, not backtracking inside one attempt.
 *
 * Index scanning never revisits a character, so this is linear: 400k `<` in under a
 * millisecond.
 */
function stripHtmlTags(input: string): string {
  let out = "";
  let cursor = 0;
  let open = input.indexOf("<");
  while (open !== -1) {
    const close = input.indexOf(">", open + 1);
    if (close === -1) break;
    out += input.slice(cursor, open);
    cursor = close + 1;
    open = input.indexOf("<", cursor);
  }
  return out + input.slice(cursor);
}

export function sanitizeDiagramLabel(raw: string, maxLen = 120): string {
  const s = stripHtmlTags(raw).replaceAll(WHITESPACE_RUN, " ").trim();
  if (s.length <= maxLen) return s;
  return `${s.slice(0, maxLen - 1)}…`;
}
