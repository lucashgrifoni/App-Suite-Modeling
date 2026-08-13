import { useRef, useState, type SyntheticEvent } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { importArtifact } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Label } from "../components/ui/Label";
import { Select } from "../components/ui/Select";
import { PageHeader } from "../components/patterns/PageHeader";
import { FileDropZone } from "../components/patterns/FileDropZone";
import { WorkflowGuide } from "../components/onboarding/WorkflowGuide";
import { ContextHint } from "../components/onboarding/ContextHint";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import { useConfirmReplaceModel } from "../hooks/useConfirmReplaceModel";
import { fileMatchesAccept } from "../utils/fileAccept";
import { clearWizardStep } from "../utils/wizardStepStorage";
import type { ArtifactImportKind, ArtifactInference, ExplanationRecord } from "../types/api";
import type { OtmDocument } from "../types/document";

export function ImportPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { setDocument } = useSession();
  const toast = useToast();
  const confirmReplaceModel = useConfirmReplaceModel();

  const KINDS: { value: ArtifactImportKind; labelKey: string; accept: string }[] = [
    { value: "openapi", labelKey: "import.kindOpenapi", accept: ".yaml,.yml,.json" },
    { value: "terraform", labelKey: "import.kindTerraform", accept: ".tf" },
    { value: "kubernetes", labelKey: "import.kindKubernetes", accept: ".yaml,.yml" },
  ];

  const [kind, setKind] = useState<ArtifactImportKind>("openapi");
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inferences, setInferences] = useState<ArtifactInference[] | null>(null);
  const [unknowns, setUnknowns] = useState<string[] | null>(null);
  const [structuredExplanations, setStructuredExplanations] = useState<ExplanationRecord[] | null>(null);

  function confidenceLabel(c: ArtifactInference["confidence"]): string {
    if (c === "high") return t("import.confidenceHigh");
    if (c === "medium") return t("import.confidenceMedium");
    return t("import.confidenceLow");
  }

  /**
   * Drop a selection the new artifact type no longer accepts.
   *
   * The drop zone updated its "Accepted types" line while "Selected: main2.tf" stayed put,
   * and submitting a perfectly well-formed Terraform file as OpenAPI answered "The artifact
   * could not be read as YAML or JSON. Check the file opens in an editor without syntax
   * errors" — sending the user to debug a healthy file instead of naming the type mismatch.
   * The input's own value is reset too, or the browser keeps showing the file name next to
   * a state that no longer has one.
   *
   * A `.yaml` that both OpenAPI and Kubernetes accept survives the switch: only a selection
   * the app has just declared unacceptable is discarded.
   */
  function changeKind(next: ArtifactImportKind) {
    setKind(next);
    const accepted = KINDS.find((k) => k.value === next)?.accept ?? "";
    if (!file || fileMatchesAccept(file.name, accepted)) return;
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setError(null);
    toast.info(t("import.selectionClearedByType", { name: file.name, accepted }));
  }

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    if (!file) {
      const msg = t("import.pickFile");
      setError(msg);
      toast.warning(msg);
      return;
    }
    if (!confirmReplaceModel()) return;
    setError(null);
    setLoading(true);
    setInferences(null);
    setUnknowns(null);
    setStructuredExplanations(null);
    try {
      const res = await importArtifact(kind, file);
      setDocument(res.document as unknown as OtmDocument);
      // The draft has never been reviewed, so the wizard opens at step 1 instead of at
      // whatever step the replaced model had reached. See utils/wizardStepStorage.
      clearWizardStep();
      setInferences(res.inferences);
      setUnknowns(res.unknowns);
      setStructuredExplanations(res.explanations ?? null);
      toast.success(t("import.toastImported"));
    } catch (err) {
      const msg = apiErrorMessage(err, t, "import.toastFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  const meta = KINDS.find((k) => k.value === kind);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={t("import.eyebrow")}
        title={t("import.title")}
        description={
          <Trans
            i18nKey="import.description"
            components={{ 0: <strong className="text-otm-text" /> }}
          />
        }
      />

      <div className="space-y-2 rounded-otm-lg border border-otm-border/80 bg-otm-surface-1/50 px-4 py-3">
        <WorkflowGuide variant="compact" />
        <ContextHint>
          <Trans
            i18nKey="import.contextAfterDraft"
            components={{ 0: <strong className="font-medium text-otm-text-muted" /> }}
          />
        </ContextHint>
      </div>

      <Alert variant="info">
        <Trans
          i18nKey="import.alertResult"
          components={{
            0: (
              <Link to="/analysis" className="font-medium text-otm-accent underline-offset-4 hover:underline" />
            ),
          }}
        />
      </Alert>

      <Card title={t("import.cardTitle")} subtitle={t("import.cardSubtitle")} variant="glass">
        <form onSubmit={onSubmit} className="space-y-4" aria-busy={loading}>
          <div>
            <Label htmlFor="kind">{t("import.artifactType")}</Label>
            <Select
              id="kind"
              value={kind}
              onChange={(e) => changeKind(e.target.value as ArtifactImportKind)}
              className="mt-1 w-full max-w-md"
            >
              {KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {t(k.labelKey)}
                </option>
              ))}
            </Select>
          </div>

          <FileDropZone
            disabled={loading}
            onFile={(f) => setFile(f)}
            description={`${t("import.acceptedTypes")} ${meta?.accept ?? "—"}`}
          >
            <div className="mt-4">
              <Label htmlFor="file" className="sr-only">
                {t("import.fileLabel")}
              </Label>
              <input
                id="file"
                ref={fileInputRef}
                type="file"
                accept={meta?.accept}
                className="mx-auto block w-full max-w-sm text-sm text-otm-text-muted file:mr-3 file:rounded-otm-md file:border file:border-otm-border file:bg-otm-surface-2 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-otm-text"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              {file ? (
                <p className="mt-2 text-xs text-otm-accent">
                  {t("import.selected")} <span className="font-mono">{file.name}</span>
                </p>
              ) : null}
            </div>
          </FileDropZone>

          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={loading}>
              {loading ? t("import.submitLoading") : t("import.submit")}
            </Button>
            <Button type="button" variant="secondary" onClick={() => navigate("/wizard")}>
              {t("import.goWizard")}
            </Button>
          </div>
        </form>
      </Card>

      {error && <Alert>{error}</Alert>}

      {inferences && inferences.length > 0 && (
        <Card title={t("import.inferencesTitle")} subtitle={t("import.inferencesSubtitle")} variant="elevated">
          <ul className="list-inside list-disc space-y-2 text-sm text-otm-text-muted">
            {inferences.map((i) => (
              <li key={i.id}>
                <span className="text-otm-text-subtle">[{confidenceLabel(i.confidence)}]</span> {i.message}
              </li>
            ))}
          </ul>
          {structuredExplanations && structuredExplanations.length > 0 ? (
            <details className="mt-4 rounded-otm-md border border-otm-border bg-otm-surface-1 p-3 text-xs text-otm-text-muted">
              <summary className="cursor-pointer font-medium text-otm-text">{t("import.jsonContractSummary")}</summary>
              <p className="mt-2">
                <Trans
                  i18nKey="import.jsonContractBody"
                  components={{
                    0: <code className="rounded bg-otm-surface-3 px-1 text-otm-accent" />,
                  }}
                />
              </p>
            </details>
          ) : null}
        </Card>
      )}

      {unknowns && unknowns.length > 0 && (
        <Card title={t("import.unknownTitle")} subtitle={t("import.unknownSubtitle")} variant="glass">
          <ul className="list-inside list-disc space-y-1 text-sm text-amber-900 dark:text-amber-100">
            {unknowns.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
