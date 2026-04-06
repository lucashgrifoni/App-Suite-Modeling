import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";

export function QuickStartPanel({
  onBlank,
  loading,
}: Readonly<{
  onBlank: () => void;
  loading: boolean;
}>) {
  const { t } = useTranslation();

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-otm-text-subtle">{t("quickStart.fast")}</p>
        <p className="mt-1 font-display text-sm font-semibold text-otm-text">{t("quickStart.blankTitle")}</p>
        <p className="mt-1 text-xs text-otm-text-muted">{t("quickStart.blankDesc")}</p>
        <Button className="mt-3 w-full" disabled={loading} onClick={onBlank}>
          {loading ? t("quickStart.blankCtaLoading") : t("quickStart.blankCta")}
        </Button>
      </div>
      <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-otm-text-subtle">{t("quickStart.infra")}</p>
        <p className="mt-1 font-display text-sm font-semibold text-otm-text">{t("quickStart.importTitle")}</p>
        <p className="mt-1 text-xs text-otm-text-muted">{t("quickStart.importDesc")}</p>
        <Link to="/import" className="mt-3 block">
          <Button variant="secondary" className="w-full">
            {t("quickStart.importBtn")}
          </Button>
        </Link>
      </div>
      <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-otm-text-subtle">
          {t("quickStart.accelerator")}
        </p>
        <p className="mt-1 font-display text-sm font-semibold text-otm-text">{t("quickStart.templateTitle")}</p>
        <p className="mt-1 text-xs text-otm-text-muted">{t("quickStart.templateDesc")}</p>
        <Link to="/templates" className="mt-3 block">
          <Button variant="secondary" className="w-full">
            {t("quickStart.templateBtn")}
          </Button>
        </Link>
      </div>
    </div>
  );
}
