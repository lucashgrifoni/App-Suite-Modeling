/**
 * Optional: set VITE_REPO_URL in `.env` for correct GitHub / docs links.
 * Example: VITE_REPO_URL=https://github.com/your-org/your-repo
 */
const fallback = "https://github.com";

export const repoUrl: string =
  typeof import.meta.env.VITE_REPO_URL === "string" &&
  import.meta.env.VITE_REPO_URL.length > 0
    ? import.meta.env.VITE_REPO_URL
    : fallback;

export const docsReadmeUrl = `${repoUrl.replace(/\/$/, "")}/blob/main/docs/README.md`;

/** Issues URL; if VITE_REPO_URL is unset, points to generic GitHub (set env for a real repo). */
export const issuesUrl =
  repoUrl === fallback ? fallback : `${repoUrl.replace(/\/$/, "")}/issues`;
