import { useEffect, useMemo, useRef, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link, Navigate } from "react-router";
import { validateDocument } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Label } from "../components/ui/Label";
import { Select } from "../components/ui/Select";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/patterns/PageHeader";
import { ModelSummary } from "../components/patterns/ModelSummary";
import { Stepper } from "../components/patterns/Stepper";
import { Panel } from "../components/patterns/Panel";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import { updateArrayItem } from "../utils/collections";
import {
  applyDataFlowIdRename,
  OTM_ENTITY_ID_REGEX,
  removeComponents,
  removeDataFlows,
  sanitizeEntityIdInput,
} from "../utils/documentNormalize";
import { applyComponentIdRename, nextEntityId } from "../utils/wizardEdits";
import { readWizardStep, writeWizardStep } from "../utils/wizardStepStorage";
import { useStableRowKeys } from "../utils/useStableRowKeys";
import {
  getAdaptiveAnswer,
  promptsForProfile,
  setAdaptiveAnswer,
  type AdaptiveAnswer,
  type AdaptivePrompt,
} from "../constants/adaptiveWizard";
import type { MethodologyId } from "../types/methodology";
import {
  COMPONENT_KINDS,
  SYSTEM_TYPES,
  type OtmComponent,
  type OtmDataFlow,
} from "../types/document";

const STEP_DEFS = [
  { id: 0, labelKey: "wizard.stepContext" as const },
  { id: 1, labelKey: "wizard.stepComponents" as const },
  { id: 2, labelKey: "wizard.stepFlows" as const },
  { id: 3, labelKey: "wizard.stepDone" as const },
];

const LAST_STEP = STEP_DEFS.length - 1;

/** Espaço/tab/etc. no fim do ID quebra correspondência com fluxos e validação no servidor. */
function idHasTrailingWhitespace(value: string): boolean {
  return /\s$/.test(value);
}

/**
 * The furthest step a document has already earned.
 *
 * Step gating was component-local state initialised to 0, so every arrival at /wizard — and
 * every refresh — re-locked Components, Flows and Finish even for a finished model whose
 * data was right there in the session. Editing an existing model's components meant walking
 * the whole wizard again past steps that had nothing left to ask. Deriving the unlock from
 * the document instead means the tabs describe the model, not this mount's click history.
 */
export function furthestStepForDocument(
  doc: { components?: unknown[]; data_flows?: unknown[] } | null,
): number {
  if (!doc) return 0;
  if (doc.data_flows?.length) return LAST_STEP;
  if (doc.components?.length) return 2;
  return 0;
}

