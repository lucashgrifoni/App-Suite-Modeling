import { useState } from "react";
import { Navigate } from "react-router-dom";
import { exportArtifacts } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Label } from "../components/ui/Label";
import { Checkbox } from "../components/ui/Checkbox";
import { Alert } from "../components/ui/Alert";
import { useSession } from "../context/SessionContext";
import type { ExportFormat } from "../types/api";

const FORMATS: { id: ExportFormat; label: string; hint: string }[] = [
  { id: "document_json", label: "Documento (JSON)", hint: "Modelo canónico" },
  { id: "document_markdown", label: "Documento (Markdown)", hint: "Relatório legível" },
  { id: "flowchart_mermaid", label: "Diagrama Mermaid", hint: "Flowchart LR" },
  { id: "analysis_json", label: "Análise (JSON)", hint: "Resultado completo do motor" },
  { id: "analysis_markdown", label: "Análise (Markdown)", hint: "Secção de relatório" },
  { id: "bundle_json", label: "Bundle (JSON)", hint: "Documento + análise num ficheiro" },
];

export function ExportPage() {
  const { document: otmDoc, analysis } = useSession();
  const [selected, setSelected] = useState<Set<ExportFormat>>(
    () => new Set(["document_markdown", "analysis_markdown"]),
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, string> | null>(null);

  if (!otmDoc) return <Navigate to="/" replace />;
  const model = otmDoc;

  function toggle(id: ExportFormat) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function runExport() {
    setError(null);
    setResult(null);
    if (selected.size === 0) {
      setError("Escolha pelo menos um formato.");
      return;
    }
    setLoading(true);
    try {
      const needsAnalysis = [...selected].some((f) =>
        ["analysis_json", "analysis_markdown", "bundle_json"].includes(f),
      );
      const { artifacts } = await exportArtifacts({
        document: model,
        formats: [...selected],
        analysis: needsAnalysis ? analysis : null,
      });
      setResult(artifacts);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Exportação falhou.");
    } finally {
      setLoading(false);
    }
  }

  function download(name: string, content: string, mime: string) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Exportar</h1>
        <p className="mt-1 text-sm text-slate-600">
          Gera ficheiros no browser. Formatos que incluem análise usam o último resultado em sessão;
          se faltar, o servidor corre o motor automaticamente.
        </p>
      </div>

      <Card title="Formatos">
        <ul className="space-y-3">
          {FORMATS.map((f) => (
            <li key={f.id} className="flex items-start gap-3">
              <Checkbox
                id={f.id}
                checked={selected.has(f.id)}
                onChange={() => toggle(f.id)}
                className="mt-1"
              />
              <div>
                <Label htmlFor={f.id} className="!mb-0 cursor-pointer font-medium">
                  {f.label}
                </Label>
                <p className="text-xs text-slate-500">{f.hint}</p>
              </div>
            </li>
          ))}
        </ul>
        <Button className="mt-4" onClick={() => void runExport()} disabled={loading}>
          {loading ? "A gerar…" : "Gerar ficheiros"}
        </Button>
      </Card>

      {error && <Alert>{error}</Alert>}

      {result && (
        <Card title="Descarregar">
          <ul className="space-y-2">
            {Object.entries(result).map(([key, text]) => (
              <li key={key} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="font-mono text-slate-700">{key}</span>
                <Button
                  variant="secondary"
                  className="!py-1.5 !text-xs"
                  onClick={() =>
                    download(
                      `otm-export-${key}.${extFor(key)}`,
                      text,
                      mimeFor(key),
                    )
                  }
                >
                  Descarregar
                </Button>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500">
            Também pode copiar do preview técnico abaixo.
          </p>
          {Object.entries(result).map(([key, text]) => (
            <details key={`d-${key}`} className="mt-2">
              <summary className="cursor-pointer text-sm font-medium text-slate-700">
                {key}
              </summary>
              <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-slate-900 p-2 text-xs text-slate-100">
                {text.slice(0, 8000)}
                {text.length > 8000 ? "\n…" : ""}
              </pre>
            </details>
          ))}
        </Card>
      )}
    </div>
  );
}

function extFor(key: string): string {
  if (key.includes("mermaid")) return "mmd";
  if (key.includes("markdown")) return "md";
  return "json";
}

function mimeFor(key: string): string {
  if (key.includes("markdown")) return "text/markdown;charset=utf-8";
  if (key.includes("mermaid")) return "text/plain;charset=utf-8";
  return "application/json;charset=utf-8";
}
