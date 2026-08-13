/**
 * "Premium PDF" against a server that cannot render PDFs.
 *
 * The button produced a red alert reading exactly "Internal Server Error" — the raw HTTP
 * reason phrase — while the response body carried the server's own sentence and a
 * `request_id`. Two separate faults met there. The route builds its own `ApiError` by hand
 * because it reads a binary body rather than JSON, and it handed that error the raw response
 * TEXT as `body`; everything that presents an error reads the envelope off `body`, so a
 * string meant none of it applied. And the API's unhandled-exception handler answers
 * `{code, message, request_id}` at the top level while every other handler nests the same
 * envelope under `detail`, which was the only shape the client knew.
 *
 * The Python side of the original defect — an `OSError` from the native PDF stack escaping
 * an `except ImportError` — belongs to the CLI lane. This covers the contract from the
 * browser's side: whichever of the two the server sends, the person at the screen gets
 * something they can act on.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ExportPage } from "./ExportPage";
import { AnalysisHistoryProvider } from "../context/AnalysisHistoryContext";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import i18n from "../i18n/i18n";
import type { OtmDocument } from "../types/document";

// jsPDF pulls a canvas/font stack jsdom cannot run; the server-side buttons are the subject.
vi.mock("../lib/generateReportPdf", () => ({
  generateReportPdfBlob: vi.fn(),
  downloadPdfBlob: vi.fn(),
}));

const DOC_KEY = "otm.web.document";

const MODEL = {
  model: {
    schema_version: "1.0.0",
    system_type: "web_application",
    industry_sector: "generic",
    methodology: "stride",
  },
  metadata: { title: "Payments Gateway", tags: [] },
  components: [{ id: "api", name: "Api", kind: "process" }],
  data_flows: [],
  trust_boundaries: [],
  assets: [],
  threats: [],
  mitigations: [],
  evidence_suggestions: [],
} as unknown as OtmDocument;

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter initialEntries={["/export"]}>
      <ToastProvider>
        <SessionProvider>
          <AnalysisHistoryProvider>{children}</AnalysisHistoryProvider>
        </SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

function respondWith(status: number, statusText: string, body: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      statusText,
      text: () => Promise.resolve(body),
    } as Response),
  );
}

async function clickPremiumPdf() {
  render(<ExportPage />, { wrapper: Providers });
  await userEvent.click(screen.getByTestId("export-premium-pdf"));
  return screen.findAllByRole("alert");
}

/** Everything the page put in front of the user, alerts and toasts alike. */
async function messages(): Promise<string> {
  const alerts = await clickPremiumPdf();
  return alerts.map((a) => a.textContent ?? "").join("\n");
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  sessionStorage.setItem(DOC_KEY, JSON.stringify(MODEL));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("premium PDF against a server with no PDF backend", () => {
  const PDF_501 = JSON.stringify({
    detail: {
      code: "PDF_DEPENDENCY",
      message:
        "PDF requer o pacote opcional: pip install 'open-threat-model[report]' ou pip install xhtml2pdf",
    },
  });

  it("states what happened in words the user can act on", async () => {
    respondWith(501, "Not Implemented", PDF_501);

    expect(await messages()).toContain(i18n.t("apiErrors.codes.PDF_DEPENDENCY"));
  });

  it("points at the alternative that works on this same page", async () => {
    respondWith(501, "Not Implemented", PDF_501);

    expect(await messages()).toContain(i18n.t("export.premiumMd"));
  });

  it("does not show a server-side pip command to a browser user", async () => {
    respondWith(501, "Not Implemented", PDF_501);

    expect(await messages()).not.toContain("pip install");
  });

  it("never shows the bare HTTP reason phrase", async () => {
    respondWith(501, "Not Implemented", PDF_501);

    expect(await messages()).not.toContain("Not Implemented");
  });
});

describe("premium PDF against a server that crashed", () => {
  const INTERNAL_500 = JSON.stringify({
    code: "INTERNAL_ERROR",
    message: "An unexpected error occurred.",
    request_id: "adadde6c-5ec1-4285-8cf5-3b84b3f54fe2",
  });

  it("shows the server's own sentence, not 'Internal Server Error'", async () => {
    respondWith(500, "Internal Server Error", INTERNAL_500);
    const text = await messages();

    expect(text).toContain("An unexpected error occurred.");
    expect(text).not.toContain("Internal Server Error");
  });

  it("shows the request id, so the failure can be found in the server log", async () => {
    respondWith(500, "Internal Server Error", INTERNAL_500);

    expect(await messages()).toContain("adadde6c-5ec1-4285-8cf5-3b84b3f54fe2");
  });

  it("still falls back to the reason phrase when the server sent no body", async () => {
    respondWith(500, "Internal Server Error", "");

    expect(await messages()).toContain("Internal Server Error");
  });
});
