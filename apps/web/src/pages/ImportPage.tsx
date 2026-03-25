import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { importArtifact } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Label } from "../components/ui/Label";
import { Select } from "../components/ui/Select";
import { useSession } from "../context/SessionContext";
import type { ArtifactImportKind, ArtifactInference, ExplanationRecord } from "../types/api";

const KINDS: { value: ArtifactImportKind; label: string; accept: string }[] = [
  { value: "openapi", label: "OpenAPI / Swagger (YAML ou JSON)", accept: ".yaml,.yml,.json" },
  { value: "terraform", label: "Terraform (.tf)", accept: ".tf" },
  { value: "kubernetes", label: "Kubernetes (YAML)", accept: ".yaml,.yml" },
];

function confidenceLabel(c: ArtifactInference["confidence"]): string {
  if (c === "high") return "Alta";
  if (c === "medium") return "Média";
  return "Baixa";
}

export function ImportPage() {
  const navigate = useNavigate();
  const { setDocument } = useSession();
  const [kind, setKind] = useState<ArtifactImportKind>("openapi");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inferences, setInferences] = useState<ArtifactInference[] | null>(null);
  const [unknowns, setUnknowns] = useState<string[] | null>(null);
  const [structuredExplanations, setStructuredExplanations] = useState<ExplanationRecord[] | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Escolha um ficheiro.");
      return;
    }
    setError(null);
    setLoading(true);
    setInferences(null);
    setUnknowns(null);
    setStructuredExplanations(null);
    try {
      const res = await importArtifact(kind, file);
      setDocument(res.document);
      setInferences(res.inferences);
      setUnknowns(res.unknowns);
      setStructuredExplanations(res.explanations ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha no envio ao servidor.");
    } finally {
      setLoading(false);
    }
  }

  const meta = KINDS.find((k) => k.value === kind);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Importar artefacto</h1>
        <p className="mt-2 max-w-xl text-slate-600">
          Gera um <strong>rascunho</strong> canónico com inferências explícitas. Não substitui revisão nem
          análise de ameaças.
        </p>
      </div>

      <Alert variant="info">
        O resultado inclui componentes e fluxos prováveis. Confira a lista de inferências antes de ir a{" "}
        <Link to="/analysis" className="font-medium text-sky-700 hover:underline">
          análise
        </Link>
        .
      </Alert>

      <Card title="Envio" subtitle="O ficheiro é processado no servidor; nada é persistido na API (MVP).">
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <Label htmlFor="kind">Tipo de artefacto</Label>
            <Select
              id="kind"
              value={kind}
              onChange={(e) => setKind(e.target.value as ArtifactImportKind)}
              className="mt-1 w-full max-w-md"
            >
              {KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="file">Ficheiro</Label>
            <input
              id="file"
              type="file"
              accept={meta?.accept}
              className="mt-1 block w-full text-sm text-slate-600 file:mr-3 file:rounded file:border file:border-slate-200 file:bg-white file:px-3 file:py-1.5 file:text-sm"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={loading}>
              {loading ? "A importar…" : "Gerar rascunho"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => navigate("/wizard")}>
              Ir para assistente
            </Button>
          </div>
        </form>
      </Card>

      {error && <Alert>{error}</Alert>}

      {inferences && inferences.length > 0 && (
        <Card title="Inferências" subtitle="Transparência — cada linha explica o raciocínio do assistente.">
          <ul className="list-inside list-disc space-y-2 text-sm text-slate-700">
            {inferences.map((i) => (
              <li key={i.id}>
                <span className="text-slate-500">[{confidenceLabel(i.confidence)}]</span> {i.message}
              </li>
            ))}
          </ul>
          {structuredExplanations && structuredExplanations.length > 0 ? (
            <details className="mt-4 rounded border border-slate-100 bg-slate-50 p-3 text-xs text-slate-700">
              <summary className="cursor-pointer font-medium text-slate-900">Mesmo conteúdo (contrato JSON)</summary>
              <p className="mt-2 text-slate-600">
                Útil para relatórios e API: campo <code className="rounded bg-white px-1">explanations</code>{" "}
                espelha as inferências com tipo e categoria.
              </p>
            </details>
          ) : null}
        </Card>
      )}

      {unknowns && unknowns.length > 0 && (
        <Card title="Não inferido" subtitle="Limitações explícitas deste lote.">
          <ul className="list-inside list-disc space-y-1 text-sm text-amber-900">
            {unknowns.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
