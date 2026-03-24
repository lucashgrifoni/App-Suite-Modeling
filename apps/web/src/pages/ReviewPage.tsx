import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { validateDocument } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Alert } from "../components/ui/Alert";
import { useSession } from "../context/SessionContext";

export function ReviewPage() {
  const { document } = useSession();
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
    } catch (e) {
      setMeta(null);
      setErr(e instanceof ApiError ? e.message : "Erro de validação.");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Diagrama lógico</h1>
          <p className="mt-1 text-sm text-slate-600">
            Vista em lista dos componentes e fluxos. O motor usa estes dados na análise.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => void quickValidate()}>
            Validar no servidor
          </Button>
          <Link to="/analysis">
            <Button>Correr análise</Button>
          </Link>
        </div>
      </div>

      {meta && (
        <p className="text-sm text-emerald-800" role="status">
          {meta}
        </p>
      )}
      {err && <Alert>{err}</Alert>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Componentes" subtitle={`${doc.components.length} itens`}>
          <ul className="divide-y divide-slate-100">
            {doc.components.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                <span className="font-mono text-xs text-slate-500">{c.id}</span>
                <span className="font-medium text-slate-900">{c.name}</span>
                <Badge tone="neutral">{c.kind}</Badge>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Fluxos" subtitle={`${doc.data_flows.length} ligações`}>
          <ul className="divide-y divide-slate-100">
            {doc.data_flows.map((f) => (
              <li key={f.id} className="py-2 text-sm text-slate-700">
                <span className="font-mono text-xs text-slate-500">{f.id}</span>
                <div className="mt-0.5">
                  <span className="font-medium">{f.from_component}</span>
                  <span className="mx-2 text-slate-400">→</span>
                  <span className="font-medium">{f.to_component}</span>
                  {f.name && (
                    <span className="ml-2 text-slate-500">({f.name})</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Avançado" subtitle="JSON canónico (perfil técnico).">
        <Button variant="ghost" className="mb-2 !px-0" onClick={() => setShowJson((v) => !v)}>
          {showJson ? "Ocultar JSON" : "Mostrar JSON"}
        </Button>
        {showJson && (
          <pre className="max-h-80 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
            {JSON.stringify(doc, null, 2)}
          </pre>
        )}
      </Card>
    </div>
  );
}
