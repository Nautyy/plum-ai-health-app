"use client";

import { useState } from "react";
import type { ClaimResult, ViewMode } from "@/types/claim";
import { formatBreakdownKey, isActionRequired } from "@/types/claim";
import { formatScalar } from "./formatTraceDetails";
import ExecutionTracePanel from "./ExecutionTracePanel";
import {
  buildMemberAmountDetail,
  formatInr,
  hasMemberAmountDetail,
  memberDecisionLabel,
  memberNextSteps,
  memberRejectionReason,
} from "./memberFriendly";
import { getViewCapabilities } from "./viewCapabilities";

const DECISION_STYLES: Record<string, { badge: string; accent: string }> = {
  APPROVED: { badge: "bg-emerald-100 text-emerald-800", accent: "text-emerald-700" },
  PARTIAL: { badge: "bg-amber-100 text-amber-800", accent: "text-amber-700" },
  REJECTED: { badge: "bg-rose-100 text-rose-800", accent: "text-rose-700" },
  MANUAL_REVIEW: { badge: "bg-sky-100 text-sky-800", accent: "text-sky-700" },
  PENDING: { badge: "bg-slate-100 text-slate-700", accent: "text-slate-600" },
};

type Props = {
  result: ClaimResult;
  viewMode: ViewMode;
  onRecordClaim?: (memberNote?: string) => void | Promise<void>;
  recordLoading?: boolean;
  recordError?: string | null;
};

function ActionRequiredBanner({ reason, friendly }: { reason: string; friendly: boolean }) {
  if (friendly) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
        <p className="text-sm font-semibold text-amber-900">We need a bit more from you</p>
        <p className="mt-1 text-sm leading-relaxed text-amber-950">{reason}</p>
        <p className="mt-2 text-xs text-amber-800">
          Update your documents and submit the claim again — it only takes a minute.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">Action required</p>
      <p className="mt-1 text-sm leading-relaxed text-amber-950">{reason}</p>
      <p className="mt-2 text-xs text-amber-800">
        Gatekeeper or document validation failed — review trace below.
      </p>
    </div>
  );
}

