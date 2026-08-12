import { useMemo, useRef, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link, Navigate } from "react-router";
import { validateDocument } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Label } from "../components/ui/Label";
import { Select } from "../components/ui/Select";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/patterns/PageHeader";
import { WorkflowGuide } from "../components/onboarding/WorkflowGuide";
import { HelpCallout } from "../components/onboarding/HelpCallout";
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

/** Espaço/tab/etc. no fim do ID quebra correspondência com fluxos e validação no servidor. */
function idHasTrailingWhitespace(value: string): boolean {
  return /\s$/.test(value);
}

export function WizardPage() {
  const { t, i18n } = useTranslation();
  const { document, setDocument } = useSession();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  /** ID do fluxo no início da edição (focus), para propagar rename em ativos/fronteiras no blur. */
  const flowIdFocusStartRef = useRef<Map<number, string>>(new Map());

  const stepsForStepper = useMemo(
    () => STEP_DEFS.map((s) => ({ id: s.id, label: t(s.labelKey) })),
    [t],
  );

  const componentIds = useMemo(
    () => document?.components.map((c) => c.id).filter(Boolean) ?? [],
    [document?.components],
  );

  const templateProfile = useMemo(
    () => (document?.model.template_semantic_profile ?? "").trim().toLowerCase(),
    [document?.model.template_semantic_profile],
  );
  const adaptivePrompts = useMemo(() => promptsForProfile(templateProfile), [templateProfile]);

  if (!document) return <Navigate to="/" replace />;
  const doc = document;

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
      setStep((s) => Math.min(s + 1, STEP_DEFS.length - 1));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : t("wizard.validationFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setValidating(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={t("wizard.eyebrow")}
        title={t("wizard.title")}
        description={
          <Trans
            i18nKey="wizard.description"
            components={{
              0: <code className="rounded bg-otm-surface-3 px-1 text-xs text-otm-accent" />,
              1: <code className="rounded bg-otm-surface-3 px-1 text-xs text-otm-accent" />,
            }}
          />
        }
      />

      <div className="space-y-3">
        <WorkflowGuide variant="compact" />
        <HelpCallout title={t("wizard.helpNext")} tone="tip">
          <p>
            <Trans
              i18nKey="wizard.helpNextBody"
              components={{
                0: <strong className="text-otm-text" />,
                1: <strong className="text-otm-text" />,
              }}
            />
          </p>
        </HelpCallout>
      </div>

      <Panel>
        <Stepper
          steps={stepsForStepper}
          currentIndex={step}
          onStepClick={(i) => {
            if (i <= step) setStep(STEP_DEFS[i].id);
          }}
        />
      </Panel>

      {error && (
        <Alert className="whitespace-pre-wrap break-words">{error}</Alert>
      )}

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
              <summary className="cursor-pointer font-medium text-otm-text">{t("wizard.semanticProfile")}</summary>
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
                <Label htmlFor="tprofile">template_semantic_profile</Label>
                <Input
                  id="tprofile"
                  className="mt-1 font-mono text-sm"
                  value={doc.model.template_semantic_profile ?? ""}
                  onChange={(e) =>
                    updateModel({
                      template_semantic_profile: e.target.value.trim() || null,
                    })
                  }
                  placeholder={t("wizard.templateSemanticProfilePlaceholder")}
                />
              </div>
            </details>
            {templateProfile && adaptivePrompts.length > 0 ? (
              <details className="rounded-otm-md border border-otm-mint-500/20 bg-emerald-950/10 px-3 py-2 text-sm" open>
                <summary className="cursor-pointer font-medium text-emerald-900 dark:text-emerald-100">
                  {t("wizard.adaptiveTitle")}
                </summary>
                <p className="mt-2 text-xs text-otm-text-muted">{t("wizard.adaptiveBody")}</p>
                <ul className="mt-3 space-y-3">
                  {adaptivePrompts.map((p) => (
                    <li key={p.id} className="grid gap-1 sm:grid-cols-[1fr_auto] sm:items-center">
                      <div>
                        <p className="text-otm-text">{adaptivePromptLabel(p)}</p>
                        {adaptivePromptHint(p) ? (
                          <p className="text-xs text-otm-text-muted">{adaptivePromptHint(p)}</p>
                        ) : null}
                      </div>
                      <Select
                        className="max-w-[140px] justify-self-end font-mono text-xs"
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
        <Card title={t("wizard.componentsTitle")} subtitle={t("wizard.componentsSubtitle")} variant="glass">
          <div className="space-y-3">
            {doc.components.map((c, idx) => (
              <div
                // Keyed by index, NOT by the edited values: a key derived from `c.id`/`c.name`
                // changes on every keystroke, which unmounts the row mid-edit and drops focus
                // to <body>, so the field accepts one character per click. Every mutation here
                // already addresses rows by index (`updateArrayItem(doc.components, idx, …)`),
                // so the index is the row's real identity.
                key={idx}
                className="grid gap-2 rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 sm:grid-cols-12 sm:items-end"
              >
                <div className="sm:col-span-3">
                  <Label htmlFor={`comp-${idx}-id`}>{t("wizard.id")}</Label>
                  <Input
                    id={`comp-${idx}-id`}
                    value={c.id}
                    aria-invalid={idHasTrailingWhitespace(c.id) || undefined}
                    aria-describedby={
                      idHasTrailingWhitespace(c.id) ? `comp-${idx}-id-trail-hint` : undefined
                    }
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
                </div>
                <div className="sm:col-span-4">
                  <Label htmlFor={`comp-${idx}-name`}>{t("wizard.name")}</Label>
                  <Input
                    id={`comp-${idx}-name`}
                    value={c.name}
                    onChange={(e) => {
                      setComponents(updateArrayItem(doc.components, idx, { ...c, name: e.target.value }));
                    }}
                  />
                </div>
                <div className="sm:col-span-3">
                  <Label htmlFor={`comp-${idx}-kind`}>{t("wizard.type")}</Label>
                  <Select
                    id={`comp-${idx}-kind`}
                    value={c.kind}
                    onChange={(e) => {
                      setComponents(updateArrayItem(doc.components, idx, { ...c, kind: e.target.value }));
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
                    onClick={() => setDocument(removeComponents(doc, [c.id]))}
                  >
                    {t("wizard.remove")}
                  </Button>
                </div>
              </div>
            ))}
            <Button
              variant="secondary"
              onClick={() =>
                setComponents([
                  ...doc.components,
                  {
                    id: `comp_${doc.components.length + 1}`,
                    name: t("wizard.newComponentShort"),
                    kind: "process",
                  },
                ])
              }
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
                key={idx}
                className="grid gap-2 rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 sm:grid-cols-12 sm:items-end"
              >
                <div className="sm:col-span-2">
                  <Label htmlFor={`flow-${idx}-id`}>{t("wizard.flowId")}</Label>
                  <p className="mb-1 text-[11px] text-otm-text-muted">{t("wizard.flowIdRenameHint")}</p>
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
                        updateArrayItem(doc.data_flows, idx, { ...f, from_component: e.target.value }),
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
                    onChange={(e) => {
                      setFlows(updateArrayItem(doc.data_flows, idx, { ...f, name: e.target.value || null }));
                    }}
                  />
                </div>
                <div className="sm:col-span-2">
                  <Button
                    variant="ghost"
                    className="w-full text-red-700 dark:text-red-300"
                    onClick={() => setDocument(removeDataFlows(doc, [f.id]))}
                  >
                    {t("wizard.remove")}
                  </Button>
                </div>
              </div>
            ))}
            <Button
              variant="secondary"
              onClick={() =>
                setFlows([
                  ...doc.data_flows,
                  {
                    id: `flow_${doc.data_flows.length + 1}`,
                    from_component: componentIds[0] ?? "",
                    to_component: componentIds[1] ?? componentIds[0] ?? "",
                    name: null,
                  },
                ])
              }
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
              <summary className="cursor-pointer font-medium text-otm-text">{t("wizard.contextSummary")}</summary>
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
          <Button variant="secondary" onClick={() => setStep((s) => s - 1)}>
            {t("wizard.prev")}
          </Button>
        )}
        {step < STEP_DEFS.length - 1 && (
          <Button onClick={() => void validateAndNext()} disabled={validating}>
            {validating ? t("wizard.validating") : t("wizard.next")}
          </Button>
        )}
        {step === STEP_DEFS.length - 1 && (
          <Link to="/review">
            <Button>{t("wizard.viewDiagram")}</Button>
          </Link>
        )}
      </div>
    </div>
  );
}
