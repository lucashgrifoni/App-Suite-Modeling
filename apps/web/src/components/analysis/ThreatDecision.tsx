import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import type { HeuristicThreat } from "../../types/api";
import { isDeclaredThreat, type DeclaredThreat } from "../../types/document";
import { useSession } from "../../context/SessionContext";
import { useToast } from "../../context/ToastContext";
import { Button } from "../ui/Button";
import { Checkbox } from "../ui/Checkbox";
import { Input } from "../ui/Input";
import { Label } from "../ui/Label";
import { Select } from "../ui/Select";

const statuses = [
  "new",
  "triaged",
  "in_progress",
  "mitigated",
  "accepted_risk",
  "false_positive",
  "wont_fix",
] as const;
type Status = (typeof statuses)[number];

function closingOutcome(status?: string) {
  if (status === "mitigated") return "risk_closed";
  if (status === "false_positive") return "false_positive_confirmed";
  return undefined;
}

/** A human decision is part of the canonical model, including after export or restore. */
export function ThreatDecision({
  suggestion,
  existing,
  onSelectDeclared,
}: Readonly<{
  suggestion?: HeuristicThreat;
  existing?: DeclaredThreat;
  onSelectDeclared?: (id: string) => void;
}>) {
  const { t } = useTranslation();
  const { document, setDocument } = useSession();
  const toast = useToast();
  const fieldId = useId();
  const [editing, setEditing] = useState(false);
  const [status, setStatus] = useState<string>(
    existing?.treatment_status ?? (existing ? "new" : "triaged"),
  );
  const [notes, setNotes] = useState(existing?.treatment_notes ?? "");
  const savedReviewDate = existing?.metadata?.risk_review_date;
  const initialReviewDate = typeof savedReviewDate === "string" ? savedReviewDate : "";
  const [assignee, setAssignee] = useState(existing?.assignee ?? "");
  const [reviewDate, setReviewDate] = useState(initialReviewDate);
  const savedVerification = existing?.metadata?.treatment_verification;
  const verification = savedVerification && typeof savedVerification === "object"
    ? savedVerification as Record<string, unknown>
    : {};
  const savedOutcome = closingOutcome(existing?.treatment_status);
  const initialReference = savedOutcome && typeof verification.reference === "string" ? verification.reference : "";
  const initialConfirmed = Boolean(savedOutcome && verification.outcome === savedOutcome);
  const [reference, setReference] = useState(initialReference);
  const [confirmed, setConfirmed] = useState(initialConfirmed);
  const outcome = closingOutcome(status);
  const id = existing?.id ?? suggestion?.id;
  const conflict =
    !existing &&
    document?.threats.some(
      (value) => value && typeof value === "object" && "id" in value && value.id === id,
    );

  function save() {
    if (!document || !id || conflict || !statuses.includes(status as Status)) return;
    if (outcome && confirmed && (!reference.trim() || (status === "false_positive" && !notes.trim()))) return;
    const decision = { treatment_status: status, treatment_notes: notes.trim() || null };
    const metadata: Record<string, unknown> = existing
      ? { ...existing.metadata }
      : { source: "otm_threat_engine", engine_heuristic: true };
    const accepted = status === "accepted_risk";
    if (accepted) {
      if (reviewDate) metadata.risk_review_date = reviewDate;
      else delete metadata.risk_review_date;
    }
    if (outcome && (status !== existing?.treatment_status || reference !== initialReference || confirmed !== initialConfirmed)) {
      const evidence = { ...verification };
      if (reference.trim()) evidence.reference = reference.trim();
      else delete evidence.reference;
      if (confirmed) evidence.outcome = outcome;
      else if (status !== existing?.treatment_status || evidence.outcome === outcome) delete evidence.outcome;
      if (Object.keys(evidence).length) metadata.treatment_verification = evidence;
      else delete metadata.treatment_verification;
    }
    const review = accepted ? { assignee: assignee.trim() || null } : {};
    if (existing) {
      setDocument({
        ...document,
        threats: document.threats.map((value) =>
          isDeclaredThreat(value) && value.id === id ? { ...value, ...decision, ...review, metadata } : value,
        ),
      });
    } else if (suggestion) {
      const {
        title,
        description,
        stride,
        target_component_id,
        target_data_flow_id,
        target_asset_id,
        risk,
        framework_refs,
      } = suggestion;
      setDocument({
        ...document,
        threats: [
          ...document.threats,
          {
            id,
            title,
            description,
            stride,
            target_component_id,
            target_data_flow_id,
            target_asset_id,
            risk,
            framework_refs: framework_refs ?? [],
            metadata,
            ...decision,
            ...review,
          },
        ],
      });
    }
    onSelectDeclared?.(id);
    setEditing(false);
    toast.success(t("work.savedDecision"));
  }
  if (conflict) {
    const editable = document?.threats.some((value) => isDeclaredThreat(value) && value.id === id);
    return editable && id && onSelectDeclared ? (
      <a className="work-text-link" href="#declared-decisions" onClick={() => onSelectDeclared(id)}>
        {t("work.viewDecision")}
      </a>
    ) : (
      <p className="work-muted">{t("work.idConflict")}</p>
    );
  }
  if (!editing)
    return (
      <div className="mt-3">
        {existing && (
          <p className="work-muted">
            {t(`work.status.${existing.treatment_status ?? "new"}`, {
              defaultValue: existing.treatment_status,
            })}
            {existing.treatment_notes ? ` · ${existing.treatment_notes}` : ""}
          </p>
        )}
        {initialReference && (
          <p className="mt-2 break-all text-sm">
            <span className="font-medium">{t("work.verificationReference")} </span>{initialReference}
          </p>
        )}
        {existing?.treatment_status === "accepted_risk" && (existing.assignee || initialReviewDate) && (
          <dl className="mt-2 grid gap-1 text-sm">
            {existing.assignee && (
              <div>
                <dt className="inline font-medium">{t("work.riskOwner")} </dt>
                <dd className="inline">{existing.assignee}</dd>
              </div>
            )}
            {initialReviewDate && (
              <div>
                <dt className="inline font-medium">{t("work.riskReviewDate")} </dt>
                <dd className="inline">{initialReviewDate}</dd>
              </div>
            )}
          </dl>
        )}
        <Button
          className="mt-2"
          variant={existing ? "secondary" : "primary"}
          onClick={() => setEditing(true)}
        >
          {t(existing ? "work.editDecision" : "work.recordDecision")}
        </Button>
      </div>
    );
  return (
    <form
      className="mt-3 space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
    >
      <div>
        <Label htmlFor={fieldId}>{t("work.treatment")}</Label>
        <Select id={fieldId} value={status} onChange={(e) => {
          const next = e.target.value;
          setStatus(next);
          setReference(next === existing?.treatment_status ? initialReference : "");
          setConfirmed(next === existing?.treatment_status && initialConfirmed);
        }}>
          {statuses.map((s) => (
            <option value={s} key={s}>
              {t(`work.status.${s}`)}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor={fieldId + "-note"}>{t("work.notes")}</Label>
        <textarea
          id={fieldId + "-note"}
          rows={3}
          className="w-full rounded-otm-md border border-otm-border-control bg-otm-surface-1 p-2 text-sm"
          value={notes}
          required={status === "false_positive" && confirmed}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>
      {status === "accepted_risk" && (
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor={fieldId + "-owner"}>{t("work.riskOwner")}</Label>
            <Input id={fieldId + "-owner"} value={assignee} onChange={(e) => setAssignee(e.target.value)} />
          </div>
          <div>
            <Label htmlFor={fieldId + "-review"}>{t("work.riskReviewDate")}</Label>
            <Input
              id={fieldId + "-review"}
              type="date"
              min="0001-01-01"
              max="9999-12-31"
              value={reviewDate}
              onChange={(e) => setReviewDate(e.target.value)}
            />
          </div>
        </div>
      )}
      {outcome && (
        <div className="space-y-2">
          <Label htmlFor={fieldId + "-evidence"}>{t("work.verificationReference")}</Label>
          <Input
            id={fieldId + "-evidence"}
            value={reference}
            required={confirmed}
            onChange={(event) => setReference(event.target.value)}
          />
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
            {t(status === "mitigated" ? "work.confirmMitigation" : "work.confirmFalsePositive")}
          </label>
          {status === "mitigated" && <p className="work-muted">{t("work.mitigationEvidenceHint")}</p>}
        </div>
      )}
      <p className="text-xs text-otm-text-muted">{t("work.rerunHint")}</p>
      <div className="flex flex-wrap gap-2">
        <Button type="submit">{t("work.saveDecision")}</Button>
        <Button
          variant="ghost"
          onClick={() => {
            setStatus(existing?.treatment_status ?? (existing ? "new" : "triaged"));
            setNotes(existing?.treatment_notes ?? "");
            setAssignee(existing?.assignee ?? "");
            setReviewDate(initialReviewDate);
            setReference(initialReference);
            setConfirmed(initialConfirmed);
            setEditing(false);
          }}
        >
          {t("work.cancel")}
        </Button>
      </div>
    </form>
  );
}

export function DeclaredDecisions({
  selected,
  onSelect,
}: Readonly<{ selected: string; onSelect: (id: string) => void }>) {
  const { document } = useSession();
  const { t } = useTranslation();
  const threats = document?.threats.filter(isDeclaredThreat) ?? [];
  const threat = threats.find((row) => row.id === selected) ?? threats[0];
  if (!threat) return null;
  return (
    <section id="declared-decisions" tabIndex={-1} className="work-panel">
      <h2 className="work-detail-title">{t("work.declared")}</h2>
      <Label htmlFor="declared-threat">{t("work.declaredThreat")}</Label>
      <Select id="declared-threat" value={threat.id} onChange={(e) => onSelect(e.target.value)}>
        {threats.map((h) => (
          <option key={h.id} value={h.id}>
            {h.title} · {h.id}
          </option>
        ))}
      </Select>
      <ThreatDecision key={threat.id} existing={threat} />
    </section>
  );
}
