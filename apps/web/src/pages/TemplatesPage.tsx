import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { instantiateTemplate, listTemplates } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Input } from "../components/ui/Input";
import { Label } from "../components/ui/Label";
import { PageHeader } from "../components/patterns/PageHeader";
import { EmptyState } from "../components/patterns/EmptyState";
import { Skeleton } from "../components/patterns/Skeleton";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import type { TemplateListItem } from "../types/api";

export function TemplatesPage() {
  const navigate = useNavigate();
  const { setDocument } = useSession();
  const toast = useToast();
  const [items, setItems] = useState<TemplateListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingList(true);
      try {
        const t = await listTemplates();
        if (!cancelled) setItems(t);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof ApiError ? e.message : "Falha ao listar templates.");
      } finally {
        if (!cancelled) setLoadingList(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        t.id.toLowerCase().includes(q) ||
        (t.description?.toLowerCase().includes(q) ?? false),
    );
  }, [items, query]);

  async function pick(id: string) {
    setError(null);
    setLoadingId(id);
    try {
      const { document } = await instantiateTemplate(id);
      setDocument(document);
      toast.success("Template aplicado. A abrir o assistente.");
      navigate("/wizard");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Template inválido ou indisponível.";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Catálogo técnico"
        title="Templates"
        description="Cada opção gera um documento canónico pronto a editar no assistente."
      />

      <div className="flex max-w-md flex-col gap-2 sm:flex-row sm:items-end">
        <div className="flex-1">
          <Label htmlFor="tpl-search">Filtrar</Label>
          <Input
            id="tpl-search"
            placeholder="ID, título ou descrição…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
          />
        </div>
      </div>

      {error && <Alert>{error}</Alert>}

      {loadingList ? (
        <div className="space-y-3">
          <Skeleton className="h-28 w-full rounded-otm-xl" />
          <Skeleton className="h-28 w-full rounded-otm-xl" />
        </div>
      ) : (
        <ul className="space-y-3">
          {filtered.map((t) => (
            <li key={t.id}>
              <Card variant="elevated" className="otm-tilt-hover">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-display font-semibold text-otm-text">{t.title}</span>
                      <Badge tone="neutral">{t.id}</Badge>
                      {t.suggested_pack && (
                        <Badge tone="accent">Pack sugerido: {t.suggested_pack}</Badge>
                      )}
                    </div>
                    {t.description && (
                      <p className="mt-1 text-sm text-otm-text-muted">{t.description}</p>
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
      )}

      {!loadingList && items.length === 0 && !error && (
        <EmptyState
          title="Sem templates no servidor"
          description="Não há modelos embutidos disponíveis neste ambiente. Crie um modelo em branco ou importe um artefacto."
        />
      )}

      {!loadingList && items.length > 0 && filtered.length === 0 && (
        <EmptyState
          title="Nenhum resultado"
          description="Ajuste o filtro para encontrar templates por ID ou palavras-chave."
        />
      )}
    </div>
  );
}