export function WizardPage() {
  const { t, i18n } = useTranslation();
  const { document, setDocument } = useSession();
  const toast = useToast();
  const [step, setStep] = useState(() =>
    Math.min(readWizardStep(LAST_STEP), furthestStepForDocument(document)),
  );
  /** Highest step reached this mount; a step does not re-lock because the user went back. */
  const [maxVisited, setMaxVisited] = useState(step);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  /** ID do fluxo no início da edição (focus), para propagar rename em ativos/fronteiras no blur. */
  const flowIdFocusStartRef = useRef<Map<number, string>>(new Map());
  /** Idem para o ID do componente — sem isto, corrigir um typo desliga os fluxos desse componente. */
  const componentIdFocusStartRef = useRef<Map<number, string>>(new Map());

  const stepsForStepper = useMemo(
    () => STEP_DEFS.map((s) => ({ id: s.id, label: t(s.labelKey) })),
    [t],
  );

  const componentIds = useMemo(
    () => document?.components.map((c) => c.id).filter(Boolean) ?? [],
    [document?.components],
  );

  /**
   * Component ids used by more than one row.
   *
   * The collision is fully decidable in the browser, and deferring it to "Next" meant the
   * user met it as the server's raw verdict — `DOCUMENT_VALIDATION_ERROR: … components:
   * Value error, duplicate id in components` — at the top of the step, with nothing saying
   * which of the rows was wrong. The rows now carry it themselves, next to the field.
   */
  const duplicateComponentIds = useMemo(() => {
    const seen = new Set<string>();
    const repeated = new Set<string>();
    for (const id of componentIds) {
      if (seen.has(id)) repeated.add(id);
      seen.add(id);
    }
    return repeated;
  }, [componentIds]);

  // Row identity for the two editable grids. Not the array index: see useStableRowKeys.
  const componentRowKeys = useStableRowKeys(document?.components.length ?? 0);
  const flowRowKeys = useStableRowKeys(document?.data_flows.length ?? 0);

  const templateProfile = useMemo(
    () => (document?.model.template_semantic_profile ?? "").trim().toLowerCase(),
    [document?.model.template_semantic_profile],
  );
  const adaptivePrompts = useMemo(() => promptsForProfile(templateProfile), [templateProfile]);

  /** Unlocked by what the model already contains, or by how far this visit has walked. */
  const reachableStep = Math.max(furthestStepForDocument(document), maxVisited);

  useEffect(() => writeWizardStep(step), [step]);

  if (!document) return <Navigate to="/" replace />;
  const doc = document;

  function goToStep(next: number) {
    setStep(next);
    setMaxVisited((m) => Math.max(m, next));
  }

  const methodology: MethodologyId = doc.model.methodology ?? "stride";

  function methodologyHintText(): string {
    const key = `wizard.methodologyHints.${methodology}`;
    return i18n.exists(key) ? t(key) : t("wizard.methodologyHints.default");
  }

  function adaptivePromptLabel(p: AdaptivePrompt): string {
    const key = `adaptive.${templateProfile}.${p.id}.label`;
    const tr = t(key);
    return tr === key ? p.label : tr;
  }

  function adaptivePromptHint(p: AdaptivePrompt): string | undefined {
    if (!p.hint) return undefined;
    const key = `adaptive.${templateProfile}.${p.id}.hint`;
    const tr = t(key);
    return tr === key ? p.hint : tr;
  }

  function formatAnswer(a: AdaptiveAnswer | null): string {
    if (a === "yes") return t("wizard.adaptiveYes");
    if (a === "no") return t("wizard.adaptiveNo");
    if (a === "unk") return t("wizard.adaptiveUnk");
    return "—";
  }

  function wizardSummaryLines(prompts: AdaptivePrompt[]): string[] {
    if (!templateProfile || !prompts.length) return [];
    return prompts.map((p) => {
      const v = getAdaptiveAnswer(doc.metadata.tags, templateProfile, p.id);
      return `${adaptivePromptLabel(p)} → ${formatAnswer(v)}`;
    });
  }

  function updateMetadata(partial: Partial<typeof doc.metadata>) {
    setDocument({
      ...doc,
      metadata: { ...doc.metadata, ...partial },
    });
  }

  function updateModel(partial: Partial<typeof doc.model>) {
    setDocument({
      ...doc,
      model: { ...doc.model, ...partial },
    });
  }

  function setComponents(components: OtmComponent[]) {
    setDocument({ ...doc, components });
  }

  function setFlows(flows: OtmDataFlow[]) {
    setDocument({ ...doc, data_flows: flows });
  }

  async function validateAndNext() {
    setError(null);
    setValidating(true);
    try {
      await validateDocument(doc);
      goToStep(Math.min(step + 1, LAST_STEP));
    } catch (e) {
      const msg = apiErrorMessage(e, t, "wizard.validationFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setValidating(false);
    }
  }

  return (
    <div className="work-page">
      <PageHeader
        eyebrow={t("wizard.eyebrow")}
        title={t("wizard.title")}
        description={doc.metadata.title}
        actions={
          <Link className="work-action" to="/review">
            {t("wizard.viewDiagram")}
          </Link>
        }
      />

      <Panel>
        <Stepper
          steps={stepsForStepper}
          currentIndex={step}
          maxReachableIndex={reachableStep}
          onStepClick={(i) => {
            if (i <= reachableStep) goToStep(STEP_DEFS[i].id);
          }}
        />
      </Panel>

      {error && <Alert className="whitespace-pre-wrap break-words">{error}</Alert>}

      <div className="work-split">
        <div className="grid min-w-0 gap-4">
          {step === 0 && (
            <Card title={t("wizard.cardContext")} variant="glass">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="title">{t("wizard.modelTitle")}</Label>
                  <Input
                    id="title"
                    value={doc.metadata.title}
                    onChange={(e) => updateMetadata({ title: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="summary">{t("wizard.summaryOptional")}</Label>
                  <Input
                    id="summary"
                    value={doc.metadata.summary ?? ""}
                    onChange={(e) => updateMetadata({ summary: e.target.value || null })}
                  />
                </div>
                <div>
                  <Label htmlFor="stype">{t("wizard.systemType")}</Label>
                  <Select
                    id="stype"
                    value={doc.model.system_type}
                    onChange={(e) => updateModel({ system_type: e.target.value })}
                  >
                    {SYSTEM_TYPES.map((o) => (
                      <option key={o.value} value={o.value}>
                        {t(`document.systemTypes.${o.value}`)}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <Label htmlFor="methodology">{t("wizard.methodology")}</Label>
                  <Select
                    id="methodology"
                    value={methodology}
                    onChange={(e) => updateModel({ methodology: e.target.value as MethodologyId })}
                  >
                    <option value="stride">STRIDE</option>
                    <option value="pasta">PASTA</option>
                    <option value="nist_data_centric">NIST Data-Centric</option>
                    <option value="linddun">LINDDUN</option>
                    <option value="octave_allegro">OCTAVE Allegro</option>
                    <option value="cia_die">CIA / CIA-DIE</option>
                    <option value="plot4ai">PLOT4ai</option>
                  </Select>
                  <p className="mt-1 text-xs text-otm-text-muted">{methodologyHintText()}</p>
                </div>
                <details className="rounded-otm-md border border-otm-border/80 bg-otm-surface-2/40 px-3 py-2 text-sm">
                  <summary className="cursor-pointer font-medium text-otm-text">
                    {t("wizard.semanticProfile")}
                  </summary>
                  <p className="mt-2 text-xs text-otm-text-muted">
                    <Trans
                      i18nKey="wizard.semanticProfileBody"
                      components={{
                        0: <code className="text-otm-accent" />,
                        1: <code className="text-otm-accent" />,
                        2: <code className="text-otm-accent" />,
                      }}
                    />
                  </p>
                  <div className="mt-2">
                    {/* Was the literal string `template_semantic_profile` — the canonical field
                    name used as the visible label, untranslated, under a summary and a help
                    paragraph that are both translated. */}
                    <Label htmlFor="tprofile">{t("wizard.templateSemanticProfileLabel")}</Label>
                    <Input
                      id="tprofile"
                      className="mt-1 font-mono text-sm"
                      value={doc.model.template_semantic_profile ?? ""}
                      // Trim on blur, not on change. Trimming inside onChange fed the
                      // controlled input back its own trimmed value, so the space the user had
                      // just typed was gone before the next character arrived: "api backend
                      // rest" became "apibackendrest", silently and with no hint that spaces
                      // were unwelcome.
                      onChange={(e) => updateModel({ template_semantic_profile: e.target.value })}
                      onBlur={(e) =>
                        updateModel({ template_semantic_profile: e.target.value.trim() || null })
                      }
                      placeholder={t("wizard.templateSemanticProfilePlaceholder")}
                    />
                  </div>
                </details>
                {templateProfile && adaptivePrompts.length > 0 ? (
                  <details
                    className="rounded-otm-md border border-otm-mint-500/20 bg-emerald-950/10 px-3 py-2 text-sm"
                    open
                  >
                    <summary className="cursor-pointer font-medium text-emerald-900 dark:text-emerald-100">
                      {t("wizard.adaptiveTitle")}
                    </summary>
                    <p className="mt-2 text-xs text-otm-text-muted">{t("wizard.adaptiveBody")}</p>
                    <ul className="mt-3 space-y-3">
                      {adaptivePrompts.map((p) => (
                        <li key={p.id} className="grid gap-1 sm:grid-cols-[1fr_auto] sm:items-center">
                          <div>
                            {/* The question is the control's name. Sitting in a plain sibling
                            paragraph, it was invisible to assistive tech: all three selects
                            announced as a bare "combobox" with no name (WCAG 2.1 4.1.2),
                            while the answers are real data entry — they are stored as tags
                            on the model and travel into the JSON export. `aria-labelledby`
                            keeps the layout exactly as designed. */}
                            <p id={`adaptive-${p.id}-label`} className="text-otm-text">
                              {adaptivePromptLabel(p)}
                            </p>
                            {adaptivePromptHint(p) ? (
                              <p id={`adaptive-${p.id}-hint`} className="text-xs text-otm-text-muted">
                                {adaptivePromptHint(p)}
                              </p>
                            ) : null}
                          </div>
                          <Select
                            className="max-w-[140px] justify-self-end font-mono text-xs"
                            aria-labelledby={`adaptive-${p.id}-label`}
                            aria-describedby={
                              adaptivePromptHint(p) ? `adaptive-${p.id}-hint` : undefined
                            }
                            value={getAdaptiveAnswer(doc.metadata.tags, templateProfile, p.id) ?? "unk"}
                            onChange={(e) => {
                              const v = e.target.value as AdaptiveAnswer | "unk";
                              const ans: AdaptiveAnswer = v === "unk" ? "unk" : v;
                              updateMetadata({
                                tags: setAdaptiveAnswer(doc.metadata.tags, templateProfile, p.id, ans),
                              });
                            }}
                          >
                            <option value="unk">{t("wizard.adaptiveUnk")}</option>
                            <option value="yes">{t("wizard.adaptiveYes")}</option>
                            <option value="no">{t("wizard.adaptiveNo")}</option>
                          </Select>
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : null}
              </div>
            </Card>
          )}

          {step === 1 && (
            <Card
              title={t("wizard.componentsTitle")}
              subtitle={t("wizard.componentsSubtitle")}
              variant="glass"
            >
              <div className="space-y-3">
                {doc.components.map((c, idx) => (
                  <div
                    // Keyed by index, NOT by the edited values: a key derived from `c.id`/`c.name`
                    // changes on every keystroke, which unmounts the row mid-edit and drops focus
                    // to <body>, so the field accepts one character per click. Every mutation here
                    // NOT the edited values: a key derived from `c.id`/`c.name` changes on
                    // every keystroke, unmounts the row mid-edit and drops focus to <body>,
                    // so the field accepts one character per click.
                    key={componentRowKeys.keyAt(idx)}
                    className="grid gap-2 rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 sm:grid-cols-12 sm:items-end"
                  >
                    <div className="sm:col-span-3">
                      <Label htmlFor={`comp-${idx}-id`}>{t("wizard.id")}</Label>
                      <Input
                        id={`comp-${idx}-id`}
                        value={c.id}
                        aria-invalid={
                          idHasTrailingWhitespace(c.id) || duplicateComponentIds.has(c.id) || undefined
                        }
                        aria-describedby={
                          [
                            idHasTrailingWhitespace(c.id) ? `comp-${idx}-id-trail-hint` : null,
                            duplicateComponentIds.has(c.id) ? `comp-${idx}-id-dup-hint` : null,
                          ]
                            .filter(Boolean)
                            .join(" ") || undefined
                        }
                        onFocus={() => {
                          componentIdFocusStartRef.current.set(idx, c.id);
                        }}
                        onBlur={(e) => {
                          // Correcting a component id must carry its flows, assets, boundary
                          // memberships and threat targets with it. Without this, fixing a
                          // typo in the very field that exists for it silently detaches every
                          // flow from that component and the server answers
                          // `data_flow '<id>' from_component '<old>' not found` — which no
                          // screen in this app can repair.
                          const from = componentIdFocusStartRef.current.get(idx);
                          componentIdFocusStartRef.current.delete(idx);
                          const raw = e.target.value;
                          const trimmed = raw.trim();
                          let components = doc.components;
                          let dirty = trimmed !== raw;
                          if (dirty) {
                            components = updateArrayItem(components, idx, { ...c, id: trimmed });
                          }
                          let nextDoc = { ...doc, components };
                          const to = components[idx]?.id ?? "";
                          if (from && to && from !== to && OTM_ENTITY_ID_REGEX.test(to)) {
                            // The helper refuses ambiguous renames (duplicate new id, old id
                            // still in use) by returning the document unchanged.
                            const renamed = applyComponentIdRename(nextDoc, from, to);
                            if (renamed !== nextDoc) {
                              nextDoc = renamed;
                              dirty = true;
                            }
                          }
                          if (dirty) setDocument(nextDoc);
                        }}
                        onChange={(e) => {
                          setComponents(
                            updateArrayItem(doc.components, idx, {
                              ...c,
                              id: sanitizeEntityIdInput(e.target.value),
                            }),
                          );
                        }}
                      />
                      {idHasTrailingWhitespace(c.id) ? (
                        <p
                          id={`comp-${idx}-id-trail-hint`}
                          role="alert"
                          className="mt-1 text-xs font-medium text-amber-600 dark:text-amber-400"
                        >
                          {t("wizard.idTrailingWhitespace")}
                        </p>
                      ) : null}
                      {duplicateComponentIds.has(c.id) ? (
                        <p
                          id={`comp-${idx}-id-dup-hint`}
                          role="alert"
                          className="mt-1 text-xs font-medium text-amber-600 dark:text-amber-400"
                        >
                          {t("wizard.idDuplicate", { id: c.id })}
                        </p>
                      ) : null}
                    </div>
                    <div className="sm:col-span-4">
                      <Label htmlFor={`comp-${idx}-name`}>{t("wizard.name")}</Label>
                      <Input
                        id={`comp-${idx}-name`}
                        value={c.name}
                        // Trim on blur, and fall back to the id when nothing is left. A name of
                        // only spaces was stored verbatim and travelled into every deliverable:
                        // an empty Mermaid node, and `- **   ** (`id`)` in the Markdown export,
                        // where the bold markers wrap nothing and render as literal asterisks.
                        // The id is the one label guaranteed to exist, so it stands in rather
                        // than shipping a blank. Trimming here and not in onChange keeps the
                        // space the user just typed from vanishing mid-word.
                        onBlur={(e) => {
                          const trimmed = e.target.value.trim();
                          if (trimmed === c.name) return;
                          setComponents(
                            updateArrayItem(doc.components, idx, { ...c, name: trimmed || c.id }),
                          );
                        }}
                        onChange={(e) => {
                          setComponents(
                            updateArrayItem(doc.components, idx, { ...c, name: e.target.value }),
                          );
                        }}
                      />
                    </div>
                    <div className="sm:col-span-3">
                      <Label htmlFor={`comp-${idx}-kind`}>{t("wizard.type")}</Label>
                      <Select
                        id={`comp-${idx}-kind`}
                        value={c.kind}
                        onChange={(e) => {
                          setComponents(
                            updateArrayItem(doc.components, idx, { ...c, kind: e.target.value }),
                          );
                        }}
                      >
                        {COMPONENT_KINDS.map((k) => (
                          <option key={k.value} value={k.value}>
                            {t(`document.componentKinds.${k.value}`)}
                          </option>
                        ))}
                      </Select>
                    </div>
                    <div className="sm:col-span-2">
                      <Button
                        variant="ghost"
                        className="w-full text-red-300"
                        // Cascades to flows, assets and trust boundaries. A plain splice here
                        // left orphan references that the canonical schema rejects, bricking
                        // validate/analyze/export for the rest of the session.
                        //
                        // The cascade is right; doing it in silence was not. Data flows are
                        // authored separately, on their own wizard step, and two of them could
                        // vanish from one click on "Remove" with no dialog, no notification and
                        // no inline message — the only trace was a count changing on a step the
                        // user may not revisit.
                        onClick={() => {
                          componentRowKeys.noteRemoval(idx);
                          const next = removeComponents(doc, [c.id]);
                          const droppedFlows = doc.data_flows.length - next.data_flows.length;
                          setDocument(next);
                          if (droppedFlows > 0) {
                            toast.warning(
                              t("wizard.removeCascadedToFlows", {
                                count: droppedFlows,
                                name: c.name || c.id,
                              }),
                            );
                          }
                        }}
                      >
                        {t("wizard.remove")}
                      </Button>
                    </div>
                  </div>
                ))}
                <Button
                  variant="secondary"
                  onClick={() => {
                    componentRowKeys.noteInsert();
                    setComponents([
                      ...doc.components,
                      {
                        // Array length is not a monotonic counter: add two, delete the
                        // first, add again and it hands back the surviving row's id.
                        id: nextEntityId("comp_", componentIds),
                        name: t("wizard.newComponentShort"),
                        kind: "process",
                      },
                    ]);
                  }}
                >
                  {t("wizard.addComponent")}
                </Button>
              </div>
            </Card>
          )}

          {step === 2 && (
            <Card title={t("wizard.flowsTitle")} subtitle={t("wizard.flowsSubtitle")} variant="glass">
              <div className="space-y-3">
                {doc.data_flows.map((f, idx) => (
                  <div
                    // Index key — see the components list above. A content-derived key also broke
                    // the flow-ID rename propagation below, whose onFocus/onBlur pair cannot
                    // survive an element destroyed mid-edit.
                    key={flowRowKeys.keyAt(idx)}
                    className="grid gap-2 rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 sm:grid-cols-12 sm:items-end"
                  >
                    <div className="sm:col-span-2">
                      <Label htmlFor={`flow-${idx}-id`}>{t("wizard.flowId")}</Label>
                      <p className="mb-1 text-[11px] text-otm-text-muted">
                        {t("wizard.flowIdRenameHint")}
                      </p>
                      <Input
                        id={`flow-${idx}-id`}
                        value={f.id}
                        aria-invalid={idHasTrailingWhitespace(f.id) || undefined}
                        aria-describedby={
                          idHasTrailingWhitespace(f.id) ? `flow-${idx}-id-trail-hint` : undefined
                        }
                        onFocus={() => {
                          flowIdFocusStartRef.current.set(idx, f.id);
                        }}
                        onBlur={(e) => {
                          const from = flowIdFocusStartRef.current.get(idx);
                          flowIdFocusStartRef.current.delete(idx);
                          const raw = e.target.value;
                          const trimmed = raw.trim();
                          let flows = doc.data_flows;
                          if (trimmed !== raw) {
                            flows = updateArrayItem(flows, idx, { ...f, id: trimmed });
                          }
                          const to = flows[idx]?.id ?? "";
                          let nextDoc: typeof doc = { ...doc, data_flows: flows };
                          let dirty = trimmed !== raw;
                          if (
                            from !== undefined &&
                            from &&
                            to &&
                            from !== to &&
                            OTM_ENTITY_ID_REGEX.test(to) &&
                            nextDoc.data_flows.filter((x) => x.id === to).length === 1
                          ) {
                            nextDoc = applyDataFlowIdRename(nextDoc, from, to);
                            dirty = true;
                          }
                          if (dirty) setDocument(nextDoc);
                        }}
                        onChange={(e) => {
                          setFlows(
                            updateArrayItem(doc.data_flows, idx, {
                              ...f,
                              id: sanitizeEntityIdInput(e.target.value),
                            }),
                          );
                        }}
                      />
                      {idHasTrailingWhitespace(f.id) ? (
                        <p
                          id={`flow-${idx}-id-trail-hint`}
                          role="alert"
                          className="mt-1 text-xs font-medium text-amber-600 dark:text-amber-400"
                        >
                          {t("wizard.idTrailingWhitespace")}
                        </p>
                      ) : null}
                    </div>
                    <div className="sm:col-span-3">
                      <Label htmlFor={`flow-${idx}-from`}>{t("wizard.from")}</Label>
                      <Select
                        id={`flow-${idx}-from`}
                        value={f.from_component}
                        onChange={(e) => {
                          setFlows(
                            updateArrayItem(doc.data_flows, idx, {
                              ...f,
                              from_component: e.target.value,
                            }),
                          );
                        }}
                      >
                        <option value="">—</option>
                        {componentIds.map((id) => (
                          <option key={id} value={id}>
                            {id}
                          </option>
                        ))}
                      </Select>
                    </div>
                    <div className="sm:col-span-3">
                      <Label htmlFor={`flow-${idx}-to`}>{t("wizard.to")}</Label>
                      <Select
                        id={`flow-${idx}-to`}
                        value={f.to_component}
                        onChange={(e) => {
                          setFlows(
                            updateArrayItem(doc.data_flows, idx, { ...f, to_component: e.target.value }),
                          );
                        }}
                      >
                        <option value="">—</option>
                        {componentIds.map((id) => (
                          <option key={id} value={id}>
                            {id}
                          </option>
                        ))}
                      </Select>
                    </div>
                    <div className="sm:col-span-2">
                      <Label htmlFor={`flow-${idx}-name`}>{t("wizard.flowNameOptional")}</Label>
                      <p className="mb-1 text-[11px] text-otm-text-muted">{t("wizard.flowNameHint")}</p>
                      <Input
                        id={`flow-${idx}-name`}
                        value={f.name ?? ""}
                        // Trim on blur, as on the component name beside it. `|| null` alone only
                        // catches the empty string, so a name of three spaces was truthy, was
                        // stored, and became a Mermaid edge caption holding nothing plus `(   )`
                        // in the review list. This field is optional, so blank means `null` — no
                        // label — rather than the id fallback a component name needs.
                        onBlur={(e) => {
                          const next = e.target.value.trim() || null;
                          if (next === (f.name ?? null)) return;
                          setFlows(updateArrayItem(doc.data_flows, idx, { ...f, name: next }));
                        }}
                        onChange={(e) => {
                          setFlows(
                            updateArrayItem(doc.data_flows, idx, { ...f, name: e.target.value || null }),
                          );
                        }}
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <Button
                        variant="ghost"
                        className="w-full text-red-700 dark:text-red-300"
                        onClick={() => {
                          flowRowKeys.noteRemoval(idx);
                          setDocument(removeDataFlows(doc, [f.id]));
                        }}
                      >
                        {t("wizard.remove")}
                      </Button>
                    </div>
                  </div>
                ))}
                <Button
                  variant="secondary"
                  onClick={() => {
                    flowRowKeys.noteInsert();
                    setFlows([
                      ...doc.data_flows,
                      {
                        id: nextEntityId(
                          "flow_",
                          doc.data_flows.map((fl) => fl.id),
                        ),
                        from_component: componentIds[0] ?? "",
                        to_component: componentIds[1] ?? componentIds[0] ?? "",
                        name: null,
                      },
                    ]);
                  }}
                >
                  {t("wizard.addFlow")}
                </Button>
              </div>
            </Card>
          )}

          {step === 3 && (
            <Card title={t("wizard.reviewTitle")} variant="elevated">
              <p className="text-sm text-otm-text-muted">{t("wizard.reviewBody")}</p>
              <ul className="mt-3 list-inside list-disc text-sm text-otm-text-muted">
                <li>{t("wizard.reviewCountComponents", { count: doc.components.length })}</li>
                <li>{t("wizard.reviewCountFlows", { count: doc.data_flows.length })}</li>
                <li>{t("wizard.reviewMethodology", { methodology })}</li>
              </ul>
              {wizardSummaryLines(adaptivePrompts).length > 0 ? (
                <details className="mt-4 rounded-otm-md border border-otm-border/80 bg-otm-surface-2/50 px-3 py-2 text-sm">
                  <summary className="cursor-pointer font-medium text-otm-text">
                    {t("wizard.contextSummary")}
                  </summary>
                  <p className="mt-2 text-xs text-otm-text-muted">
                    <Trans
                      i18nKey="wizard.contextSummaryBody"
                      components={{
                        0: <code className="text-otm-accent" />,
                      }}
                    />
                  </p>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-otm-text-muted">
                    {wizardSummaryLines(adaptivePrompts).map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </Card>
          )}

          <div className="flex flex-wrap gap-2">
            {step > 0 && (
              <Button variant="secondary" onClick={() => goToStep(step - 1)}>
                {t("wizard.prev")}
              </Button>
            )}
            {step < LAST_STEP && (
              <Button onClick={() => void validateAndNext()} disabled={validating}>
                {validating ? t("wizard.validating") : t("wizard.next")}
              </Button>
            )}
            {step === LAST_STEP && (
              <Link className="work-action primary" to="/review">
                {t("wizard.viewDiagram")}
              </Link>
            )}
          </div>
        </div>
        <aside>
          <ModelSummary document={doc} />
        </aside>
      </div>
    </div>
  );
}
