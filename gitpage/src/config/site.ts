/**
 * Repository the landing page links to.
 *
 * The default is this project's own repository, not a placeholder. The previous fallback was
 * the bare `https://github.com`, and since the Pages workflow never sets `VITE_REPO_URL`,
 * every "View on GitHub", "Docs" and "Issues" call to action on the published site dropped
 * the visitor on GitHub's homepage. A dead CTA on a landing page costs more than a wrong one:
 * it reads as an abandoned project.
 *
 * Override with `VITE_REPO_URL` when building a fork.
 */
const defaultRepoUrl = "https://github.com/lucashgrifoni/App-Suite-Modeling";

export const repoUrl: string =
  typeof import.meta.env.VITE_REPO_URL === "string" &&
  import.meta.env.VITE_REPO_URL.length > 0
    ? import.meta.env.VITE_REPO_URL
    : defaultRepoUrl;

const base = repoUrl.replace(/\/$/, "");

export const docsReadmeUrl = `${base}/blob/main/docs/README.md`;
export const issuesUrl = `${base}/issues`;
