import { Link, NavLink, Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import { useSession } from "../../context/SessionContext";
import { ErrorBoundary } from "../error/ErrorBoundary";
import { Button } from "../ui/Button";
import { FadeIn } from "../motion/FadeIn";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-3 py-1.5 text-sm font-medium transition duration-otm ease-otm ${
    isActive
      ? "bg-otm-primary-subtle text-otm-accent shadow-otm-sm"
      : "text-otm-text-muted hover:bg-otm-primary-muted hover:text-otm-text"
  }`;

export function AppLayout() {
  const { t } = useTranslation();
  const { document, reset } = useSession();
  const location = useLocation();

  /**
   * "New model" discards the session document, which is the only copy of the user's work —
   * the home page says so. It used to do that on a single click of a control that sits in
   * the header of every page, with no confirmation, no undo and, for a model that was never
   * analysed, no History snapshot to fall back on. The equivalent session-replacing action
   * on the History page already asks first; this one now asks the same way.
   */
  function confirmReset() {
    if (!globalThis.confirm(t("nav.confirmNewModel"))) return;
    reset();
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden text-otm-text">
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        aria-hidden
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(48, 178, 127, 0.18), transparent), radial-gradient(ellipse 60% 40% at 100% 0%, rgba(86, 255, 149, 0.08), transparent)",
        }}
      />
      <div
        className="pointer-events-none fixed inset-x-0 top-0 -z-10 h-96 opacity-40 blur-3xl"
        style={{
          background:
            "linear-gradient(180deg, rgba(86,255,149,0.12) 0%, transparent 100%)",
        }}
        aria-hidden
      />

      <header className="sticky top-0 z-50 border-b border-otm-border bg-otm-surface-glass backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <Link
            to="/"
            className="group flex items-center gap-3 font-display text-lg font-semibold tracking-tight text-otm-text"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-otm-primary to-otm-accent text-sm font-bold text-otm-green-950 shadow-otm-glow transition duration-otm group-hover:brightness-110">
              OTM
            </span>
            <span className="flex flex-col leading-tight">
              <span>App Suite Modeling</span>
              <span className="text-[11px] font-normal text-otm-text-subtle">
                {t("layout.brandSubtitle")}
              </span>
            </span>
          </Link>

          <nav
            className="flex flex-1 flex-wrap items-center justify-center gap-1 sm:gap-2"
            aria-label={t("layout.ariaMainNav")}
          >
            {!document && (
              <>
                <NavLink to="/templates" className={navLinkClass}>
                  {t("nav.templates")}
                </NavLink>
                <NavLink to="/import" className={navLinkClass}>
                  {t("nav.import")}
                </NavLink>
              </>
            )}
            {document && (
              <>
                <NavLink to="/wizard" className={navLinkClass}>
                  {t("nav.wizard")}
                </NavLink>
                <NavLink to="/review" className={navLinkClass}>
                  {t("nav.review")}
                </NavLink>
                <NavLink to="/analysis" className={navLinkClass}>
                  {t("nav.analysis")}
                </NavLink>
                <NavLink to="/export" className={navLinkClass}>
                  {t("nav.export")}
                </NavLink>
                <NavLink to="/history" className={navLinkClass}>
                  {t("nav.history")}
                </NavLink>
                <NavLink to="/diff" className={navLinkClass}>
                  {t("nav.diff")}
                </NavLink>
              </>
            )}
          </nav>

          <div className="flex items-center justify-end gap-2">
            <LanguageSwitcher />
            <ThemeToggle />
            {document && (
              <Button variant="ghost" className="!py-1.5 !text-xs" onClick={confirmReset}>
                {t("nav.newModel")}
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto min-h-[50vh] w-full min-w-0 max-w-7xl px-4 py-10 md:py-12">
        <FadeIn key={location.pathname}>
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </FadeIn>
      </main>

      <footer className="border-t border-otm-border py-8 text-center text-xs text-otm-text-subtle">
        <p className="mx-auto max-w-2xl leading-relaxed">
          {t("layout.footerNote")}
        </p>
      </footer>
    </div>
  );
}
