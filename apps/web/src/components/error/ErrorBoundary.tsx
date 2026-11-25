import { Component, type ErrorInfo, type ReactNode } from "react";
import i18n from "../../i18n/i18n";
import { resetFailedChunkRoutes } from "../../lib/lazyRoute";
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

  /**
   * This boundary is keyed on the pathname by the layout, so it is torn down whenever the
   * user navigates. Unmounting *while showing a failure* therefore means exactly one thing:
   * the user has left the broken screen. That is the moment a route whose JavaScript chunk
   * failed to download is allowed to fetch it again — see lib/lazyRoute for why the retry
   * cannot be triggered from inside the failure itself.
   */
  override componentWillUnmount() {
    if (this.state.error) resetFailedChunkRoutes();
  }

  private readonly reload = () => {
    this.setState({ error: null });
    globalThis.location?.reload();
  };

  override render() {
    if (this.state.error) {
      // `error.message` is a library or engine string, not a sentence written for anyone:
      // "Failed to fetch dynamically imported module: /assets/WizardPage-CsLYIQKb.js", with
      // wording that even differs between browsers for the identical fault. It used to be
      // the ONLY line shown, with the translated copy reachable only when the message was
      // empty — which it almost never is, so that copy was effectively dead. The human
      // sentence now leads and the raw text stays one click away for whoever needs it.
      const technical = this.state.error.message;
      return (
        <div
          className="rounded-otm-xl border border-red-500/30 bg-red-950/40 px-6 py-8 text-center shadow-otm-md"
          role="alert"
        >
          <p className="font-display text-lg font-semibold text-red-100">{i18n.t("errorBoundary.title")}</p>
          <p className="mt-2 text-sm text-red-200/90">{i18n.t("errorBoundary.fallback")}</p>
          {technical ? (
            <details className="mx-auto mt-4 max-w-xl text-left">
              <summary className="cursor-pointer text-xs font-medium text-red-200/90">
                {i18n.t("errorBoundary.detailsSummary")}
              </summary>
              <p className="mt-2 break-words rounded-otm-md bg-red-950/60 p-2 font-mono text-xs text-red-100/90">
                {technical}
              </p>
            </details>
          ) : null}
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            <Button type="button" onClick={this.reload}>
              {i18n.t("errorBoundary.reload")}
            </Button>
            <a href="/">
              <Button variant="secondary" type="button">
                {i18n.t("errorBoundary.home")}
              </Button>
            </a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
