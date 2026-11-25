import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { instantiateTemplate, listTemplates } from "../api/otmApi";
import type { TemplateListQuery } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
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
import { useConfirmReplaceModel } from "../hooks/useConfirmReplaceModel";
import { clearWizardStep } from "../utils/wizardStepStorage";
import type { TemplateListItem } from "../types/api";

export function TemplatesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { setDocument } = useSession();
  const toast = useToast();
  const confirmReplaceModel = useConfirmReplaceModel();
  const [items, setItems] = useState<TemplateListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [query, setQuery] = useState("");
  const [queryDebounced, setQueryDebounced] = useState("");
  const [category, setCategory] = useState("");
  const [complexity, setComplexity] = useState("");
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState("");
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
          setPage(0);
          setSelectedId("");
          // Sem isto o banner de erro era só de escrita: um 5xx transitório enquanto o
          // utilizador escrevia deixava-o fixo por cima de uma página a funcionar até
          // recarregar o separador.
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(apiErrorMessage(e, t, "templates.listFail"));
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
    if (!confirmReplaceModel()) return;
    setError(null);
    setLoadingId(id);
    try {
      const { document } = await instantiateTemplate(id);
      setDocument(document);
      // A template the user has never seen opens at step 1, not wherever the previous
      // model was left. See utils/wizardStepStorage.
      clearWizardStep();
      toast.success(t("templates.toastOk"));
      navigate("/wizard");
    } catch (e) {
      const msg = apiErrorMessage(e, t, "templates.toastFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setLoadingId(null);
    }
  }

  const lastPage = Math.max(0, Math.ceil(items.length / 8) - 1);
  const rows = items.slice(page * 8, page * 8 + 8);
  const selected = rows.find((item) => item.id === selectedId) ?? rows[0];

  return (
    <div className="work-page">
      <PageHeader
        eyebrow={t("templates.eyebrow")}
        title={t("templates.title")}
        description={t("templates.description")}
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
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
            className="flex h-10 w-full rounded-otm-md border border-otm-border bg-[color:Field] px-3 text-sm text-otm-text shadow-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-otm-accent"
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
            className="flex h-10 w-full rounded-otm-md border border-otm-border bg-[color:Field] px-3 text-sm text-otm-text shadow-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-otm-accent"
          >
            {complexityOptions.map((o) => (
              <option key={o.value || "any"} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div className="lg:col-span-1">
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
        selected && (
          <div className="work-split">
            <Card title={t("work.catalog")} subtitle={t("work.templateCount", { count: items.length })}>
              <div className="work-list-head grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)_auto]">
                <span>{t("quickStart.templateTitle")}</span>
                <span>{t("templates.category")}</span>
                <span>{t("templates.complexity")}</span>
              </div>
              <ul>
                {rows.map((item) => (
                  <li data-testid={`tpl-row-${item.id}`} key={item.id}>
                    <button
                      type="button"
                      className="work-select-row grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)_auto]"
                      aria-pressed={selected.id === item.id}
                      onClick={() => setSelectedId(item.id)}
                    >
                      <span>
                        <b>{item.title}</b>
                        <small>{item.id}</small>
                      </span>
                      <span>
                        {categoryOptions.find((option) => option.value === item.category)?.label ??
                          item.category_label}
                      </span>
                      <small>
                        {complexityOptions.find((option) => option.value === item.complexity)?.label ??
                          item.complexity}
                      </small>
                    </button>
                  </li>
                ))}
              </ul>
              {lastPage > 0 && (
                <div className="work-pager">
                  <button type="button" disabled={page === 0} onClick={() => setPage(page - 1)}>
                    {t("work.previous")}
                  </button>
                  {page + 1} / {lastPage + 1}
                  <button type="button" disabled={page >= lastPage} onClick={() => setPage(page + 1)}>
                    {t("work.next")}
                  </button>
                </div>
              )}
            </Card>
            <Card title={selected.title} subtitle={selected.best_for ?? undefined}>
              <p className="work-muted">{selected.description}</p>
              <div className="my-3 flex flex-wrap gap-2">
                <Badge tone="neutral">
                  {categoryOptions.find((option) => option.value === selected.category)?.label ??
                    selected.category_label}
                </Badge>
                {selected.suggested_pack && (
                  <Badge tone="accent">
                    {t("templates.packBadge")} {selected.suggested_pack}
                  </Badge>
                )}
                {selected.suggested_methodology && <Badge>{selected.suggested_methodology}</Badge>}
              </div>
              <Button disabled={loadingId !== null} onClick={() => void pick(selected.id)}>
                {t(loadingId === selected.id ? "templates.loading" : "templates.useTemplate")}
              </Button>
            </Card>
          </div>
        )
      )}

      {!loadingList && items.length === 0 && !error && (
        <EmptyState title={t("templates.emptyResults")} description={t("templates.emptyResultsDesc")} />
      )}
    </div>
  );
}
