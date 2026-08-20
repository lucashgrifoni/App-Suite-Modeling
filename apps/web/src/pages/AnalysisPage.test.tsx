/**
 * "Run analysis" announced success for a run that never happened.
 *
 * An upstream that answers 200 with a zero-byte body — a captive portal, an SPA-fallback
 * static host, a gateway pointed at the wrong port — reached the analyze handler as a
 * successful result, so the toast read "Analysis generated. Review metrics and threats
 * below." while the page below it still said "Engine not run yet", nothing was stored, and
 * a History snapshot was written for the non-event (`analysis: null`, `maxScore: null`).
 * Every other failure mode (connection refused, 502, timeout) was reported correctly, so
 * only the 2xx path was unguarded.
 *
 * `../api/otmApi` is deliberately NOT mocked: the defect lived in the shared client, and
 * these tests exist to prove the whole path from `fetch` to the toast is fixed.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisPage } from "./AnalysisPage";
import { AnalysisHistoryProvider } from "../context/AnalysisHistoryContext";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import type { OtmDocument } from "../types/document";

const HISTORY_KEY = "otm.analysis.history";

const DOC: OtmDocument = {
  model: {
    schema_version: "1.0.0",
    system_type: "web_application",
    industry_sector: "generic",
    methodology: "stride",
  },
  metadata: { title: "Portal admin", tags: [] },
  components: [{ id: "admin", name: "Administrador", kind: "external_entity" }],
  data_flows: [],
  trust_boundaries: [],
  assets: [],
  threats: [],
  mitigations: [],
  evidence_suggestions: [],
} as unknown as OtmDocument;

function respondWith(body: string, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    statusText: `HTTP ${status}`,
    text: () => Promise.resolve(body),
  } as Response);
}

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter initialEntries={["/analysis"]}>
      <ToastProvider>
        <SessionProvider>
          <AnalysisHistoryProvider>{children}</AnalysisHistoryProvider>
        </SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

async function clickRunAnalysis() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: /Run analysis/i }));
}

beforeEach(() => {
  sessionStorage.setItem("otm.web.document", JSON.stringify(DOC));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("AnalysisPage against an upstream answering 200 with nothing", () => {
  it("does not claim the analysis was generated", async () => {
    vi.stubGlobal("fetch", respondWith(""));

    render(<AnalysisPage />, { wrapper: Providers });
    await clickRunAnalysis();

    await screen.findByRole("alert");
    expect(screen.queryByText(/Analysis generated/)).toBeNull();
  });

  it("tells the user the API could not be reached", async () => {
    vi.stubGlobal("fetch", respondWith(""));

    render(<AnalysisPage />, { wrapper: Providers });
    await clickRunAnalysis();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Could not reach the API/);
  });

  it("writes no History snapshot for a run that never happened", async () => {
    vi.stubGlobal("fetch", respondWith(""));

    render(<AnalysisPage />, { wrapper: Providers });
    await clickRunAnalysis();

    await screen.findByRole("alert");
    expect(localStorage.getItem(HISTORY_KEY)).toBeNull();
  });

  it("leaves the empty state on screen, matching what actually happened", async () => {
    vi.stubGlobal("fetch", respondWith(""));

    render(<AnalysisPage />, { wrapper: Providers });
    await clickRunAnalysis();

    await screen.findByRole("alert");
    expect(screen.getByText(/Engine not run yet/)).toBeInTheDocument();
  });

  it("still records a genuine run, so the guard did not break the success path", async () => {
    vi.stubGlobal(
      "fetch",
      respondWith(
        JSON.stringify({
          engine_version: "0.1.0",
          document_title: "Portal admin",
          methodology: "stride",
          summary: { heuristic_threats_generated: 1, max_risk_score: 12 },
          structural_findings: [],
          trust_boundary_findings: [],
          heuristic_threats: [],
        }),
      ),
    );

    render(<AnalysisPage />, { wrapper: Providers });
    await clickRunAnalysis();

    await screen.findByText(/Analysis generated/);
    await waitFor(() => expect(localStorage.getItem(HISTORY_KEY)).not.toBeNull());
  });
});

/**
 * `"evicted"` e `"failed"` tinham mensagem nos dois idiomas, quatro chamadores e um
 * comentário a explicar porque existem — e nenhum teste a exigi-los. `pushHistoryEntry`
 * é testado a devolver `"evicted"` em `analysisHistoryStorage.test.ts`, mas ninguém
 * verificava que alguém repara nisso: apagar os quatro `else if` deixava a suíte inteira
 * verde, e o utilizador voltava a perder snapshots antigos debaixo de um toast de sucesso
 * sem ressalva — exactamente o defeito que o comentário no código diz já ter acontecido.
 *
 * O mock é em `pushHistoryEntry` e não no contexto, para que a cadeia real
 * armazenamento -> contexto -> página -> toast seja percorrida. O que fica simulado é só a
 * fronteira cujo comportamento próprio já tem testes: em jsdom o `localStorage` não tem
 * quota real, portanto a pressão de espaço não pode ser provocada a sério.
 */
describe("AnalysisPage quando o Histórico não coube todo no browser", () => {
  async function runWithOutcome(outcome: "evicted" | "failed") {
    const storage = await import("../utils/analysisHistoryStorage");
    vi.spyOn(storage, "pushHistoryEntry").mockReturnValue(outcome);
    vi.stubGlobal("fetch", respondWith(JSON.stringify({ threats: [], metrics: {} })));

    render(<AnalysisPage />, { wrapper: Providers });
    await clickRunAnalysis();
  }

  it("avisa que snapshots antigos foram removidos para este caber", async () => {
    await runWithOutcome("evicted");

    await waitFor(() => {
      expect(screen.getByText(/older snapshots were removed/i)).toBeInTheDocument();
    });
  });

  it("diz que este snapshot não foi guardado, em vez de o dar por guardado", async () => {
    await runWithOutcome("failed");

    await waitFor(() => {
      expect(screen.getByText(/was not added to History/i)).toBeInTheDocument();
    });
  });
});
