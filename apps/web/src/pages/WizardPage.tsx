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
import { useSession } from "../context/SessionContext";
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
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);

  if (!document) return <Navigate to="/" replace />;
  const doc = document;

  const componentIds = useMemo(
    () => doc.components.map((c) => c.id).filter(Boolean),
    [doc.components],
  );

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
      setError(
        e instanceof ApiError
          ? e.message
          : "O modelo não passou na validação. Corrija os campos obrigatórios.",
      );
    } finally {
      setValidating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Assistente</h1>
        <p className="mt-1 text-sm text-slate-600">
          Quatro passos curtos. Os IDs devem ser únicos (letras, números, <code className="text-xs">_</code>{" "}
          e <code className="text-xs">-</code>).
        </p>
      </div>

      <ol className="flex flex-wrap gap-2">
        {STEPS.map((s, i) => (
          <li key={s.id}>
            <button
              type="button"
              onClick={() => (i <= step ? setStep(s.id) : undefined)}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                s.id === step
                  ? "bg-slate-900 text-white"
                  : i < step
                    ? "bg-slate-200 text-slate-800"
                    : "bg-slate-100 text-slate-400"
              }`}
            >
              {i + 1}. {s.label}
            </button>
          </li>
        ))}
      </ol>

      {error && <Alert>{error}</Alert>}

      {step === 0 && (
        <Card title="Contexto do sistema">
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
        <Card title="Componentes" subtitle="Elementos do diagrama (processos, dados, utilizadores…).">
          <div className="space-y-3">
            {doc.components.map((c, idx) => (
              <div
                key={idx}
                className="grid gap-2 rounded-lg border border-slate-100 p-3 sm:grid-cols-12 sm:items-end"
              >
                <div className="sm:col-span-3">
                  <Label>ID</Label>
                  <Input
                    value={c.id}
                    onChange={(e) => {
                      const next = [...doc.components];
                      next[idx] = { ...c, id: e.target.value };
                      setComponents(next);
                    }}
                  />
                </div>
                <div className="sm:col-span-4">
                  <Label>Nome</Label>
                  <Input
                    value={c.name}
                    onChange={(e) => {
                      const next = [...doc.components];
                      next[idx] = { ...c, name: e.target.value };
                      setComponents(next);
                    }}
                  />
                </div>
                <div className="sm:col-span-3">
                  <Label>Tipo</Label>
                  <Select
                    value={c.kind}
                    onChange={(e) => {
                      const next = [...doc.components];
                      next[idx] = { ...c, kind: e.target.value };
                      setComponents(next);
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
                    className="w-full text-red-600"
                    onClick={() =>
                      setComponents(doc.components.filter((_, j) => j !== idx))
                    }
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
        >
          <div className="space-y-3">
            {doc.data_flows.map((f, idx) => (
              <div
                key={idx}
                className="grid gap-2 rounded-lg border border-slate-100 p-3 sm:grid-cols-12 sm:items-end"
              >
                <div className="sm:col-span-2">
                  <Label>ID fluxo</Label>
                  <Input
                    value={f.id}
                    onChange={(e) => {
                      const next = [...doc.data_flows];
                      next[idx] = { ...f, id: e.target.value };
                      setFlows(next);
                    }}
                  />
                </div>
                <div className="sm:col-span-3">
                  <Label>De</Label>
                  <Select
                    value={f.from_component}
                    onChange={(e) => {
                      const next = [...doc.data_flows];
                      next[idx] = { ...f, from_component: e.target.value };
                      setFlows(next);
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
                  <Label>Para</Label>
                  <Select
                    value={f.to_component}
                    onChange={(e) => {
                      const next = [...doc.data_flows];
                      next[idx] = { ...f, to_component: e.target.value };
                      setFlows(next);
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
                  <Label>Nome (opcional)</Label>
                  <Input
                    value={f.name ?? ""}
                    onChange={(e) => {
                      const next = [...doc.data_flows];
                      next[idx] = { ...f, name: e.target.value || null };
                      setFlows(next);
                    }}
                  />
                </div>
                <div className="sm:col-span-2">
                  <Button
                    variant="ghost"
                    className="w-full text-red-600"
                    onClick={() =>
                      setFlows(doc.data_flows.filter((_, j) => j !== idx))
                    }
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
        <Card title="Pronto para rever">
          <p className="text-sm text-slate-600">
            Valide no servidor e avance para a vista de componentes e fluxos. Pode voltar a qualquer
            passo para ajustar.
          </p>
          <ul className="mt-3 list-inside list-disc text-sm text-slate-600">
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