function FinancialBreakdown({ breakdown }: { breakdown: Record<string, unknown> }) {
  const entries = Object.entries(breakdown).filter(([, v]) => v !== null && v !== undefined);
  if (entries.length === 0) return null;

  return (
    <section className="rounded-xl border border-border bg-surface-muted p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
        Financial breakdown
      </h3>
      <dl className="mt-3 space-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex justify-between gap-4 text-sm">
            <dt className="text-text-muted">{formatBreakdownKey(key)}</dt>
            <dd className="font-medium text-text">{formatScalar(key, value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function MemberAmountDetails({ result }: { result: ClaimResult }) {
  const detail = buildMemberAmountDetail(result);
  if (!hasMemberAmountDetail(result)) return null;

  return (
    <section className="rounded-xl border border-border bg-surface-muted p-4">
      <h3 className="text-sm font-semibold text-text">How your amount was calculated</h3>
      <p className="mt-1 text-xs text-text-muted">
        Based on your policy rules and the amounts returned from adjudication.
      </p>

      {detail.lineItems.length > 0 && (
        <ul className="mt-4 space-y-2">
          {detail.lineItems.map((item, i) => (
            <li
              key={`${item.description}-${i}`}
              className={`rounded-lg border px-3 py-2.5 text-sm ${
                item.approved
                  ? "border-emerald-200 bg-emerald-50/60"
                  : "border-rose-200 bg-rose-50/40"
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <span className="font-medium text-text">{item.description}</span>
                <span className="font-semibold text-text">{formatInr(item.amount)}</span>
              </div>
              <p className={`mt-1 text-xs ${item.approved ? "text-emerald-800" : "text-rose-800"}`}>
                {item.statusLabel}
                {item.reason ? ` — ${item.reason}` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}

      {detail.narrative.length > 0 && (
        <ul className="mt-4 space-y-1.5 border-t border-border pt-4">
          {detail.narrative.map((line, i) => (
            <li key={i} className="text-sm leading-relaxed text-text">
              {line}
            </li>
          ))}
        </ul>
      )}

      {detail.rows.length > 0 && (
        <dl className="mt-4 space-y-2.5 border-t border-border pt-4">
          {detail.rows.map(({ key, label, value, hint }) => (
            <div key={key} className="flex justify-between gap-4 text-sm">
              <dt className="text-text-muted">
                <span className="block">{label}</span>
                {hint && (
                  <span className="mt-0.5 block text-[11px] font-normal text-text-muted/80">{hint}</span>
                )}
              </dt>
              <dd className={`shrink-0 font-medium ${key === "approved_amount" ? "text-emerald-700" : "text-text"}`}>
                {value}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function LineItemsTable({ items }: { items: NonNullable<ClaimResult["line_item_decisions"]> }) {
  if (!items.length) return null;

  return (
    <section className="overflow-hidden rounded-xl border border-border">
      <h3 className="border-b border-border bg-surface-muted px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-muted">
        Line item decisions
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-muted">
              <th className="px-4 py-2 font-medium">Item</th>
              <th className="px-4 py-2 font-medium">Amount</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={`${item.description}-${i}`} className="border-b border-border last:border-0">
                <td className="px-4 py-2.5">
                  <p className="font-medium text-text">{item.description}</p>
                  {item.rejection_reason && (
                    <p className="mt-0.5 text-xs text-rose-600">{item.rejection_reason}</p>
                  )}
                </td>
                <td className="px-4 py-2.5 whitespace-nowrap">
                  ₹{item.amount.toLocaleString("en-IN")}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      item.approved
                        ? "bg-emerald-100 text-emerald-800"
                        : item.approved === false
                          ? "bg-rose-100 text-rose-800"
                          : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {item.approved ? "Approved" : item.approved === false ? "Rejected" : "Review"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function WhatHappensNext({ text }: { text: string }) {
  return (
    <section className="rounded-xl border border-plum-brand/20 bg-plum-50 px-4 py-3">
      <p className="text-sm font-semibold text-plum-900">What happens next</p>
      <p className="mt-1 text-sm leading-relaxed text-plum-950">{text}</p>
    </section>
  );
}

function SubmissionAudit({ result }: { result: ClaimResult }) {
  const submission = result.submission;
  const breakdown = result.financial_breakdown ?? {};
  if (!submission && !result.submitted_at) return null;

  const documents = (submission?.documents as Array<{ file_name?: string; actual_type?: string }>) ?? [];
  const submittedAt = result.submitted_at
    ? new Date(result.submitted_at).toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <section className="rounded-xl border border-border bg-surface-muted p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
        Submission audit
      </h3>
      <dl className="mt-3 space-y-2 text-sm">
        {submittedAt && (
          <div className="flex justify-between gap-4">
            <dt className="text-text-muted">Adjudicated</dt>
            <dd className="font-medium text-text">{submittedAt}</dd>
          </div>
        )}
        {result.ops_approved_at && (
          <div className="flex justify-between gap-4">
            <dt className="text-text-muted">Ops approved</dt>
            <dd className="font-medium text-emerald-700">
              {new Date(result.ops_approved_at).toLocaleString("en-IN", {
                day: "numeric",
                month: "short",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </dd>
          </div>
        )}
        {result.ops_approval_note && (
          <div>
            <dt className="text-text-muted">Ops approval note</dt>
            <dd className="mt-1 whitespace-pre-wrap font-medium text-text">{result.ops_approval_note}</dd>
          </div>
        )}
        {result.member_note && (
          <div>
            <dt className="text-text-muted">Member note</dt>
            <dd className="mt-1 whitespace-pre-wrap font-medium text-text">{result.member_note}</dd>
          </div>
        )}
        {submission?.member_id != null && (
          <div className="flex justify-between gap-4">
            <dt className="text-text-muted">Employee ID</dt>
            <dd className="font-medium text-text">{String(submission.member_id)}</dd>
          </div>
        )}
        {submission?.claim_for != null && (
          <div className="flex justify-between gap-4">
            <dt className="text-text-muted">Claim for</dt>
            <dd className="font-medium text-text">{String(submission.claim_for)}</dd>
          </div>
        )}
        {(submission?.patient_name as string | undefined) && (
          <div className="flex justify-between gap-4">
            <dt className="text-text-muted">Patient</dt>
            <dd className="font-medium text-text">{String(submission.patient_name)}</dd>
          </div>
        )}
        {submission?.policy_id != null && (
          <div className="flex justify-between gap-4">
            <dt className="text-text-muted">Policy</dt>
            <dd className="font-medium text-text">{String(submission.policy_id)}</dd>
          </div>
        )}
        {submission?.claim_category != null && (
          <div className="flex justify-between gap-4">
            <dt className="text-text-muted">Category</dt>
            <dd className="font-medium text-text">{String(submission.claim_category)}</dd>
          </div>
        )}
        {submission?.claimed_amount != null && (
          <div className="flex justify-between gap-4">
            <dt className="text-text-muted">Claimed (form)</dt>
            <dd className="font-medium text-text">
              ₹{Number(submission.claimed_amount).toLocaleString("en-IN")}
            </dd>
          </div>
        )}
        {typeof breakdown.document_total_amount === "number" && (
          <div className="flex justify-between gap-4">
            <dt className="text-text-muted">Document total (OCR)</dt>
            <dd className="font-medium text-text">
              ₹{Number(breakdown.document_total_amount).toLocaleString("en-IN")}
            </dd>
          </div>
        )}
        {typeof breakdown.claimed_amount === "number" &&
          typeof breakdown.document_total_amount === "number" &&
          breakdown.claimed_amount !== breakdown.document_total_amount && (
            <div className="flex justify-between gap-4">
              <dt className="text-text-muted">Eligible for policy</dt>
              <dd className="font-medium text-text">
                ₹{Number(breakdown.claimed_amount).toLocaleString("en-IN")}
              </dd>
            </div>
          )}
      </dl>
      {documents.length > 0 && (
        <div className="mt-3 border-t border-border pt-3">
          <p className="text-xs font-medium text-text-muted">Documents submitted</p>
          <ul className="mt-2 space-y-1">
            {documents.map((doc, i) => (
              <li key={`${doc.file_name ?? i}-${i}`} className="text-sm text-text">
                {doc.file_name ?? "Document"} · {doc.actual_type ?? "unknown type"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function SubmitClaimBanner({
  recorded,
  loading,
  error,
  onSubmit,
}: {
  recorded: boolean;
  loading?: boolean;
  error?: string | null;
  onSubmit?: (memberNote?: string) => void | Promise<void>;
}) {
  const [memberNote, setMemberNote] = useState("");

  if (recorded) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
        <p className="text-sm font-semibold text-emerald-900">Claim submitted to Plum</p>
        <p className="mt-1 text-sm leading-relaxed text-emerald-800">
          Our claims team can review this claim in the ops console and process settlement.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-plum-brand/25 bg-plum-50 px-4 py-4">
      <p className="text-sm font-semibold text-plum-900">Submit this claim</p>
      <p className="mt-1 text-sm leading-relaxed text-plum-950">
        The decision above is a preview. When you submit, we send it to Plum for processing and
        your claims team can review it.
      </p>
      <details className="mt-3 group">
        <summary className="cursor-pointer text-sm font-medium text-plum-800 marker:content-none [&::-webkit-details-marker]:hidden">
          <span className="inline-flex items-center gap-1.5">
            <span className="text-plum-brand transition group-open:rotate-90">›</span>
            Add a note for the ops team (optional)
          </span>
        </summary>
        <textarea
          className="mt-2 w-full rounded-xl border border-border bg-white px-3 py-2.5 text-sm text-text outline-none transition focus:border-plum-brand/50 focus:ring-2 focus:ring-plum-brand/10"
          rows={3}
          value={memberNote}
          onChange={(e) => setMemberNote(e.target.value)}
          placeholder="Anything you'd like the claims team to know…"
          maxLength={1000}
        />
      </details>
      <button
        type="button"
        onClick={() => onSubmit?.(memberNote.trim() || undefined)}
        disabled={loading || !onSubmit}
        className="mt-3 w-full rounded-xl bg-plum-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-plum-brand-dark disabled:opacity-50"
      >
        {loading ? "Submitting…" : "Submit claim to Plum"}
      </button>
      {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}
    </div>
  );
}

export default function DecisionCard({
  result,
  viewMode,
  onRecordClaim,
  recordLoading,
  recordError,
}: Props) {
  const caps = getViewCapabilities(viewMode);
  const style = DECISION_STYLES[result.decision] ?? DECISION_STYLES.PENDING;
  const confidence = Math.round(result.confidence_score * 100);
  const actionRequired = isActionRequired(result);
  const breakdown = result.financial_breakdown ?? {};
  const lineItems = result.line_item_decisions ?? [];
  const nextSteps = caps.showWhatHappensNext ? memberNextSteps(result) : null;
  const decisionLabel = caps.useFriendlyLabels
    ? memberDecisionLabel(result.decision)
    : result.decision.replace("_", " ");
  const isRecorded = Boolean(result.recorded || result.submitted_at);
  const isOpsView = viewMode === "ops";
  const awaitingOpsApproval = isOpsView && !result.ops_approved && result.decision !== "PENDING";

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm ring-1 ring-black/3">
      <div className="border-b border-border bg-surface-muted px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
              {caps.useFriendlyLabels
                ? "Your claim result"
                : result.ops_approved
                  ? "Final ops decision"
                  : "AI recommendation"}
            </p>
            <p className="text-lg font-semibold text-text">#{result.claim_id}</p>
            {isOpsView && !result.ops_approved && (
              <p className="mt-0.5 text-xs text-amber-700">Pending human approval for settlement</p>
            )}
            {isOpsView && result.ops_approved && (
              <p className="mt-0.5 text-xs text-emerald-700">Signed off for settlement</p>
            )}
            {caps.useFriendlyLabels && (
              <p className="mt-0.5 text-xs text-text-muted">Your claim reference number</p>
            )}
          </div>
          <div className="flex flex-col items-end gap-1">
          <span className={`rounded-full px-3 py-1 text-sm font-semibold ${style.badge}`}>
            {decisionLabel}
          </span>
          {awaitingOpsApproval && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800">
              Awaiting HITL
            </span>
          )}
          </div>
        </div>
      </div>

      <div className="space-y-4 p-5">
        {actionRequired && (
          <ActionRequiredBanner reason={result.reason} friendly={caps.useFriendlyLabels} />
        )}

        {result.approved_amount > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
              {caps.useFriendlyLabels
                ? "You'll receive"
                : result.ops_approved
                  ? "Approved amount"
                  : "AI recommended payout"}
            </p>
            <p className={`text-3xl font-bold ${style.accent}`}>
              ₹{result.approved_amount.toLocaleString("en-IN")}
            </p>
          </div>
        )}

        {!actionRequired && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
              {caps.useFriendlyLabels ? "In plain English" : "Decision rationale"}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-text">{result.reason}</p>
          </div>
        )}

        {caps.showConfidence && (
          <div>
            <div className="mb-1 flex items-center justify-between text-xs text-text-muted">
              <span>Confidence</span>
              <span className="font-semibold text-plum-brand">{confidence}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-border">
              <div
                className="h-full rounded-full bg-plum-brand transition-all"
                style={{ width: `${confidence}%` }}
              />
            </div>
            {result.execution_trace.some((e) => e.degraded) && (
              <p className="mt-1.5 text-xs text-amber-700">
                Confidence reduced due to degraded steps in the trace below.
              </p>
            )}
          </div>
        )}

        {result.rejection_reasons && result.rejection_reasons.length > 0 && (
          <div className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">
            <p className="font-medium">
              {caps.useFriendlyLabels ? "Why this wasn't approved" : "Rejection reasons"}
            </p>
            <ul className="mt-1 list-inside list-disc space-y-0.5">
              {result.rejection_reasons.map((reason) => (
                <li key={reason}>
                  {caps.useFriendlyLabels ? memberRejectionReason(reason) : reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {caps.showMemberPayoutSummary && caps.useFriendlyLabels && (
          <MemberAmountDetails result={result} />
        )}

        {nextSteps && <WhatHappensNext text={nextSteps} />}

        {caps.showSubmitClaimButton && (
          <SubmitClaimBanner
            recorded={isRecorded}
            loading={recordLoading}
            error={recordError}
            onSubmit={onRecordClaim}
          />
        )}

        {caps.showSubmissionAudit && <SubmissionAudit result={result} />}

        {caps.showFinancialBreakdown && <FinancialBreakdown breakdown={breakdown} />}

        {caps.showLineItems && lineItems.length > 0 && <LineItemsTable items={lineItems} />}

        <ExecutionTracePanel
          trace={result.execution_trace}
          viewMode={viewMode}
          defaultOpen={!caps.traceCollapsedByDefault}
        />
      </div>
    </div>
  );
}
