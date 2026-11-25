import { useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import { useSession } from "../../context/SessionContext";
import { ErrorBoundary } from "../error/ErrorBoundary";
import { Button } from "../ui/Button";
import { FadeIn } from "../motion/FadeIn";
import { WorkspaceIcon, type WorkspaceIconName } from "../ui/WorkspaceIcon";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";
import "../../workspace.css";

const groups = [
  { label: "work.area", routes: ["home", "templates", "import"] },
  { label: "work.model", routes: ["wizard", "review", "analysis"] },
  { label: "work.evidence", routes: ["diff", "export", "history"] },
] as const;
const requiresModel = new Set(["wizard", "review", "analysis", "diff", "export"]);

export function AppLayout() {
  const { t } = useTranslation();
  const { document, reset } = useSession();
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const route = pathname.split("/")[1]?.toLowerCase() || "home";
  function label(key: string) {
    return key === "home" || key === "diff" ? t(`work.${key}`) : t(`nav.${key}`);
  }

  return (
    <div
      className="work-shell"
      onKeyDown={(e) => {
        if (e.key === "Escape" && menuOpen) {
          setMenuOpen(false);
          menuButton.current?.focus();
        }
      }}
    >
      <a href="#main" className="sr-only work-skip focus:not-sr-only">
        {t("layout.skipToContent")}
      </a>
      <aside className="work-rail">
        <div className="work-brandbar">
          <Link to="/" className="work-brand" onClick={() => setMenuOpen(false)}>
            <span className="work-mark">OTM</span>
            <span>
              App Suite<small>Modeling</small>
            </span>
          </Link>
          <button
            ref={menuButton}
            type="button"
            className="work-menu"
            aria-controls="workspace-nav"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <WorkspaceIcon name="menu" />
            {t("work.menu")}
          </button>
        </div>
        <nav
          id="workspace-nav"
          aria-label={t("layout.ariaMainNav")}
          className={menuOpen ? "work-nav is-open" : "work-nav"}
        >
          {groups.map((group) => (
            <div className="work-nav-group" key={group.label}>
              <p>{t(group.label)}</p>
              {group.routes.map((key) => {
                const contents = (
                  <>
                    <WorkspaceIcon name={key as WorkspaceIconName} />
                    {label(key)}
                  </>
                );
                return !document && requiresModel.has(key) ? (
                  <span
                    key={key}
                    aria-disabled="true"
                    className="work-nav-link locked"
                    title={t("work.openFirst")}
                  >
                    {contents}
                  </span>
                ) : (
                  <NavLink
                    key={key}
                    end
                    to={key === "home" ? "/" : `/${key}`}
                    className="work-nav-link"
                    onClick={() => setMenuOpen(false)}
                  >
                    {contents}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="work-local">
          <span className="work-dot" />
          {t("work.local")}
          <small>{t("work.browser")}</small>
        </div>
      </aside>
      <div className="work-body">
        <header className="work-bar">
          <div className="work-crumb">
            <WorkspaceIcon name="folder" />
            <span>{t("work.area")}</span>
            <span aria-hidden="true">/</span>
            <strong>{label(route)}</strong>
          </div>
          <div className="work-tools">
            <ThemeToggle />
            <LanguageSwitcher />
            {document && (
              <Button
                variant="ghost"
                className="!px-2 !text-xs"
                onClick={() => {
                  if (globalThis.confirm(t("nav.confirmNewModel"))) reset();
                }}
              >
                {t("nav.newModel")}
              </Button>
            )}
          </div>
        </header>
        <main id="main" tabIndex={-1} className="work-main">
          <FadeIn key={pathname}>
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </FadeIn>
        </main>
      </div>
    </div>
  );
}
