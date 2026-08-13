import { useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { createBlankModel } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/patterns/PageHeader";
import { GlowDivider } from "../components/patterns/GlowDivider";
import { QuickStartPanel } from "../components/onboarding/QuickStartPanel";
import { WorkflowGuide } from "../components/onboarding/WorkflowGuide";
import { HelpCallout } from "../components/onboarding/HelpCallout";
import { ContextHint } from "../components/onboarding/ContextHint";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import { useConfirmReplaceModel } from "../hooks/useConfirmReplaceModel";
import { clearWizardStep } from "../utils/wizardStepStorage";

export function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { setDocument, document } = useSession();
  const toast = useToast();
  const confirmReplaceModel = useConfirmReplaceModel();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function startBlank() {
    if (!confirmReplaceModel()) return;
    setError(null);
    setLoading(true);
    try {
      const { document: doc } = await createBlankModel();
      setDocument(doc);
      // A blank model starts at step 1; without this it would inherit the step the replaced
      // model was left on. See utils/wizardStepStorage.
      clearWizardStep();
      toast.success(t("home.toastCreated"));
      navigate("/wizard");
    } catch (e) {
      const msg = apiErrorMessage(e, t, "home.createError");
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-12">
      <section className="relative overflow-hidden rounded-otm-xl border border-otm-border-strong bg-gradient-to-br from-otm-surface-2/95 via-otm-surface-1/80 to-otm-surface-2/90 p-8 shadow-otm-lg md:p-12 otm-perspective">
        <div className="pointer-events-none absolute -right-24 top-0 h-72 w-72 rounded-full bg-otm-accent/12 blur-3xl" aria-hidden />
        <div className="pointer-events-none absolute -left-16 bottom-0 h-56 w-56 rounded-full bg-otm-primary/25 blur-3xl" aria-hidden />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-otm-mint-400/40 to-transparent" aria-hidden />

        <div className="relative grid gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:items-center">
          <div>
            <PageHeader
              className="!border-b-0 !pb-0"
              eyebrow={t("home.eyebrow")}
              title={t("home.title")}
              description={t("home.description")}
            />
            <div className="mt-8 flex flex-wrap gap-3">
              <Button disabled={loading} onClick={startBlank}>
                {loading ? t("home.createLoading") : t("home.createCta")}
              </Button>
              <Link to="/import">
                <Button variant="secondary">{t("home.importArtifact")}</Button>
              </Link>
              <Link to="/templates">
                <Button variant="ghost">{t("home.exploreTemplates")}</Button>
              </Link>
            </div>
            <ContextHint className="mt-5 max-w-xl">
              <strong className="font-medium text-otm-text-muted">{t("home.contextHintStrong")}</strong>{" "}
              {t("home.contextHintTail")}
            </ContextHint>
          </div>

          <div className="rounded-otm-lg border border-otm-border bg-otm-surface-1/70 p-5 shadow-otm-md backdrop-blur-sm">
            <p className="font-display text-sm font-semibold text-otm-text">{t("home.whyTitle")}</p>
            <ul className="mt-3 space-y-2.5 text-sm text-otm-text-muted">
              <li className="flex gap-2">
                <span className="mt-0.5 text-otm-accent" aria-hidden>
                  ✓
                </span>
                <span>{t("home.why1")}</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-0.5 text-otm-accent" aria-hidden>
                  ✓
                </span>
                <span>{t("home.why2")}</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-0.5 text-otm-accent" aria-hidden>
                  ✓
                </span>
                <span>{t("home.why3")}</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <Alert variant="info">{t("home.mvpAlert")}</Alert>

      {error && <Alert>{error}</Alert>}

      <section className="space-y-4">
        <div>
          <h2 className="font-display text-lg font-semibold text-otm-text">{t("home.startTitle")}</h2>
          <p className="mt-1 text-sm text-otm-text-muted">{t("home.startSubtitle")}</p>
        </div>
        <QuickStartPanel onBlank={startBlank} loading={loading} />
      </section>

      <section>
        <WorkflowGuide />
        <GlowDivider className="mt-8" />
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <HelpCallout title={t("home.flowOneLinerTitle")}>
            <p>
              <Trans
                i18nKey="home.flowOneLinerRich"
                components={{
                  0: <strong className="text-otm-text" />,
                  1: <strong className="text-otm-text" />,
                  2: <strong className="text-otm-text" />,
                  3: <strong className="text-otm-text" />,
                  4: <strong className="text-otm-text" />,
                  5: <strong className="text-otm-text" />,
                }}
              />
            </p>
          </HelpCallout>
          <Card variant="elevated" title={t("home.sessionCardTitle")} subtitle={t("home.sessionCardSubtitle")}>
            {document ? (
              <p className="text-sm text-otm-text-muted">
                {t("home.hasDoc")}{" "}
                <Link to="/wizard" className="font-medium text-otm-accent underline-offset-4 hover:underline">
                  {t("home.continueWizard")}
                </Link>
                {" · "}
                <Link to="/analysis" className="font-medium text-otm-accent underline-offset-4 hover:underline">
                  {t("home.goAnalysis")}
                </Link>
              </p>
            ) : (
              <p className="text-sm text-otm-text-muted">{t("home.noDoc")}</p>
            )}
          </Card>
        </div>
      </section>
    </div>
  );
}
