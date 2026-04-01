import { Link } from "react-router-dom";
import { Button } from "../ui/Button";

export function QuickStartPanel({
  onBlank,
  loading,
}: Readonly<{
  onBlank: () => void;
  loading: boolean;
}>) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-otm-text-subtle">Rápido</p>
        <p className="mt-1 font-display text-sm font-semibold text-otm-text">Modelo em branco</p>
        <p className="mt-1 text-xs text-otm-text-muted">API cria documento canónico; edita no assistente.</p>
        <Button className="mt-3 w-full" disabled={loading} onClick={onBlank}>
          {loading ? "A criar…" : "Iniciar modelo em branco"}
        </Button>
      </div>
      <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-otm-text-subtle">Infra como código</p>
        <p className="mt-1 font-display text-sm font-semibold text-otm-text">Importar artefacto</p>
        <p className="mt-1 text-xs text-otm-text-muted">Inferências explícitas — revê antes da análise.</p>
        <Link to="/import" className="mt-3 block">
          <Button variant="secondary" className="w-full">
            Ir para importação
          </Button>
        </Link>
      </div>
      <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-otm-text-subtle">Acelerador</p>
        <p className="mt-1 font-display text-sm font-semibold text-otm-text">Template</p>
        <p className="mt-1 text-xs text-otm-text-muted">Ponto de partida com componentes típicos.</p>
        <Link to="/templates" className="mt-3 block">
          <Button variant="secondary" className="w-full">
            Ver templates
          </Button>
        </Link>
      </div>
    </div>
  );
}
