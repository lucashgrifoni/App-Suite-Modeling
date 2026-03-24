import { Link, NavLink, Outlet } from "react-router-dom";
import { useSession } from "../../context/SessionContext";
import { Button } from "../ui/Button";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm font-medium ${isActive ? "text-slate-900" : "text-slate-500 hover:text-slate-800"}`;

export function AppLayout() {
  const { document, reset } = useSession();

  return (
    <div className="min-h-screen bg-[var(--asm-bg)] text-slate-900">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="text-lg font-semibold tracking-tight text-slate-900">
            App Suite Modeling
          </Link>
          {document && (
            <nav className="flex flex-1 flex-wrap items-center justify-center gap-x-4 gap-y-1 text-center sm:gap-6">
              <NavLink to="/wizard" className={navClass}>
                Assistente
              </NavLink>
              <NavLink to="/review" className={navClass}>
                Diagrama
              </NavLink>
              <NavLink to="/analysis" className={navClass}>
                Análise
              </NavLink>
              <NavLink to="/export" className={navClass}>
                Exportar
              </NavLink>
            </nav>
          )}
          <div className="flex items-center gap-2">
            {document && (
              <Button variant="ghost" className="!py-1.5 !text-xs" onClick={() => reset()}>
                Novo modelo
              </Button>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-[var(--asm-border)] py-6 text-center text-xs text-slate-500">
        A validação e o motor executam no servidor — a UI não duplica regras de negócio.
      </footer>
    </div>
  );
}
