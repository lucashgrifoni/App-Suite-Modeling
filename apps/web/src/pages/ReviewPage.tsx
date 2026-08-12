import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate } from "react-router";
import { validateDocument } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
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
  const { t } = useTranslation();
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
        t("review.validMeta", {
          schema: v.schema_version,
          components: v.component_count,
          threats: v.threat_count,
        }),
      );
      toast.success(t("review.validOk"));
    } catch (e) {
      setMeta(null);
      const msg = apiErrorMessage(e, t, "review.validationError");
      setErr(msg);
      toast.error(msg);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={t("review.eyebrow")}
        title={t("review.title")}
        description={t("review.description")}
        actions={
          <>
            <Button variant="secondary" onClick={() => void quickValidate()}>
              {t("review.validateServer")}
            </Button>
            <Link to="/analysis">
              <Button>{t("review.runAnalysis")}</Button>
            </Link>
          </>
        }
      />

      {meta && <Alert variant="success">{meta}</Alert>}
      {err && <Alert>{err}</Alert>}

      <Card
        title={t("review.diagramCardTitle")}
        subtitle={t("review.diagramCardSubtitle")}
        variant="glass"
      >
        <ThreatModelDiagram document={doc} setDocument={setDocument} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card
          title={t("review.componentsTitle")}
          subtitle={t("review.items", { count: doc.components.length })}
          variant="glass"
        >
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
        <Card
          title={t("review.flowsTitle")}
          subtitle={t("review.links", { count: doc.data_flows.length })}
          variant="glass"
        >
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
        <Card title={t("review.trustTitle")} subtitle={t("review.trustSubtitle")} variant="glass">
          <ul className="divide-y divide-otm-border">
            {doc.trust_boundaries.map((b, idx) => (
              <li key={b.id} className="space-y-2 py-4 first:pt-0">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-mono text-xs text-otm-text-subtle">{b.id}</span>
                  <span className="font-medium text-otm-text">{b.name}</span>
                </div>
                {b.inference_note ? (
                  <p className="text-xs text-otm-text-muted">
                    <span className="font-semibold text-otm-text-subtle">{t("review.whyPrefix")} </span>
                    {b.inference_note}
                  </p>
                ) : null}
                {(b.crossing_flow_ids?.length ?? 0) > 0 ? (
                  <p className="text-xs text-otm-text-muted">
                    <span className="font-semibold text-otm-text-subtle">{t("review.crossingFlows")} </span>
                    {(b.crossing_flow_ids ?? []).join(", ")}
                  </p>
                ) : null}
                <div className="grid gap-2 sm:grid-cols-2">
                  <div>
                    <Label htmlFor={`inf-${b.id}`}>{t("review.noteOverride")}</Label>
                    <Input
                      id={`inf-${b.id}`}
                      className="mt-1 text-sm"
                      value={b.inference_note ?? ""}
                      onChange={(e) => updateTrustBoundary(idx, { inference_note: e.target.value || null })}
                      placeholder={t("review.trustPlaceholder")}
                    />
                  </div>
                  <label className="flex cursor-pointer items-center gap-2 pt-6 text-sm text-otm-text-muted">
                    <Checkbox
                      checked={b.user_validated === true}
                      onChange={(e) => updateTrustBoundary(idx, { user_validated: e.target.checked })}
                    />
                    {t("review.validatedByModeler")}
                  </label>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {doc.assets.length > 0 ? (
        <Card title={t("review.assetsTitle")} subtitle={t("review.assetsSubtitle")} variant="glass">
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
                      <Label htmlFor={`bc-${a.id}`}>{t("review.criticality")}</Label>
                      <Input
                        id={`bc-${a.id}`}
                        className="mt-1 text-sm"
                        value={a.business_criticality ?? ""}
                        onChange={(e) => updateAsset(idx, { business_criticality: e.target.value || undefined })}
                        placeholder={t("review.placeholderCriticality")}
                      />
                    </div>
                    <div>
                      <Label htmlFor={`cl-${a.id}`}>{t("review.classification")}</Label>
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
                        placeholder={t("review.placeholderClassification")}
                      />
                    </div>
                  </div>
                  {(a.related_component_ids?.length ?? 0) > 0 ||
                  (a.related_data_flow_ids?.length ?? 0) > 0 ? (
                    <p className="text-xs text-otm-text-muted">
                      {(a.related_component_ids?.length ?? 0) > 0 ? (
                        <>
                          <span className="font-semibold text-otm-text-subtle">
                            {t("review.relatedComponentsLabel")}{" "}
                          </span>
                          {(a.related_component_ids ?? []).join(", ")}
                        </>
                      ) : null}
                      {(a.related_data_flow_ids?.length ?? 0) > 0 ? (
                        <>
                          {" "}
                          <span className="font-semibold text-otm-text-subtle">
                            {t("review.relatedFlowsLabel")}{" "}
                          </span>
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

      <Card title={t("review.advancedTitle")} subtitle={t("review.advancedSubtitle")} variant="elevated">
        <Button variant="ghost" className="mb-2 !px-0" onClick={() => setShowJson((v) => !v)}>
          {showJson ? t("review.hideJson") : t("review.showJson")}
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
