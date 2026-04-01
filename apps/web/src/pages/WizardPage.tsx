import { useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { validateDocument } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Label } from "../components/ui/Label";
import { Select } from "../components/ui/Select";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/patterns/PageHeader";
import { WorkflowGuide } from "../components/onboarding/WorkflowGuide";
import { HelpCallout } from "../components/onboarding/HelpCallout";
import { Stepper } from "../components/patterns/Stepper";
import { Panel } from "../components/patterns/Panel";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import { removeArrayItem, updateArrayItem } from "../utils/collections";
import {
  COMPONENT_KINDS,
  SYSTEM_TYPES,
  type OtmComponent,
  type OtmDataFlow,
} from "../types/document";

const STEPS = [
  { id: 0, label: "Contexto" },
  { id: 1, label: "Componentes" },
  { id: 2, label: "Fluxos" },
  { id: 3, label: "Concluir" },
] as const;

export function WizardPage() {
  const { document, setDocument } = useSession();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);

  const componentIds = useMemo(
    () => document?.components.map((c) => c.id).filter(Boolean) ?? [],
    [document?.components],
  );

  if (!document) return <Navigate to="/" replace />;
  const doc = document;

  function updateMetadata(partial: Partial<typeof doc.metadata>) {
    setDocument({
      ...doc,
      metadata: { ...doc.metadata, ...partial },
    });
  }

  function updateModel(partial: Partial<typeof doc.model>) {
    setDocument({
      ...doc,
      model: { ...doc.model, ...partial },
    });
  }

  function setComponents(components: OtmComponent[]) {
    setDocument({ ...doc, components });
  }

  function setFlows(flows: OtmDataFlow[]) {
    setDocument({ ...doc, data_flows: flows });
  }

  async function validateAndNext() {
    setError(null);
    setValidating(true);
    try {
      await validateDocument(doc);
      setStep((s) => Math.min(s + 1, STEPS.length - 1));
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : "O modelo não passou na validação. Corrija os campos obrigatórios.";
      setError(msg);
      toast.error(msg);
    } finally {
      setValidating(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Assistente guiado"
        title="Assistente"
        description={
          <>
            Quatro passos curtos. Os IDs devem ser únicos (letras, números,{" "}
            <code className="rounded bg-otm-surface-3 px-1 text-xs text-otm-accent">_</code> e{" "}
            <code className="rounded bg-otm-surface-3 px-1 text-xs text-otm-accent">-</code>).
          </>
        }
      />

      <div className="space-y-3">
        <WorkflowGuide variant="compact" />
        <HelpCallout title="Próximo passo natural" tone="tip">
          Conclua os passos e valide — depois abra o <strong className="text-otm-text">diagrama</strong> e a{" "}
          <strong className="text-otm-text">análise</strong> quando o modelo estiver coerente.
        </HelpCallout>
      </div>

      <Panel>
        <Stepper
          steps={STEPS}
          currentIndex={step}
          onStepClick={(i) => {
            if (i <= step) setStep(STEPS[i].id);
          }}
        />
      </Panel>

      {error && <Alert>{error}</Alert>}

      {step === 0 && (
        <Card title="Contexto do sistema" variant="glass">
          <div className="space-y-4">
            <div>
              <Label htmlFor="title">Título do modelo</Label>
              <Input
                id="title"
                value={doc.metadata.title}
                onChange={(e) => updateMetadata({ title: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="summary">Resumo (opcional)</Label>
              <Input
                id="summary"
                value={doc.metadata.summary ?? ""}
                onChange={(e) => updateMetadata({ summary: e.target.value || null })}
              />
            </div>
            <div>
              <Label htmlFor="stype">Tipo de sistema</Label>
              <Select
                id="stype"
                value={doc.model.system_type}
                onChange={(e) => updateModel({ system_type: e.target.value })}
              >
                {SYSTEM_TYPES.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </Card>
      )}

      {step === 1 && (
        <Card
          title="Componentes"
          subtitle="Elementos do diagrama (processos, dados, utilizadores…)."
          variant="glass"
        >
          <div className="space-y-3">
            {doc.components.map((c, idx) => (
              <div
                key={`comp-${c.id}-${c.name}`}
                className="grid gap-2 rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 sm:grid-cols-12 sm:items-end"
              >
                <div className="sm:col-span-3">
                  <Label htmlFor={`comp-${idx}-id`}>ID</Label>
                  <Input
                    id={`comp-${idx}-id`}
                    value={c.id}
                    onChange={(e) => {
                      setComponents(updateArrayItem(doc.components, idx, { ...c, id: e.target.value }));
                    }}
                  />
                </div>
                <div className="sm:col-span-4">
                  <Label htmlFor={`comp-${idx}-name`}>Nome</Label>
                  <Input
                    id={`comp-${idx}-name`}
                    value={c.name}
                    onChange={(e) => {
                      setComponents(updateArrayItem(doc.components, idx, { ...c, name: e.target.value }));
                    }}
                  />
                </div>
                <div className="sm:col-span-3">
                  <Label htmlFor={`comp-${idx}-kind`}>Tipo</Label>
                  <Select
                    id={`comp-${idx}-kind`}
                    value={c.kind}
                    onChange={(e) => {
                      setComponents(updateArrayItem(doc.components, idx, { ...c, kind: e.target.value }));
                    }}
                  >
                    {COMPONENT_KINDS.map((k) => (
                      <option key={k.value} value={k.value}>
                        {k.label}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="sm:col-span-2">
                  <Button
                    variant="ghost"
                    className="w-full text-red-300"
                    onClick={() => setComponents(removeArrayItem(doc.components, idx))}
                  >
                    Remover
                  </Button>
                </div>
              </div>
            ))}
            <Button
              variant="secondary"
              onClick={() =>
                setComponents([
                  ...doc.components,
                  { id: `comp_${doc.components.length + 1}`, name: "Novo", kind: "process" },
                ])
              }
            >
              Adicionar componente
            </Button>
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card
          title="Fluxos de dados"
          subtitle="Ligações entre componentes (origem e destino = IDs dos componentes)."
          variant="glass"
        >
          <div className="space-y-3">
            {doc.data_flows.map((f, idx) => (
              <div
                key={`flow-${f.id}-${f.from_component}-${f.to_component}`}
                className="grid gap-2 rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 sm:grid-cols-12 sm:items-end"
              >
                <div className="sm:col-span-2">
                  <Label htmlFor={`flow-${idx}-id`}>ID fluxo</Label>
                  <Input
                    id={`flow-${idx}-id`}
                    value={f.id}
                    onChange={(e) => {
                      setFlows(updateArrayItem(doc.data_flows, idx, { ...f, id: e.target.value }));
                    }}
                  />
                </div>
                <div className="sm:col-span-3">
                  <Label htmlFor={`flow-${idx}-from`}>De</Label>
                  <Select
                    id={`flow-${idx}-from`}
                    value={f.from_component}
                    onChange={(e) => {
                      setFlows(
                        updateArrayItem(doc.data_flows, idx, { ...f, from_component: e.target.value }),
                      );
                    }}
                  >
                    <option value="">—</option>
                    {componentIds.map((id) => (
                      <option key={id} value={id}>
                        {id}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="sm:col-span-3">
                  <Label htmlFor={`flow-${idx}-to`}>Para</Label>
                  <Select
                    id={`flow-${idx}-to`}
                    value={f.to_component}
                    onChange={(e) => {
                      setFlows(
                        updateArrayItem(doc.data_flows, idx, { ...f, to_component: e.target.value }),
                      );
                    }}
                  >
                    <option value="">—</option>
                    {componentIds.map((id) => (
                      <option key={id} value={id}>
                        {id}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="sm:col-span-2">
                  <Label htmlFor={`flow-${idx}-name`}>Nome (opcional)</Label>
                  <Input
                    id={`flow-${idx}-name`}
                    value={f.name ?? ""}
                    onChange={(e) => {
                      setFlows(updateArrayItem(doc.data_flows, idx, { ...f, name: e.target.value || null }));
                    }}
                  />
                </div>
                <div className="sm:col-span-2">
                  <Button
                    variant="ghost"
                    className="w-full text-red-300"
                    onClick={() => setFlows(removeArrayItem(doc.data_flows, idx))}
                  >
                    Remover
                  </Button>
                </div>
              </div>
            ))}
            <Button
              variant="secondary"
              onClick={() =>
                setFlows([
                  ...doc.data_flows,
                  {
                    id: `flow_${doc.data_flows.length + 1}`,
                    from_component: componentIds[0] ?? "",
                    to_component: componentIds[1] ?? componentIds[0] ?? "",
                    name: null,
                  },
                ])
              }
            >
              Adicionar fluxo
            </Button>
          </div>
        </Card>
      )}

      {step === 3 && (
        <Card title="Pronto para rever" variant="elevated">
          <p className="text-sm text-otm-text-muted">
            Valide no servidor e avance para a vista de componentes e fluxos. Pode voltar a qualquer
            passo para ajustar.
          </p>
          <ul className="mt-3 list-inside list-disc text-sm text-otm-text-muted">
            <li>{doc.components.length} componentes</li>
            <li>{doc.data_flows.length} fluxos</li>
          </ul>
        </Card>
      )}

      <div className="flex flex-wrap gap-2">
        {step > 0 && (
          <Button variant="secondary" onClick={() => setStep((s) => s - 1)}>
            Anterior
          </Button>
        )}
        {step < STEPS.length - 1 && (
          <Button onClick={() => void validateAndNext()} disabled={validating}>
            {validating ? "A validar…" : "Seguinte"}
          </Button>
        )}
        {step === STEPS.length - 1 && (
          <Link to="/review">
            <Button>Ver diagrama lógico</Button>
          </Link>
        )}
      </div>
    </div>
  );
}
