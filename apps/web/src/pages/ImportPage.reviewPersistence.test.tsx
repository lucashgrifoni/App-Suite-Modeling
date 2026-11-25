/**
 * The inference panel is the review step the product tells the user to perform — "Import
 * with explicit inferences: review before running the engine", "Check the inference list
 * before going to analysis" — and it was erased by F5.
 *
 * Measured: four inference lines before the refresh, zero after, while
 * `sessionStorage["otm.web.document"]` still held the imported draft. The user was left with
 * a document whose stated review artifact had vanished, with no message and no way back
 * short of re-importing, which itself now prompts to replace the model.
 *
 * A refresh is simulated by unmounting and mounting the page again: both start from an
 * empty component state and read sessionStorage, which is the whole mechanism under test.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ImportPage } from "./ImportPage";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import i18n from "../i18n/i18n";
import type { OtmDocument } from "../types/document";

const DOC_KEY = "otm.web.document";

/**
 * Deliberately NOT pre-normalised — no `tags`, no empty `assets`/`threats`/… — because that
 * is what the import endpoint actually returns. The session normalises a document before
 * storing it, so a fingerprint taken from the raw response would not match the one taken
 * from the session on the next page load, and the review would be withheld from the very
 * draft it belongs to. Filling these in here would hide that.
 */
const DRAFT = {
  model: {
    schema_version: "1.0.0",
    system_type: "api_backend",
    industry_sector: "generic",
    methodology: "stride",
  },
  metadata: { title: "Orders API (rascunho OpenAPI)" },
  components: [{ id: "api", name: "API", kind: "process" }],
  data_flows: [],
} as unknown as OtmDocument;

const OTHER_MODEL = {
  ...DRAFT,
  metadata: { title: "Something else entirely" },
};

const INFERENCE_TEXT = "Pistas de autenticacao presentes em securitySchemes";
const UNKNOWN_TEXT = "Ativo generico de payloads de API adicionado.";

vi.mock("react-router", async () => ({
  ...(await vi.importActual<typeof import("react-router")>("react-router")),
  useNavigate: () => vi.fn(),
}));

vi.mock("../api/otmApi", () => ({
  importArtifact: () =>
    Promise.resolve({
      document: DRAFT,
      inferences: [{ id: "auth", confidence: "high", message: INFERENCE_TEXT }],
      unknowns: [UNKNOWN_TEXT],
      explanations: null,
    }),
}));

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter>
      <ToastProvider>
        <SessionProvider>{children}</SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

async function importAFile() {
  const user = userEvent.setup();
  const view = render(<ImportPage />, { wrapper: Providers });
  const input = document.querySelector('input[type="file"]');
  await user.upload(input as HTMLInputElement, new File(["openapi: 3.0.0\n"], "orders.yaml"));
  await user.click(screen.getByRole("button", { name: /Generate draft/i }));
  await screen.findByText(INFERENCE_TEXT, { exact: false });
  return view;
}

/** Everything a browser keeps across F5: sessionStorage survives, component state does not. */
function refresh(view: { unmount: () => void }) {
  view.unmount();
  return render(<ImportPage />, { wrapper: Providers });
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

describe("import review survives a refresh", () => {
  it("shows the inference list after the import", async () => {
    await importAFile();
    expect(screen.getByText(INFERENCE_TEXT, { exact: false })).toBeInTheDocument();
  });

  it("still shows it after a refresh", async () => {
    const view = await importAFile();
    refresh(view);
    expect(await screen.findByText(INFERENCE_TEXT, { exact: false })).toBeInTheDocument();
  });

  it("still shows the not-inferred list after a refresh", async () => {
    const view = await importAFile();
    refresh(view);
    expect(await screen.findByText(UNKNOWN_TEXT)).toBeInTheDocument();
  });

  it("keeps the draft it describes, so the two are not half-restored", async () => {
    const view = await importAFile();
    refresh(view);
    expect(sessionStorage.getItem(DOC_KEY)).toContain("Orders API");
  });

  /**
   * The pairing guard. A review describes one exact draft; presenting it beside a different
   * model would be a worse failure than presenting nothing, and this tool's output is what
   * an auditor reads.
   */
  it("withholds the review when the session holds a different model", async () => {
    const view = await importAFile();
    view.unmount();
    sessionStorage.setItem(DOC_KEY, JSON.stringify(OTHER_MODEL));

    render(<ImportPage />, { wrapper: Providers });

    await waitFor(() => expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument());
    expect(screen.queryByText(INFERENCE_TEXT, { exact: false })).toBeNull();
  });

  it("shows no review on a first visit with nothing imported", () => {
    render(<ImportPage />, { wrapper: Providers });
    expect(screen.queryByText(INFERENCE_TEXT, { exact: false })).toBeNull();
  });
});
