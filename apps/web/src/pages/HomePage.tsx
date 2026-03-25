import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createBlankModel } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Alert } from "../components/ui/Alert";
import { useSession } from "../context/SessionContext";

export function HomePage() {
  const navigate = useNavigate();
  const { setDocument, document } = useSession();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function startBlank() {
    setError(null);
    setLoading(true);
    try {
      const { document: doc } = await createBlankModel();
      setDocument(doc);
      navigate("/wizard");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Não foi possível criar o modelo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Threat modeling, passo a passo
        </h1>
        <p className="mt-2 max-w-xl text-slate-600">
          Descreva o sistema, reveja componentes e fluxos, e deixe o motor sugerir ameaças STRIDE com
          ligação a normas (OWASP, NIST CSF, ISO 27001). Tudo validado no servidor.
        </p>
      </div>
      <Alert variant="info">
        Este MVP guarda o rascunho localmente no navegador (sessão atual). Exporte o resultado para
        manter um artefacto persistente.
      </Alert>

      {error && <Alert>{error}</Alert>}

      <div className="grid gap-4 sm:grid-cols-2">
        <Card
          title="Importar artefacto"
          subtitle="OpenAPI, Terraform ou Kubernetes — rascunho com inferências explícitas (revisar antes da análise)."
        >
          <Link to="/import">
            <Button variant="secondary" className="w-full sm:w-auto">
              Importar
            </Button>
          </Link>
        </Card>
        <Card
          title="Começar em branco"
          subtitle="Modelo mínimo válido. Ideal para aprender ou desenhar do zero."
        >
          <Button disabled={loading} className="w-full sm:w-auto" onClick={startBlank}>
            {loading ? "A criar…" : "Criar novo modelo"}
          </Button>
        </Card>
        <Card
          title="Usar um template"
          subtitle="Ponto de partida com componentes típicos (ex.: SaaS web)."
        >
          <Link to="/templates">
            <Button variant="secondary" className="w-full sm:w-auto">
              Escolher template
            </Button>
          </Link>
        </Card>
      </div>

      {document && (
        <p className="text-sm text-slate-500">
          Já tem um modelo em sessão.{" "}
          <Link to="/wizard" className="font-medium text-sky-700 hover:underline">
            Continuar assistente
          </Link>
        </p>
      )}
    </div>
  );
}
