import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "../ui/Button";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Captura erros de renderização e apresenta fallback alinhado ao DS (sem dependências extra).
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[otm-web] ErrorBoundary", error, info.componentStack);
  }

  private reload = () => {
    this.setState({ error: null });
    globalThis.location?.reload();
  };

  override render() {
    if (this.state.error) {
      return (
        <div
          className="rounded-otm-xl border border-red-500/30 bg-red-950/40 px-6 py-8 text-center shadow-otm-md"
          role="alert"
        >
          <p className="font-display text-lg font-semibold text-red-100">Algo correu mal na interface</p>
          <p className="mt-2 text-sm text-red-200/90">
            {this.state.error.message || "Erro inesperado ao renderizar este ecrã."}
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            <Button type="button" onClick={this.reload}>
              Recarregar página
            </Button>
            <a href="/">
              <Button variant="secondary" type="button">
                Voltar ao início
              </Button>
            </a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
