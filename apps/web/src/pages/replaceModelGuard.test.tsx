/**
 * Replacing the session model asks first, and the replacement opens the wizard at step 1.
 *
 * Two defects met on the same click. A model built over an afternoon lives only in the
 * session — History holds nothing until an analysis or an export has run — yet "Use this
 * template", the import page's "Generate draft" and the home page's "Create new model"
 * destroyed it with no dialog at all, while the two sibling replacements ("New model" in the
 * header, Restore on History) both asked. And the wizard step, being stored per tab rather
 * than per document, survived the swap: a brand-new draft the user had never seen opened on
 * "4. Finish · Ready to review" with only "Back" and "View logical diagram" offered.
 *
 * The confirmation text is asserted literally, not through `i18n.t()`. Comparing against
 * `t(key)` passes even when the key is missing from the bundles, because i18next then returns
 * the key itself on both sides — which is exactly how a dialog reading
 * "session.confirmReplaceModel" would have reached a user.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HomePage } from "./HomePage";
import { ImportPage } from "./ImportPage";
import { TemplatesPage } from "./TemplatesPage";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import i18n from "../i18n/i18n";
import type { OtmDocument } from "../types/document";

const DOC_KEY = "otm.web.document";
const STEP_KEY = "otm.web.wizard.step";
const CONFIRM_EN = "This replaces the model in this session, and this is its only copy. Continue?";

const USER_MODEL = {
  model: {
    schema_version: "1.0.0",
    system_type: "web_application",
    industry_sector: "generic",
    methodology: "stride",
  },
  metadata: { title: "Payments Platform - 2 hours of work", tags: [] },
  components: [{ id: "web_ui", name: "Customer Web UI", kind: "process" }],
  data_flows: [],
  trust_boundaries: [],
  assets: [],
  threats: [],
  mitigations: [],
  evidence_suggestions: [],
} as unknown as OtmDocument;

const REPLACEMENT = {
  ...USER_MODEL,
  metadata: { title: "Orders API (rascunho OpenAPI)", tags: [] },
};

const navigate = vi.fn();
vi.mock("react-router", async () => ({
  ...(await vi.importActual<typeof import("react-router")>("react-router")),
  useNavigate: () => navigate,
}));

vi.mock("../api/otmApi", () => ({
  listTemplates: () =>
    Promise.resolve([
      { id: "admin-portal", title: "Portal admin", description: "d", tags: [], category: "applications" },
    ]),
  instantiateTemplate: () => Promise.resolve({ document: REPLACEMENT }),
  importArtifact: () => Promise.resolve({ document: REPLACEMENT, inferences: [], unknowns: [] }),
  createBlankModel: () => Promise.resolve({ document: REPLACEMENT }),
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

/** The import page only submits once a file is attached to its input. */
async function attachFile(user: ReturnType<typeof userEvent.setup>) {
  const input = document.querySelector('input[type="file"]');
  await user.upload(input as HTMLInputElement, new File(["openapi: 3.0.0\n"], "orders.yaml"));
}

const ENTRY_POINTS: {
  label: string;
  page: ReactNode;
  act: (user: ReturnType<typeof userEvent.setup>) => Promise<void>;
}[] = [
  {
    label: '"Use this template"',
    page: <TemplatesPage />,
    act: async (user) => {
      await user.click(await screen.findByRole("button", { name: /Use this template/i }));
    },
  },
  {
    label: '"Generate draft" on the import page',
    page: <ImportPage />,
    act: async (user) => {
      await attachFile(user);
      await user.click(screen.getByRole("button", { name: /Generate draft/i }));
    },
  },
  {
    label: '"Create new model" on the home page',
    page: <HomePage />,
    act: async (user) => {
      await user.click(screen.getAllByRole("button", { name: /Create new model/i })[0]);
    },
  },
];

beforeEach(async () => {
  await i18n.changeLanguage("en");
  sessionStorage.setItem(DOC_KEY, JSON.stringify(USER_MODEL));
  sessionStorage.setItem(STEP_KEY, "3");
  navigate.mockClear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe.each(ENTRY_POINTS)("$label with a model already in the session", ({ page, act }) => {
  it("asks before discarding the model", async () => {
    const confirmSpy = vi.spyOn(globalThis, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(page, { wrapper: Providers });

    await act(user);

    expect(confirmSpy).toHaveBeenCalledWith(CONFIRM_EN);
  });

  it("keeps the user's model when the answer is no", async () => {
    vi.spyOn(globalThis, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(page, { wrapper: Providers });

    await act(user);

    expect(sessionStorage.getItem(DOC_KEY)).toContain("Payments Platform");
    expect(navigate).not.toHaveBeenCalled();
  });

  it("replaces the model once the user confirms", async () => {
    vi.spyOn(globalThis, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(page, { wrapper: Providers });

    await act(user);

    await waitFor(() => expect(sessionStorage.getItem(DOC_KEY)).toContain("Orders API"));
  });

  it("opens the wizard at step 1 for the document the user has never seen", async () => {
    vi.spyOn(globalThis, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(page, { wrapper: Providers });

    await act(user);

    await waitFor(() => expect(sessionStorage.getItem(STEP_KEY)).toBeNull());
  });
});

describe("the confirmation is translated", () => {
  it("is not the raw i18n key in English", () => {
    expect(i18n.t("session.confirmReplaceModel")).toBe(CONFIRM_EN);
  });

  it("is Portuguese on the Portuguese UI", async () => {
    await i18n.changeLanguage("pt-BR");
    const message = i18n.t("session.confirmReplaceModel");
    await i18n.changeLanguage("en");

    expect(message).toBe("Isto substitui o modelo desta sessão, e esta é a única cópia. Continuar?");
  });
});

describe("with nothing to lose", () => {
  it("does not ask when the session has no model", async () => {
    sessionStorage.removeItem(DOC_KEY);
    const confirmSpy = vi.spyOn(globalThis, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<TemplatesPage />, { wrapper: Providers });

    await user.click(await screen.findByRole("button", { name: /Use this template/i }));

    expect(confirmSpy).not.toHaveBeenCalled();
  });
});
