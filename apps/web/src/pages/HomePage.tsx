import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createBlankModel } from "../api/otmApi";
import { ApiError } from "../api/client";
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

export function HomePage() {
  const navigate = useNavigate();
  const { setDocument, document } = useSession();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function startBlank() {
    setError(null);
    setLoading(true);
    try {
      const { document: doc } = await createBlankModel();
      setDocument(doc);
      toast.success("Modelo criado. A abrir o assistente.");
      navigate("/wizard");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Não foi possível criar o modelo.";
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
              eyebrow="Threat modeling orientado a engenharia"
              title="Threat modeling, passo a passo"
              description={
                <>
                  Modelo canónico validado no servidor, motor STRIDE com referências a normas (OWASP, NIST CSF, ISO
                  27001) e artefactos exportáveis — desenhado para equipas que precisam de evidência técnica, não só
                  diagramas.
                </>
              }
            />
            <div className="mt-8 flex flex-wrap gap-3">
              <Button disabled={loading} onClick={startBlank}>
                {loading ? "A criar…" : "Criar novo modelo"}
              </Button>
              <Link to="/import">
                <Button variant="secondary">Importar artefacto</Button>
              </Link>
              <Link to="/templates">
                <Button variant="ghost">Explorar templates</Button>
              </Link>
            </div>
            <ContextHint className="mt-5 max-w-xl">
              <strong>Validação e análise no backend</strong> — a UI orquestra o fluxo; regras e motor não correm no
              browser.
            </ContextHint>
          </div>

          <div className="rounded-otm-lg border border-otm-border bg-otm-surface-1/70 p-5 shadow-otm-md backdrop-blur-sm">
            <p className="font-display text-sm font-semibold text-otm-text">Porquê usar</p>
            <ul className="mt-3 space-y-2.5 text-sm text-otm-text-muted">
              <li className="flex gap-2">
                <span className="mt-0.5 text-otm-accent" aria-hidden>
                  ✓
                </span>
                <span>Importação com inferências explícitas — revê antes de correr o motor.</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-0.5 text-otm-accent" aria-hidden>
                  ✓
                </span>
                <span>Diff semântico entre versões do modelo (estrutura + opcionalmente análise).</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-0.5 text-otm-accent" aria-hidden>
                  ✓
                </span>
                <span>Exportação alinhada ao documento canónico — adequado a CI e revisão de pares.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <Alert variant="info">
        Este MVP guarda o rascunho localmente no navegador (sessão atual). Exporte o resultado para manter um artefacto
        persistente.
      </Alert>

      {error && <Alert>{error}</Alert>}

      <section className="space-y-4">
        <div>
          <h2 className="font-display text-lg font-semibold text-otm-text">Começar agora</h2>
          <p className="mt-1 text-sm text-otm-text-muted">Três entradas comuns — a mesma base canónica em todos os casos.</p>
        </div>
        <QuickStartPanel onBlank={startBlank} loading={loading} />
      </section>

      <section>
        <WorkflowGuide />
        <GlowDivider className="mt-8" />
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <HelpCallout title="Fluxo em uma frase">
            <p>
              <strong className="text-otm-text">Importar ou criar</strong> → <strong className="text-otm-text">assistente</strong>{" "}
              → <strong className="text-otm-text">diagrama</strong> → <strong className="text-otm-text">análise</strong> →{" "}
              <strong className="text-otm-text">exportar</strong> ou <strong className="text-otm-text">diff</strong> entre
              revisões.
            </p>
          </HelpCallout>
          <Card variant="elevated" title="Documento em sessão" subtitle="Retoma onde parou quando já existe modelo.">
            {document ? (
              <p className="text-sm text-otm-text-muted">
                Já tem um modelo carregado.{" "}
                <Link to="/wizard" className="font-medium text-otm-accent underline-offset-4 hover:underline">
                  Continuar assistente
                </Link>
                {" · "}
                <Link to="/analysis" className="font-medium text-otm-accent underline-offset-4 hover:underline">
                  Ir para análise
                </Link>
              </p>
            ) : (
              <p className="text-sm text-otm-text-muted">
                Sem modelo ativo — use &quot;Criar novo modelo&quot;, importação ou um template para iniciar.
              </p>
            )}
          </Card>
        </div>
      </section>
    </div>
  );
}
