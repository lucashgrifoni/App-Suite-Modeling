import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { validateDocument } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/patterns/PageHeader";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";

export function ReviewPage() {
  const { document } = useSession();
  const toast = useToast();
  const [showJson, setShowJson] = useState(false);
  const [meta, setMeta] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  if (!document) return <Navigate to="/" replace />;
  const doc = document;

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
        description="Vista em lista dos componentes e fluxos. O motor usa estes dados na análise."
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
