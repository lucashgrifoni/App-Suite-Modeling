/**
 * Does a file name match an `accept` list like `.yaml,.yml,.json`?
 *
 * The import page declares one such list per artifact type and hands it to both the file
 * input and the drop zone's "Accepted types" line. Nothing checked a selection that was
 * made under a *previous* type, so a well-formed `main.tf` stayed selected after the type
 * changed to OpenAPI and was submitted as YAML, producing an error that blamed the file.
 *
 * Extensions only — `accept` also permits MIME types and wildcards in HTML, but every list
 * in this app is extensions, and a name is all a `File` reliably carries.
 */
export function fileMatchesAccept(fileName: string, accept: string): boolean {
  const name = fileName.trim().toLowerCase();
  const extensions = accept
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter((e) => e.startsWith("."));
  if (extensions.length === 0) return true;
  return extensions.some((ext) => name.endsWith(ext));
}
