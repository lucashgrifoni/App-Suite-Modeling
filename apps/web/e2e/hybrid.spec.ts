/**
 * Fluxos críticos com API FastAPI real (sem mocks de fetch).
 * Executar: npm run e2e:hybrid (requer Python + otm_api instalado).
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import type { OtmDocument } from "../src/types/document";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const minimalDoc = JSON.parse(
  readFileSync(path.join(__dirname, "fixtures", "minimal-document.json"), "utf-8"),
) as Record<string, unknown>;

test("a reimportação OpenAPI preserva decisões e só grava após confirmação", async ({ page }) => {
  const header = "openapi: 3.0.0\ninfo: {title: Orders, version: '1'}\n";
  const previous = header + "paths: {/orders: {get: {operationId: listOrders}}, /old: {get: {}}}\n";
  const revised = header + "paths: {/orders: {get: {operationId: listOrders}, post: {}}, /latest: {get: {}}}\n";
  const seeded = await page.request.post("/api/v1/imports/openapi", {
    multipart: { file: { name: "original.yaml", mimeType: "application/yaml", buffer: Buffer.from(previous) } },
  });
  expect(seeded.ok()).toBe(true);
  const { document: initial } = await seeded.json();
  initial.components[1].description = "Escopo revisado pelo modelador.";
  initial.threats = [{
    id: "order_exposure", title: "Exposição de pedidos", stride: "information_disclosure",
    target_component_id: initial.components[1].id, treatment_status: "accepted_risk",
    treatment_notes: "Decisão vigente.", assignee: "Equipe de Pedidos", metadata: { risk_review_date: "2027-01-12" },
  }];
  await page.addInitScript((seed: OtmDocument) => {
    if (!sessionStorage.getItem("otm.web.document")) {
      sessionStorage.setItem("otm.web.document", JSON.stringify(seed));
    }
  }, initial);
  await page.goto("/import");
  for (const [label, name, body] of [
    ["Contrato usado na última importação", "original.yaml", previous],
    ["Contrato revisado", "revised.yaml", revised],
  ]) {
    await page.getByLabel(label).setInputFiles({ name, mimeType: "application/yaml", buffer: Buffer.from(body) });
  }
  await page.getByRole("button", { name: "Comparar contratos" }).click();
  const review = page.getByRole("region", { name: "Prévia da atualização" });
  await expect(review.getByText("POST /orders", { exact: true })).toBeVisible();
  await expect(review.getByText("GET /old", { exact: true })).toBeVisible();
  await expect(review.getByText("Modelo atual: Escopo revisado pelo modelador.")).toBeVisible();
  const readModel = () => page.evaluate(() => JSON.parse(sessionStorage.getItem("otm.web.document") ?? "null"));
  expect(await readModel()).toEqual(initial);

  await review.getByRole("button", { name: "Aplicar alterações sem conflito" }).click();
  await expect(page.getByText("Modelo atualizado. Rode a análise novamente.")).toBeVisible();
  await page.reload();
  const saved = await readModel();
  expect(saved.data_flows[0].metadata.openapi_operations_count).toBe(3);
  expect(saved.components[1].description).toBe(initial.components[1].description);
  expect(saved.trust_boundaries).toEqual(initial.trust_boundaries);
  expect(saved.threats[0]).toMatchObject(initial.threats[0]);
});

test("a referência de verificação acompanha a decisão e o relatório", async ({ page }) => {
  const seed = {
    ...minimalDoc,
    threats: [{
      id: "reviewed_false_positive", title: "Resultado revisado",
      stride: "spoofing", treatment_status: "in_progress", risk: { likelihood: 2, impact: 2 },
    }],
  };
  await page.addInitScript((model) => {
    if (!sessionStorage.getItem("otm.web.document")) {
      sessionStorage.setItem("otm.web.document", JSON.stringify(model));
    }
  }, seed);
  await page.goto("/analysis");
  await page.getByRole("button", { name: "Editar decisão" }).click();
  await page.getByLabel("Estado de tratamento").selectOption("false_positive");
  await page.getByLabel("Justificativa da decisão").fill("Validado na revisão do modelo.");
  await page.getByLabel("Referência de verificação").fill("QA-42");
  await page.getByRole("button", { name: "Salvar decisão" }).click();
  await page.reload();

  await page.getByRole("button", { name: "Editar decisão" }).click();
  await expect(page.getByLabel("Referência de verificação")).toHaveValue("QA-42");
  const confirmation = page.getByRole("checkbox", { name: "Confirmo o falso positivo com esta evidência." });
  await expect(confirmation).not.toBeChecked();
  await confirmation.check();
  await page.getByRole("button", { name: "Salvar decisão" }).click();
  await page.goto("/export");

  const downloadReady = page.waitForEvent("download");
  await page.getByTestId("export-report-md").click();
  const stream = await (await downloadReady).createReadStream();
  if (!stream) throw new Error("Expected a risk report download");
  const chunks = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  const report = Buffer.concat(chunks).toString("utf8");
  expect(report).toContain("QA-42");
  expect(report).toContain("Validado na revisão do modelo.");
});

test("o aceite com responsável e data acompanha o modelo e o relatório", async ({ page }) => {
  await page.addInitScript((seed: string) => {
    if (!sessionStorage.getItem("otm.web.document")) sessionStorage.setItem("otm.web.document", seed);
  }, JSON.stringify(minimalDoc));
  await page.goto("/analysis");
  await page.getByRole("button", { name: "Gerar análise" }).click();
  await page.getByRole("button", { name: "Registrar decisão" }).click();
  await page.getByLabel("Estado de tratamento").selectOption("accepted_risk");
  await page.getByLabel("Justificativa da decisão").fill("Revisar a identidade do serviço.");
  await page.getByLabel("Responsável pelo risco").fill("Equipe de Arquitetura");
  await page.getByLabel("Data de revisão").fill("2027-01-12");
  await page.getByRole("button", { name: "Salvar decisão" }).click();
  const stored = page.getByLabel("Selecionar ameaça declarada");
  await expect(stored).toBeVisible();
  const id = await stored.inputValue();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(stored).toHaveValue(id);
  await page.getByRole("button", { name: "Gerar análise" }).click();
  await expect(page.getByTestId("cockpit-priorities")).toBeVisible();
  await page.getByRole("button", { name: "Editar decisão" }).click();
  await expect(page.getByLabel("Responsável pelo risco")).toHaveValue("Equipe de Arquitetura");
  await expect(page.getByLabel("Data de revisão")).toHaveValue("2027-01-12");
  await page.getByLabel("Data de revisão").fill("2027-01-20");
  await page.getByRole("button", { name: "Salvar decisão" }).click();
  await page.goto("/export");
  await page.locator("#document_json").check();
  await page.getByRole("button", { name: "Gerar ficheiros" }).click();
  const downloadReady = page.waitForEvent("download");
  await page
    .getByTestId("export-download-section")
    .locator("li")
    .filter({ hasText: "document_json" })
    .getByRole("button")
    .click();
  const stream = await (await downloadReady).createReadStream();
  if (!stream) throw new Error("Expected a model JSON download");
  const chunks = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  const doc = JSON.parse(Buffer.concat(chunks).toString("utf8")) as OtmDocument;
  expect(doc.threats).toHaveLength(1);
  expect(doc.threats[0]).toMatchObject({
    id,
    treatment_status: "accepted_risk",
    treatment_notes: "Revisar a identidade do serviço.",
    assignee: "Equipe de Arquitetura",
    metadata: { risk_review_date: "2027-01-20", engine_heuristic: true },
  });
  const validation = await page.request.post("/api/v1/models/validate", { data: { document: doc } });
  expect(validation.ok()).toBe(true);

  const reportReady = page.waitForEvent("download");
  await page.getByTestId("export-report-md").click();
  const reportPath = await (await reportReady).path();
  if (!reportPath) throw new Error("Expected a risk report download");
  const report = readFileSync(reportPath, "utf8");
  const treatment = report.split("## Tratamento das ameaças declaradas")[1]?.split("\n## ")[0];
  expect(treatment).toContain(id);
  expect(treatment).toContain("Fila de revisão de riscos aceitos");
  expect(treatment).toContain("Revisar a identidade do serviço.");
  expect(treatment).toContain("Responsável: Equipe de Arquitetura");
  expect(treatment).toContain("Data de revisão: 2027-01-20");

  const pdfReady = page.waitForEvent("download");
  await page.getByTestId("export-pdf").click();
  const pdfPath = await (await pdfReady).path();
  if (!pdfPath) throw new Error("Expected a PDF download");
  expect(readFileSync(pdfPath).subarray(0, 5).toString()).toBe("%PDF-");

  await page.evaluate(() => {
    const key = "otm.web.document";
    const current = JSON.parse(sessionStorage.getItem(key)!);
    current.threats[0].treatment_notes = "Justificativa atualizada depois da exportação.";
    sessionStorage.setItem(key, JSON.stringify(current));
  });
  await page.goto("/history");
  await expect(page.getByTestId("history-list").getByRole("button").first()).toBeVisible();
  const historyReady = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar Markdown", exact: true }).click();
  const historyPath = await (await historyReady).path();
  if (!historyPath) throw new Error("Expected a revision report download");
  const historicalReport = readFileSync(historyPath, "utf8");
  expect(historicalReport).toContain(id);
  expect(historicalReport).toContain("Revisar a identidade do serviço.");
  expect(historicalReport).toContain("Data de revisão: 2027-01-20");
  expect(historicalReport).not.toContain("Justificativa atualizada depois da exportação.");
  expect(historicalReport).toContain("Análise gerada na exportação a partir do modelo fornecido.");
});

test("o diagrama mantém as fronteiras e permite inspecionar um componente no celular", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript((seed: string) => {
    sessionStorage.setItem("otm.web.document", seed);
  }, JSON.stringify(minimalDoc));
  await page.goto("/review");
  await expect(page.locator('[data-boundary-id="internet"]')).toHaveText("Internet");
  await expect(page.locator('[data-boundary-id="vpc"]')).toHaveText("Conta cloud / VPC");
  await page.getByRole("button", { name: "Visualizar", exact: true }).click();
  await page.getByRole("button", { name: "API", exact: true }).last().press("Enter");
  const inspector = page.locator(".diagram-inspector");
  await expect(inspector.getByRole("heading", { name: "API" })).toBeVisible();
  await expect(inspector.getByText("Conta cloud / VPC")).toBeVisible();
  await expect(inspector.getByText("REST", { exact: true })).toBeVisible();
  await expect(inspector.getByText(/Registos de pedidos/)).toBeVisible();
  await expect(inspector.locator("#dm-label")).toHaveCount(0);
  await page.getByRole("button", { name: "Navegação" }).click();
  await page.locator("#workspace-nav").getByRole("link", { name: "Análise" }).press("Enter");
  await expect(page).toHaveURL(/\/analysis$/);
});

test("híbrido: análise real — cockpit e pré-check a partir do motor", async ({ page }) => {
  await page.addInitScript((docJson: string) => {
    sessionStorage.setItem("otm.web.document", docJson);
  }, JSON.stringify(minimalDoc));

  await page.goto("/analysis");
  await page.selectOption("#methodology", "stride");
  await page.getByRole("button", { name: "Gerar análise" }).click();

  await expect(page.getByTestId("cockpit-executive-strip")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("decision-cockpit")).toBeVisible();
  await expect(page.getByText(/pré-check/i).first()).toBeVisible();
  await expect(page.getByTestId("cockpit-priorities")).toBeVisible();
});

test("híbrido: compare real — diff semântico e meta v1.5", async ({ page }) => {
  const revised = {
    ...minimalDoc,
    components: [
      ...(minimalDoc.components as object[]),
      { id: "hybrid_svc", name: "Serviço híbrido", kind: "process" },
    ],
  };

  await page.addInitScript((docJson: string) => {
    sessionStorage.setItem("otm.web.document", docJson);
  }, JSON.stringify(minimalDoc));

  await page.goto("/diff");
  await page.locator("#revised-json").fill(JSON.stringify(revised));
  await page.getByRole("checkbox", { name: /Incluir análise/i }).check();
  await page.getByRole("button", { name: "Comparar" }).click();

  await expect(page.getByTestId("diff-semantic-panel")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("diff-structural-refs")).toBeVisible();
  // `semantic_interpretation_links` pode estar vazio (v1.5) — validar mudança estrutural na UI.
  await expect(page.getByText("Estrutura", { exact: true })).toBeVisible();
});

test("híbrido: export real — artefactos com análise do motor", async ({ page }) => {
  await page.addInitScript((docJson: string) => {
    sessionStorage.setItem("otm.web.document", docJson);
  }, JSON.stringify(minimalDoc));

  await page.goto("/analysis");
  await page.selectOption("#methodology", "stride");
  await page.getByRole("button", { name: "Gerar análise" }).click();
  await expect(page.getByTestId("cockpit-priorities")).toBeVisible({ timeout: 60_000 });

  await page.getByRole("button", { name: "Exportar resultados" }).click();
  await expect(page).toHaveURL(/\/export/);
  await page.getByRole("button", { name: "Gerar ficheiros" }).click();
  await expect(page.getByRole("heading", { name: "Descarregar" })).toBeVisible({ timeout: 60_000 });
});
