/**
 * Which step the wizard was left on, so a refresh does not throw the user back to step 1.
 *
 * The step belongs to the document being edited, not to the browser tab. Keeping it purely
 * per-session meant a document that arrives from outside the wizard — an imported draft, a
 * gallery template — reopened at the step the PREVIOUS model had reached: a brand-new draft
 * the user had never seen was presented as "4. Finish · Ready to review", with only "Back"
 * and "View logical diagram" offered, while the import page itself promises "use the wizard
 * to adjust IDs and flows before the engine". Every producer of a new document therefore
 * calls `clearWizardStep`, and the wizard opens at step 1 as it does for "Create new model".
 */

const WIZARD_STEP_KEY = "otm.web.wizard.step";

/** The stored step, clamped to `[0, maxStep]`; 0 when absent or unusable. */
export function readWizardStep(maxStep: number): number {
  try {
    const raw = sessionStorage.getItem(WIZARD_STEP_KEY);
    const n = raw === null ? Number.NaN : Number(raw);
    if (!Number.isInteger(n) || n < 0) return 0;
    return Math.min(n, maxStep);
  } catch {
    return 0;
  }
}

export function writeWizardStep(step: number): void {
  try {
    sessionStorage.setItem(WIZARD_STEP_KEY, String(step));
  } catch {
    /* quota / private mode */
  }
}

/** Call whenever a *different* document replaces the one in the session. */
export function clearWizardStep(): void {
  try {
    sessionStorage.removeItem(WIZARD_STEP_KEY);
  } catch {
    /* private mode */
  }
}
