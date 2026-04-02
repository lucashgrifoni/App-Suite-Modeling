import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { instantiateTemplate, listTemplates } from "../api/otmApi";
import type { TemplateListQuery } from "../api/otmApi";
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

const CATEGORY_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Todas as categorias" },
  { value: "applications", label: "Applications" },
  { value: "cloud_infra", label: "Cloud & Infra" },
  { value: "identity_access", label: "Identity & Access" },
  { value: "integrations", label: "Integrations" },
  { value: "ai_llm", label: "AI & LLM" },
  { value: "industry", label: "Industry" },
  { value: "objective", label: "Objective-based" },
];

const COMPLEXITY_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Qualquer complexidade" },
  { value: "low", label: "Baixa" },
  { value: "medium", label: "Média" },
  { value: "high", label: "Alta" },
];

export function TemplatesPage() {
  const navigate = useNavigate();
  const { setDocument } = useSession();
  const toast = useToast();
  const [items, setItems] = useState<TemplateListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [query, setQuery] = useState("");
  const [queryDebounced, setQueryDebounced] = useState("");
  const [category, setCategory] = useState("");
  const [complexity, setComplexity] = useState("");
  const [tag, setTag] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setQueryDebounced(query.trim()), 280);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingList(true);
      const params: TemplateListQuery = {};
      if (category) params.category = category;
      if (complexity) params.complexity = complexity;
      if (tag.trim()) params.tag = tag.trim();
      if (queryDebounced) params.q = queryDebounced;
      try {
        const t = await listTemplates(
          Object.keys(params).length ? params : undefined,
        );
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
  }, [category, complexity, tag, queryDebounced]);

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
        description="Cada opção gera um documento canónico pronto a editar no assistente. Use filtros para reduzir a lista sem perder contexto."
      />

      <div className="grid max-w-4xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <Label htmlFor="tpl-search">Texto</Label>
          <Input
            id="tpl-search"
            placeholder="ID, título, descrição, tags…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
          />
        </div>
        <div>
          <Label htmlFor="tpl-cat">Categoria</Label>
          <select
            id="tpl-cat"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="flex h-10 w-full rounded-otm-md border border-otm-border bg-otm-surface px-3 text-sm text-otm-text shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-otm-accent"
          >
            {CATEGORY_OPTIONS.map((o) => (
              <option key={o.value || "all"} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="tpl-cx">Complexidade</Label>
          <select
            id="tpl-cx"
            value={complexity}
            onChange={(e) => setComplexity(e.target.value)}
            className="flex h-10 w-full rounded-otm-md border border-otm-border bg-otm-surface px-3 text-sm text-otm-text shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-otm-accent"
          >
            {COMPLEXITY_OPTIONS.map((o) => (
              <option key={o.value || "any"} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2 lg:col-span-4">
          <Label htmlFor="tpl-tag">Tag (exacta)</Label>
          <Input
            id="tpl-tag"
            placeholder="ex.: llm, api, finance…"
            value={tag}
            onChange={(e) => setTag(e.target.value)}
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
          {items.map((t) => (
            <li key={t.id}>
              <Card variant="elevated" className="otm-card-stable-hover">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-display font-semibold text-otm-text">{t.title}</span>
                      <Badge tone="neutral">{t.id}</Badge>
                      {t.complexity && (
                        <Badge tone="neutral">Complexidade: {t.complexity}</Badge>
                      )}
                      <Badge tone="neutral">{t.category_label}</Badge>
                      {t.suggested_pack && (
                        <Badge tone="accent">Pack: {t.suggested_pack}</Badge>
                      )}
                      {t.suggested_methodology && (
                        <Badge tone="neutral">{t.suggested_methodology}</Badge>
                      )}
                    </div>
                    {t.description && (
                      <p className="mt-1 text-sm text-otm-text-muted">{t.description}</p>
                    )}
                    {t.best_for && (
                      <p className="mt-1 text-xs text-otm-text-muted">
                        <span className="font-medium text-otm-text">Ideal para:</span> {t.best_for}
                      </p>
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
          title="Sem resultados"
          description="Ajuste o filtro ou o texto de pesquisa. Os templates são pontos de partida — não substituem modelagem completa."
        />
      )}
    </div>
  );
}
