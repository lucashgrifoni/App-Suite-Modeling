import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { instantiateTemplate, listTemplates } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { useSession } from "../context/SessionContext";
import type { TemplateListItem } from "../types/api";

export function TemplatesPage() {
  const navigate = useNavigate();
  const { setDocument } = useSession();
  const [items, setItems] = useState<TemplateListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const t = await listTemplates();
        if (!cancelled) setItems(t);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof ApiError ? e.message : "Falha ao listar templates.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function pick(id: string) {
    setError(null);
    setLoadingId(id);
    try {
      const { document } = await instantiateTemplate(id);
      setDocument(document);
      navigate("/wizard");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Template inválido ou indisponível.");
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Templates</h1>
        <p className="mt-1 text-sm text-slate-600">
          Cada opção gera um documento canónico pronto a editar no assistente.
        </p>
      </div>
      {error && <Alert>{error}</Alert>}
      <ul className="space-y-3">
        {items.map((t) => (
          <li key={t.id}>
            <Card>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-900">{t.title}</span>
                    <Badge tone="neutral">{t.id}</Badge>
                    {t.suggested_pack && (
                      <Badge tone="accent">Pack sugerido: {t.suggested_pack}</Badge>
                    )}
                  </div>
                  {t.description && (
                    <p className="mt-1 text-sm text-slate-600">{t.description}</p>
                  )}
                </div>
                <Button
                  disabled={loadingId !== null}
                  onClick={() => pick(t.id)}
                  className="shrink-0"
                >
                  {loadingId === t.id ? "A carregar…" : "Usar este template"}
                </Button>
              </div>
            </Card>
          </li>
        ))}
      </ul>
      {items.length === 0 && !error && (
        <p className="text-sm text-slate-500">Nenhum template embutido no servidor.</p>
      )}
    </div>
  );
}
