import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useSession } from "../context/SessionContext";

/**
 * Ask before an action replaces the model in the session.
 *
 * The session document is the only copy of the user's work — the home page says so, and
 * History holds nothing until an analysis or an export has been run. Two of the actions
 * that replace it already ask ("New model" in the header, Restore on the History page)
 * while three did not: "Use this template", the import page's "Generate draft", and
 * "Create new model" on the home page. A user who had spent an afternoon on a model lost
 * it to a single click, with no dialog, no toast and nothing to restore from.
 *
 * Returns a predicate: `true` means the caller may proceed. With no model in the session
 * there is nothing to lose, so nothing is asked.
 */
export function useConfirmReplaceModel(): () => boolean {
  const { t } = useTranslation();
  const { document } = useSession();
  return useCallback(
    () => document === null || globalThis.confirm(t("session.confirmReplaceModel")),
    [document, t],
  );
}
