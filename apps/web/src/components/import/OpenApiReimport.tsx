import { useState, type SyntheticEvent } from "react";
import { useTranslation } from "react-i18next";
import { apiErrorMessage } from "../../api/apiErrorMessage";
import { previewOpenApiReimport } from "../../api/otmApi";
import { useToast } from "../../context/ToastContext";
import type { OpenApiReimportPreview } from "../../types/api";
import type { OtmDocument } from "../../types/document";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Label } from "../ui/Label";

const operationSections = ["added", "removed", "changed", "shared_sections_changed"] as const;
const fileClass =
  "block w-full min-w-0 text-sm text-otm-text-muted file:mr-3 file:rounded-otm-md file:border file:border-otm-border file:bg-otm-surface-2 file:px-3 file:py-1.5 file:text-otm-text";

type Props = {
  document: OtmDocument;
  onApply: (document: OtmDocument) => void;
};

function displayValue(value: unknown): string {
  return typeof value === "string" ? value : (JSON.stringify(value) ?? "—");
}

export function OpenApiReimport({ document, onApply }: Readonly<Props>) {
  const { t } = useTranslation();
  const toast = useToast();
  const [previous, setPrevious] = useState<File | null>(null);
  const [revised, setRevised] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<{ source: OtmDocument; result: OpenApiReimportPreview } | null>(null);
  const preview = review?.source === document ? review.result : null;

  function clearReview() {
    setReview(null);
    setError(null);
  }

  async function compare(event: SyntheticEvent) {
    event.preventDefault();
    if (!previous || !revised || loading) return;
    clearReview();
    setLoading(true);
    try {
      const result = await previewOpenApiReimport(previous, revised, document);
      setReview({ source: document, result });
    } catch (cause) {
      setError(apiErrorMessage(cause, t, "import.toastFail"));
    } finally {
      setLoading(false);
    }
  }

  function apply() {
    if (!preview?.changes.length) return;
    onApply(preview.document as unknown as OtmDocument);
    setReview(null);
    toast.success(t("import.reimportApplied"));
  }

  return (
    <Card title={t("import.reimportTitle")} variant="glass">
      <form onSubmit={compare} className="space-y-4" aria-busy={loading}>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="min-w-0">
            <Label htmlFor="openapi-previous">{t("import.reimportPrevious")}</Label>
            <input
              id="openapi-previous" type="file" accept=".yaml,.yml,.json" className={fileClass}
              disabled={loading}
              onChange={(event) => { setPrevious(event.target.files?.[0] ?? null); clearReview(); }}
            />
          </div>
          <div className="min-w-0">
            <Label htmlFor="openapi-revised">{t("import.reimportRevised")}</Label>
            <input
              id="openapi-revised" type="file" accept=".yaml,.yml,.json" className={fileClass}
              disabled={loading}
              onChange={(event) => { setRevised(event.target.files?.[0] ?? null); clearReview(); }}
            />
          </div>
        </div>
        <Button type="submit" variant="secondary" disabled={loading || !previous || !revised}>
          {loading ? t("import.reimportComparing") : t("import.reimportCompare")}
        </Button>
      </form>
      {error && <Alert className="mt-4">{error}</Alert>}
      {preview && (
        <section className="mt-4 space-y-4 text-sm" aria-label={t("import.reimportReview")}>
          <dl className="grid gap-3 sm:grid-cols-2">
            {operationSections.map((key) => (
              <div key={key} className="min-w-0 rounded-otm-md border border-otm-border p-3">
                <dt className="font-medium">{t(`import.reimportOps.${key}`)}</dt>
                <dd className="mt-1 text-otm-text-muted">
                  <ul className="space-y-1 break-all font-mono">
                    {(preview.operations[key] ?? []).map((operation) => <li key={operation}>{operation}</li>)}
                  </ul>
                  {!preview.operations[key]?.length && "—"}
                </dd>
              </div>
            ))}
          </dl>
          {preview.conflicts.length > 0 && (
            <Alert variant="warning">
              <p className="font-medium">{t("import.reimportConflicts")}</p>
              <ul className="mt-2 space-y-2 break-all">
                {preview.conflicts.map(({ field, before, after }) => (
                  <li key={field}>
                    <code>{field}</code>
                    <div>{t("import.reimportCurrent")} {displayValue(before)}</div>
                    <div>{t("import.reimportIncoming")} {displayValue(after)}</div>
                  </li>
                ))}
              </ul>
            </Alert>
          )}
          {preview.changes.length > 0 ? (
            <>
              <p className="font-medium">{t("import.reimportChanges")}</p>
              <ul className="list-inside list-disc space-y-1 break-all">
                {preview.changes.map(({ field, after }) => (
                  <li key={field}><code>{field}</code>{" → "}{displayValue(after)}</li>
                ))}
              </ul>
              <Button type="button" onClick={apply}>{t("import.reimportApply")}</Button>
            </>
          ) : (
            <p className="text-otm-text-muted">{t("import.reimportNoChanges")}</p>
          )}
        </section>
      )}
    </Card>
  );
}
