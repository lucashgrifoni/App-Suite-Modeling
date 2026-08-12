import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
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

export function TemplatesPage() {
  const { t } = useTranslation();
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

  const categoryOptions = useMemo(
    () =>
      [
        { value: "", label: t("templates.catAll") },
        { value: "applications", label: t("templates.catApplications") },
        { value: "cloud_infra", label: t("templates.catCloud") },
        { value: "identity_access", label: t("templates.catIdentity") },
        { value: "integrations", label: t("templates.catIntegrations") },
        { value: "ai_llm", label: t("templates.catAi") },
        { value: "industry", label: t("templates.catIndustry") },
        { value: "objective", label: t("templates.catObjective") },
      ] as const,
    [t],
  );

  const complexityOptions = useMemo(
    () =>
      [
        { value: "", label: t("templates.cxAny") },
        { value: "low", label: t("templates.cxLow") },
        { value: "medium", label: t("templates.cxMedium") },
        { value: "high", label: t("templates.cxHigh") },
      ] as const,
    [t],
  );

  useEffect(() => {
    const timer = setTimeout(() => setQueryDebounced(query.trim()), 280);
    return () => clearTimeout(timer);
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
        const list = await listTemplates(
          Object.keys(params).length ? params : undefined,
        );
        if (!cancelled) {
          setItems(list);
          // Sem isto o banner de erro era só de escrita: um 5xx transitório enquanto o
          // utilizador escrevia deixava-o fixo por cima de uma página a funcionar até
          // recarregar o separador.
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : t("templates.listFail"));
          // As linhas que ficavam no ecrã respondiam à consulta ANTERIOR, mas apareciam por
          // baixo do texto de pesquisa novo, sem indicação de que estavam desactualizadas —
          // o utilizador podia escolher um template julgando que correspondia ao filtro.
          setItems([]);
        }
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
      toast.success(t("templates.toastOk"));
      navigate("/wizard");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : t("templates.toastFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader eyebrow={t("templates.eyebrow")} title={t("templates.title")} description={t("templates.description")} />

      <div className="grid max-w-4xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <Label htmlFor="tpl-search">{t("templates.search")}</Label>
          <Input
            id="tpl-search"
            placeholder={t("templates.searchPlaceholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
          />
        </div>
        <div>
          <Label htmlFor="tpl-cat">{t("templates.category")}</Label>
          <select
            id="tpl-cat"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="flex h-10 w-full rounded-otm-md border border-otm-border bg-otm-surface px-3 text-sm text-otm-text shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-otm-accent"
          >
            {categoryOptions.map((o) => (
              <option key={o.value || "all"} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="tpl-cx">{t("templates.complexity")}</Label>
          <select
            id="tpl-cx"
            value={complexity}
            onChange={(e) => setComplexity(e.target.value)}
            className="flex h-10 w-full rounded-otm-md border border-otm-border bg-otm-surface px-3 text-sm text-otm-text shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-otm-accent"
          >
            {complexityOptions.map((o) => (
              <option key={o.value || "any"} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2 lg:col-span-4">
          <Label htmlFor="tpl-tag">{t("templates.tag")}</Label>
          <Input
            id="tpl-tag"
            placeholder={t("templates.tagPlaceholder")}
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
          {items.map((item) => (
            <li key={item.id} data-testid={`tpl-row-${item.id}`}>
              <Card variant="elevated" className="otm-card-stable-hover">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-display font-semibold text-otm-text">{item.title}</span>
                      <Badge tone="neutral">{item.id}</Badge>
                      {item.complexity && (
                        <Badge tone="neutral">{t("templates.complexityBadge", { value: item.complexity })}</Badge>
                      )}
                      <Badge tone="neutral">{item.category_label}</Badge>
                      {item.suggested_pack && (
                        <Badge tone="accent">
                          {t("templates.packBadge")} {item.suggested_pack}
                        </Badge>
                      )}
                      {item.suggested_methodology && (
                        <Badge tone="neutral">{item.suggested_methodology}</Badge>
                      )}
                    </div>
                    {item.description && (
                      <p className="mt-1 text-sm text-otm-text-muted">{item.description}</p>
                    )}
                    {item.best_for && (
                      <p className="mt-1 text-xs text-otm-text-muted">
                        <span className="font-medium text-otm-text">{t("templates.idealFor")}</span> {item.best_for}
                      </p>
                    )}
                  </div>
                  <Button
                    disabled={loadingId !== null}
                    onClick={() => pick(item.id)}
                    className="shrink-0"
                  >
                    {loadingId === item.id ? t("templates.loading") : t("templates.useTemplate")}
                  </Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {!loadingList && items.length === 0 && !error && (
        <EmptyState title={t("templates.emptyResults")} description={t("templates.emptyResultsDesc")} />
      )}
    </div>
  );
}
