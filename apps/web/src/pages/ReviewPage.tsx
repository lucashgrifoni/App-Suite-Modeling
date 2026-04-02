import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { validateDocument } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Alert } from "../components/ui/Alert";
import { Checkbox } from "../components/ui/Checkbox";
import { Input } from "../components/ui/Input";
import { Label } from "../components/ui/Label";
import { PageHeader } from "../components/patterns/PageHeader";
import { ThreatModelDiagram } from "../components/diagram/ThreatModelDiagram";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import { updateArrayItem } from "../utils/collections";
import type { OtmAsset, OtmTrustBoundary } from "../types/document";

export function ReviewPage() {
  const { document, setDocument } = useSession();
  const toast = useToast();
  const [showJson, setShowJson] = useState(false);
  const [meta, setMeta] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  if (!document) return <Navigate to="/" replace />;
  const doc = document;

  function updateTrustBoundary(index: number, partial: Partial<OtmTrustBoundary>) {
    const cur = doc.trust_boundaries[index];
    if (!cur) return;
    setDocument({
      ...doc,
      trust_boundaries: updateArrayItem(doc.trust_boundaries, index, { ...cur, ...partial }),
    });
  }

  function updateAsset(index: number, partial: Partial<OtmAsset>) {
    const cur = doc.assets[index];
    if (!cur) return;
    setDocument({
      ...doc,
      assets: updateArrayItem(doc.assets, index, { ...cur, ...partial }),
    });
  }

  async function quickValidate() {
    setErr(null);
    try {
      const v = await validateDocument(doc);
      setMeta(
        `Válido · schema ${v.schema_version} · ${v.component_count} componentes · ${v.threat_count} ameaças no documento`,
      );
      toast.success("Documento válido no servidor.");
    } catch (e) {
      setMeta(null);
      const msg = e instanceof ApiError ? e.message : "Erro de validação.";
      setErr(msg);
      toast.error(msg);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Revisão estrutural"
        title="Diagrama lógico"
        description="Editor visual (React Flow) com edição activa por omissão: arraste nós, ligue componentes e use Delete. «Visualizar» desativa alterações estruturais. A lista abaixo reflecte o modelo em sessão."
        actions={
          <>
            <Button variant="secondary" onClick={() => void quickValidate()}>
              Validar no servidor
            </Button>
            <Link to="/analysis">
              <Button>Correr análise</Button>
            </Link>
          </>
        }
      />

      {meta && <Alert variant="success">{meta}</Alert>}
      {err && <Alert>{err}</Alert>}

      <Card
        title="Diagrama interativo"
        subtitle="Por omissão: Editar (arrastar, ligar, apagar, rótulos). Botão «Visualizar» = só leitura."
        variant="glass"
      >
        <ThreatModelDiagram document={doc} setDocument={setDocument} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Componentes" subtitle={`${doc.components.length} itens`} variant="glass">
          <ul className="divide-y divide-otm-border">
            {doc.components.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                <span className="font-mono text-xs text-otm-text-subtle">{c.id}</span>
                <span className="font-medium text-otm-text">{c.name}</span>
                <Badge tone="neutral">{c.kind}</Badge>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Fluxos" subtitle={`${doc.data_flows.length} ligações`} variant="glass">
          <ul className="divide-y divide-otm-border">
            {doc.data_flows.map((f) => (
              <li key={f.id} className="py-2 text-sm text-otm-text-muted">
                <span className="font-mono text-xs text-otm-text-subtle">{f.id}</span>
                <div className="mt-0.5">
                  <span className="font-medium text-otm-text">{f.from_component}</span>
                  <span className="mx-2 text-otm-text-subtle">→</span>
                  <span className="font-medium text-otm-text">{f.to_component}</span>
                  {f.name && (
                    <span className="ml-2 text-otm-text-subtle">({f.name})</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {doc.trust_boundaries.length > 0 ? (
        <Card
          title="Trust boundaries"
          subtitle="Notas de inferência, fluxos que cruzam e validação manual (sem editar JSON)."
          variant="glass"
        >
          <ul className="divide-y divide-otm-border">
            {doc.trust_boundaries.map((b, idx) => (
              <li key={b.id} className="space-y-2 py-4 first:pt-0">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-mono text-xs text-otm-text-subtle">{b.id}</span>
                  <span className="font-medium text-otm-text">{b.name}</span>
                </div>
                {b.inference_note ? (
                  <p className="text-xs text-otm-text-muted">
                    <span className="font-semibold text-otm-text-subtle">Porquê: </span>
                    {b.inference_note}
                  </p>
                ) : null}
                {(b.crossing_flow_ids?.length ?? 0) > 0 ? (
                  <p className="text-xs text-otm-text-muted">
                    <span className="font-semibold text-otm-text-subtle">Fluxos cruzando: </span>
                    {(b.crossing_flow_ids ?? []).join(", ")}
                  </p>
                ) : null}
                <div className="grid gap-2 sm:grid-cols-2">
                  <div>
                    <Label htmlFor={`inf-${b.id}`}>Nota / override</Label>
                    <Input
                      id={`inf-${b.id}`}
                      className="mt-1 text-sm"
                      value={b.inference_note ?? ""}
                      onChange={(e) => updateTrustBoundary(idx, { inference_note: e.target.value || null })}
                      placeholder="Ex.: confirmar segmentação DMZ"
                    />
                  </div>
                  <label className="flex cursor-pointer items-center gap-2 pt-6 text-sm text-otm-text-muted">
                    <Checkbox
                      checked={b.user_validated === true}
                      onChange={(e) => updateTrustBoundary(idx, { user_validated: e.target.checked })}
                    />
                    Validada pelo modelador
                  </label>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {doc.assets.length > 0 ? (
        <Card title="Ativos" subtitle="Criticidade e ligações a componentes/fluxos." variant="glass">
          <ul className="divide-y divide-otm-border">
            {doc.assets.map((a, idx) => {
              return (
                <li key={a.id} className="space-y-2 py-4 first:pt-0">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="font-mono text-xs text-otm-text-subtle">{a.id}</span>
                    <span className="font-medium text-otm-text">{a.name}</span>
                    {a.asset_kind ? <Badge tone="neutral">{a.asset_kind}</Badge> : null}
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div>
                      <Label htmlFor={`bc-${a.id}`}>Criticidade</Label>
                      <Input
                        id={`bc-${a.id}`}
                        className="mt-1 text-sm"
                        value={a.business_criticality ?? ""}
                        onChange={(e) => updateAsset(idx, { business_criticality: e.target.value || undefined })}
                        placeholder="ex.: high"
                      />
                    </div>
                    <div>
                      <Label htmlFor={`cl-${a.id}`}>Classificação</Label>
                      <Input
                        id={`cl-${a.id}`}
                        className="mt-1 text-sm"
                        value={a.data_classification ?? a.sensitivity ?? ""}
                        onChange={(e) =>
                          updateAsset(idx, {
                            data_classification: e.target.value || undefined,
                            sensitivity: e.target.value || undefined,
                          })
                        }
                        placeholder="ex.: confidential"
                      />
                    </div>
                  </div>
                  {(a.related_component_ids?.length ?? 0) > 0 ||
                  (a.related_data_flow_ids?.length ?? 0) > 0 ? (
                    <p className="text-xs text-otm-text-muted">
                      {(a.related_component_ids?.length ?? 0) > 0 ? (
                        <>
                          <span className="font-semibold text-otm-text-subtle">Componentes: </span>
                          {(a.related_component_ids ?? []).join(", ")}
                        </>
                      ) : null}
                      {(a.related_data_flow_ids?.length ?? 0) > 0 ? (
                        <>
                          {" "}
                          <span className="font-semibold text-otm-text-subtle">Fluxos: </span>
                          {(a.related_data_flow_ids ?? []).join(", ")}
                        </>
                      ) : null}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </Card>
      ) : null}

      <Card title="Avançado" subtitle="JSON canónico (perfil técnico)." variant="elevated">
        <Button variant="ghost" className="mb-2 !px-0" onClick={() => setShowJson((v) => !v)}>
          {showJson ? "Ocultar JSON" : "Mostrar JSON"}
        </Button>
        {showJson && (
          <pre className="max-h-80 overflow-auto rounded-otm-md bg-otm-green-950 p-3 text-xs text-otm-mint-300">
            {JSON.stringify(doc, null, 2)}
          </pre>
        )}
      </Card>
    </div>
  );
}
