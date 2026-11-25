import { TopologyPreview } from "../components/diagram/TopologyPreview";
import { WorkspaceIcon } from "../components/ui/WorkspaceIcon";
import { WorkspaceStat } from "../components/patterns/ModelSummary";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { createBlankModel } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/patterns/PageHeader";
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
    <div className="work-page">
      <PageHeader
        eyebrow={t("work.area")}
        title={document ? t("work.overview") : t("home.title")}
        description={document ? t("work.resumeHint") : t("home.startSubtitle")}
      />
      {error && <Alert>{error}</Alert>}
      {document && (
        <>
          <section className="work-panel work-session work-half">
            <div>
              <div className="work-row work-text-link">
                <WorkspaceIcon name="folder" />
                {t("work.sessionModel")}
              </div>
              <h2>{document.metadata.title}</h2>
              <p className="work-muted">{document.metadata.summary}</p>
              <p className="mt-3 text-xs text-otm-text-muted">
                {[document.metadata.owner, t("work.schema", { value: document.model.schema_version })]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <Link className="work-action primary" to="/wizard">
                  {t("home.continueWizard")}
                  <WorkspaceIcon name="arrow" />
                </Link>
                <Link className="work-action" to="/review">
                  <WorkspaceIcon name="review" />
                  {t("nav.review")}
                </Link>
              </div>
            </div>
            <TopologyPreview document={document} />
          </section>
          <section>
            <h2 className="work-section-title">{t("work.structure")}</h2>
            <div className="work-stats">
              <WorkspaceStat
                icon="box"
                label={t("review.componentsTitle")}
                value={document.components.length}
              />
              <WorkspaceStat
                icon="flow"
                label={t("review.flowsTitle")}
                value={document.data_flows.length}
              />
              <WorkspaceStat
                icon="boundary"
                label={t("work.boundaries")}
                value={document.trust_boundaries.length}
              />
              <WorkspaceStat
                icon="asset"
                label={t("review.assetsTitle")}
                value={document.assets.length}
              />
            </div>
          </section>
        </>
      )}
      <section>
        <h2 className="work-section-title">{document ? t("work.startOther") : t("home.startTitle")}</h2>
        <div className="work-choices">
          <button
            type="button"
            className="work-choice"
            aria-label={loading ? t("home.createLoading") : t("home.createCta")}
            disabled={loading}
            onClick={startBlank}
          >
            <span className="work-iconbox">
              <WorkspaceIcon name="plus" />
            </span>
            <strong>{loading ? t("home.createLoading") : t("home.createCta")}</strong>
            <small>{t("quickStart.blankDesc")}</small>
          </button>
          <Link className="work-choice" to="/import">
            <span className="work-iconbox">
              <WorkspaceIcon name="import" />
            </span>
            <strong>{t("home.importArtifact")}</strong>
            <small>{t("quickStart.importDesc")}</small>
          </Link>
          <Link className="work-choice" to="/templates">
            <span className="work-iconbox">
              <WorkspaceIcon name="templates" />
            </span>
            <strong>{t("home.exploreTemplates")}</strong>
            <small>{t("quickStart.templateDesc")}</small>
          </Link>
        </div>
      </section>
      <p className="work-muted">{t("home.mvpAlert")}</p>
    </div>
  );
}
