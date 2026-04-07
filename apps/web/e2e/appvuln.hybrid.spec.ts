/**
 * Matriz APPVULN: percorre todos os casos do wizard (catálogo → review → análise).
 * Variáveis: APPVULN_UI_MATRIX (JSON com cases), APPVULN_RESULTS_ROOT (pasta de saída).
 */
import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

type MatrixCase = {
  lab_id: string;
  template_id: string;
  case_key: string;
};

type CaseResult = {
  case_key: string;
  lab_id: string;
  template_id: string;
  ok: boolean;
  error?: string;
  screenshot?: string;
};

function loadCases(): MatrixCase[] {
  const matrixPath = process.env.APPVULN_UI_MATRIX;
  if (!matrixPath || !fs.existsSync(matrixPath)) {
    throw new Error(`APPVULN_UI_MATRIX missing or not found: ${matrixPath ?? "<unset>"}`);
  }
  const payload = JSON.parse(fs.readFileSync(matrixPath, "utf-8")) as { cases: Array<Record<string, unknown>> };
  return payload.cases.map((item) => {
    const lab = typeof item.lab_id === "string" ? item.lab_id : String(item.lab_id ?? "");
    const dir =
      item.case_dir_name === undefined || item.case_dir_name === null
        ? ""
        : String(item.case_dir_name);
    const tpl = typeof item.template_id === "string" ? item.template_id : String(item.template_id ?? "");
    const fallbackKey = dir ? `${lab}/${dir}` : `${lab}/${tpl}`;
    const ck = item.case_key;
    return {
      lab_id: lab,
      template_id: tpl,
      case_key: typeof ck === "string" ? ck : String(ck ?? fallbackKey),
    };
  });
}

function resultsPaths() {
  const resultsRoot = process.env.APPVULN_RESULTS_ROOT;
  if (!resultsRoot) {
    throw new Error("APPVULN_RESULTS_ROOT is required.");
  }
  const runDir = path.join(resultsRoot, "00-controle-geral", "04-log-de-execucao");
  const screenshotDir = path.join(runDir, "auto-ui-screenshots");
  fs.mkdirSync(screenshotDir, { recursive: true });
  return {
    runDir,
    screenshotDir,
    summaryPath: path.join(runDir, "auto-playwright-summary.json"),
  };
}

test("catalog -> wizard -> review works for all template cases", async ({ page }) => {
  test.setTimeout(20 * 60 * 1000);
  const cases = loadCases();
  const paths = resultsPaths();
  const results: CaseResult[] = [];
  const failures: CaseResult[] = [];

  for (const item of cases) {
    const screenshotName = `auto-ui-${item.lab_id}-${item.template_id}.png`;
    const screenshotPath = path.join(paths.screenshotDir, screenshotName);
    try {
      await page.goto("/templates");
      await page.locator("#tpl-search").fill("");
      await page.locator("#tpl-search").fill(item.template_id);
      // Debounce de pesquisa (~280 ms) + render da lista filtrada
      await page.waitForTimeout(450);
      const row = page.getByTestId(`tpl-row-${item.template_id}`);
      await expect(row).toBeVisible({ timeout: 30000 });
      const useBtn = row.getByRole("button", {
        name: /Usar este template|Use this template|Use template/i,
      });
      await expect(useBtn).toBeEnabled({ timeout: 60000 });
      await useBtn.click();

      await expect(page).toHaveURL(/\/wizard$/);
      await expect(page.getByLabel(/Título do modelo|Model title/i)).toBeVisible({ timeout: 15000 });

      await page.goto("/review");
      await expect(page.getByRole("button", { name: /Validar no servidor|Validate on server/i })).toBeVisible({
        timeout: 15000,
      });
      await page.getByRole("button", { name: /Validar no servidor|Validate on server/i }).click();
      await expect(page.getByText(/schema/i)).toBeVisible({ timeout: 15000 });

      await page.getByRole("link", { name: /Correr análise|Run analysis/i }).click();
      await expect(page).toHaveURL(/\/analysis$/);
      await expect(page.getByRole("button", { name: /Recomendar metodologia|Recommend methodology/i })).toBeVisible({
        timeout: 15000,
      });

      await page.screenshot({ path: screenshotPath, fullPage: true });
      results.push({
        case_key: item.case_key,
        lab_id: item.lab_id,
        template_id: item.template_id,
        ok: true,
        screenshot: screenshotPath,
      });
    } catch (error) {
      await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => undefined);
      const result: CaseResult = {
        case_key: item.case_key,
        lab_id: item.lab_id,
        template_id: item.template_id,
        ok: false,
        error: error instanceof Error ? error.message : String(error),
        screenshot: screenshotPath,
      };
      results.push(result);
      failures.push(result);
    }
  }

  const summary = {
    generated_at: new Date().toISOString(),
    total_cases: cases.length,
    ok_cases: results.filter((item) => item.ok).length,
    failed_cases: failures.length,
    results,
  };
  fs.writeFileSync(paths.summaryPath, JSON.stringify(summary, null, 2), "utf-8");

  expect(failures, JSON.stringify(failures, null, 2)).toEqual([]);
});
