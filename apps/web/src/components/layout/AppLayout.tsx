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
      {/*
        First focusable element in the document, and it has to stay first.
        WCAG 2.4.1 Bypass Blocks (Level A): tabbing into any route used to cost twenty stops
        before the first control on the page — ten in the header, six in the WorkflowGuide
        breadcrumb that repeats six of the same destinations, four in the stepper — and that
        block repeats on every single page load. Visually hidden until it takes focus, which
        is the point: it is for keyboard and screen-reader users and nobody else.
      */}
      <a
        href="#main"
        className="sr-only rounded-otm-md focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:border focus:border-otm-border focus:bg-otm-surface-1 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-otm-text focus:shadow-otm-md focus:outline-none focus:ring-2 focus:ring-otm-accent"
      >
        {t("layout.skipToContent")}
      </a>
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

      {/*
        `id` is the skip link's target and `tabIndex={-1}` is what makes the jump actually
        move focus: without it several browsers scroll to the fragment and leave focus at
        the top of the document, so the next Tab lands back on the second nav link. -1 keeps
        it out of the tab sequence, so the outline it would draw on a whole page region
        after a mouse interaction is suppressed rather than shown for no reason.
      */}
      <main
        id="main"
        tabIndex={-1}
        className="mx-auto min-h-[50vh] w-full min-w-0 max-w-7xl px-4 py-10 focus:outline-none md:py-12"
      >
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
