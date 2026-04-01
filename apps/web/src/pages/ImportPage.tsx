import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { importArtifact } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Label } from "../components/ui/Label";
import { Select } from "../components/ui/Select";
import { PageHeader } from "../components/patterns/PageHeader";
import { FileDropZone } from "../components/patterns/FileDropZone";
import { WorkflowGuide } from "../components/onboarding/WorkflowGuide";
import { ContextHint } from "../components/onboarding/ContextHint";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
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
  const toast = useToast();
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
      const msg = "Escolha um ficheiro.";
      setError(msg);
      toast.warning(msg);
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
      toast.success("Rascunho importado. Revise inferências antes da análise.");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Falha no envio ao servidor.";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  const meta = KINDS.find((k) => k.value === kind);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Ingestão segura"
        title="Importar artefacto"
        description={
          <>
            Gera um <strong className="text-otm-text">rascunho</strong> canónico com inferências explícitas. Não
            substitui revisão nem análise de ameaças.
          </>
        }
      />

      <div className="space-y-2 rounded-otm-lg border border-otm-border/80 bg-otm-surface-1/50 px-4 py-3">
        <WorkflowGuide variant="compact" />
        <ContextHint>
          Depois do rascunho, use o <strong>assistente</strong> para ajustar IDs e fluxos antes do motor.
        </ContextHint>
      </div>

      <Alert variant="info">
        O resultado inclui componentes e fluxos prováveis. Confira a lista de inferências antes de ir a{" "}
        <Link to="/analysis" className="font-medium text-otm-accent underline-offset-4 hover:underline">
          análise
        </Link>
        .
      </Alert>

      <Card title="Envio" subtitle="O ficheiro é processado no servidor; nada é persistido na API (MVP)." variant="glass">
        <form onSubmit={onSubmit} className="space-y-4" aria-busy={loading}>
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

          <FileDropZone
            disabled={loading}
            onFile={(f) => setFile(f)}
            description={`Tipos aceites: ${meta?.accept ?? "—"}`}
          >
            <div className="mt-4">
              <Label htmlFor="file" className="sr-only">
                Ficheiro
              </Label>
              <input
                id="file"
                type="file"
                accept={meta?.accept}
                className="mx-auto block w-full max-w-sm text-sm text-otm-text-muted file:mr-3 file:rounded-otm-md file:border file:border-otm-border file:bg-otm-surface-2 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-otm-text"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              {file ? (
                <p className="mt-2 text-xs text-otm-accent">
                  Selecionado: <span className="font-mono">{file.name}</span>
                </p>
              ) : null}
            </div>
          </FileDropZone>

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
        <Card title="Inferências" subtitle="Transparência — cada linha explica o raciocínio do assistente." variant="elevated">
          <ul className="list-inside list-disc space-y-2 text-sm text-otm-text-muted">
            {inferences.map((i) => (
              <li key={i.id}>
                <span className="text-otm-text-subtle">[{confidenceLabel(i.confidence)}]</span> {i.message}
              </li>
            ))}
          </ul>
          {structuredExplanations && structuredExplanations.length > 0 ? (
            <details className="mt-4 rounded-otm-md border border-otm-border bg-otm-surface-1 p-3 text-xs text-otm-text-muted">
              <summary className="cursor-pointer font-medium text-otm-text">Mesmo conteúdo (contrato JSON)</summary>
              <p className="mt-2">
                Útil para relatórios e API: campo <code className="rounded bg-otm-surface-3 px-1 text-otm-accent">explanations</code>{" "}
                espelha as inferências com tipo e categoria.
              </p>
            </details>
          ) : null}
        </Card>
      )}

      {unknowns && unknowns.length > 0 && (
        <Card title="Não inferido" subtitle="Limitações explícitas deste lote." variant="glass">
          <ul className="list-inside list-disc space-y-1 text-sm text-amber-100">
            {unknowns.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
