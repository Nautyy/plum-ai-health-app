import type { ClaimResult, TraceEntry } from "@/types/claim";
import { filterTraceForView } from "@/types/claim";

const STEP_LABELS: Record<string, string> = {
  gatekeeper_agent: "Documents verified",
  submission_validator: "Details verified",
  policy_engine: "Policy check",
  decision_consolidator: "Final amount",
};

const STATUS_LABELS: Record<string, string> = {
  SUCCESS: "Verified",
  APPROVED: "Approved",
  FAILED: "Issue found",
  REJECTED: "Not covered",
  PARTIAL: "Partially approved",
  MANUAL_REVIEW: "Under review",
  PENDING: "Pending",
  DEGRADED: "Reviewed",
};

const BREAKDOWN_LABELS: Record<string, string> = {
  submitted_claimed_amount: "Amount you entered",
  document_total_amount: "Total from your documents",
  claimed_amount: "Eligible amount (after line items)",
  approved_amount: "You'll receive",
  copay_amount: "Co-pay (your share)",
  copay_percent: "Co-pay rate",
  network_discount_amount: "Network hospital discount",
  network_discount_percent: "Network discount rate",
  after_network_discount: "After network discount",
  deductible: "Deductible applied",
  sub_limit: "Category limit",
  remaining_limit: "Remaining limit",
  annual_opd_remaining: "Annual OPD balance left",
  total_deducted: "Total deductions",
};

/** Keys that reduce the payout — rendered as deductions in member explanations */
const PAYOUT_DEDUCTIONS: Array<{ amountKey: string; percentKey?: string }> = [
  { amountKey: "network_discount_amount", percentKey: "network_discount_percent" },
  { amountKey: "copay_amount", percentKey: "copay_percent" },
  { amountKey: "deductible" },
  { amountKey: "total_deducted" },
];

const REJECTION_LABELS: Record<string, string> = {
  MEMBER_NOT_FOUND:
    "The member ID you entered doesn't match anyone on your company's health policy. Double-check your employee ID or contact HR.",
  PRIMARY_MEMBER_NOT_FOUND:
    "Your dependent profile is linked to a primary member we couldn't verify. Please contact Plum support.",
  CATEGORY_NOT_COVERED:
    "This type of expense isn't covered under your current policy.",
  PER_CLAIM_EXCEEDED: "The claim amount is above the limit allowed for a single claim.",
  NO_COVERED_ITEMS: "None of the items on your bill are covered under your policy.",
  INVALID_TREATMENT_DATE:
    "The treatment date is missing or invalid. Please use a valid date (YYYY-MM-DD) and submit again.",
  INVALID_CLAIM_AMOUNT: "Please enter a claim amount greater than zero.",
  TREATMENT_DATE_MISMATCH:
    "The treatment date you entered doesn't match the date on your uploaded documents. Please correct the date or upload matching documents.",
  DOCUMENT_DATE_INCONSISTENT:
    "Your documents show different treatment dates. Please upload documents from the same visit.",
  HOSPITAL_NAME_MISMATCH:
    "The hospital name you entered doesn't match the hospital on your bill. Please correct it or upload the matching bill.",
  WAITING_PERIOD:
    "This treatment falls within a waiting period on your policy. You may be eligible after the waiting period ends.",
  PRE_AUTH_MISSING:
    "This claim needs pre-authorization from Plum before the treatment. Please obtain approval and resubmit.",
  EXCLUDED_CONDITION: "This treatment isn't covered under your policy exclusions.",
  POLICY_EVALUATION_ERROR:
    "We couldn't fully process your claim automatically. Our team will review it manually.",
};

export function memberRejectionReason(code: string): string {
  if (REJECTION_LABELS[code]) return REJECTION_LABELS[code];
  if (/^[A-Z0-9_]+$/.test(code)) {
    return code
      .toLowerCase()
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return code;
}

export function memberDecisionLabel(decision: string): string {
  switch (decision) {
    case "APPROVED":
      return "Approved";
    case "PARTIAL":
      return "Partially approved";
    case "REJECTED":
      return "Not approved";
    case "MANUAL_REVIEW":
      return "Under review";
    case "PENDING":
      return "Incomplete";
    default:
      return decision.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export function memberTraceStepLabel(step: string): string {
  return STEP_LABELS[step] ?? step.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function memberTraceStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status.replace(/_/g, " ").toLowerCase();
}

export function memberBreakdownLabel(key: string): string {
  return BREAKDOWN_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function memberTraceMessage(step: string, message: string): string {
  if (step === "gatekeeper_agent") {
    if (/required documents|readable/i.test(message)) {
      return "We received the documents we need for this claim.";
    }
    if (/member id mismatch/i.test(message)) {
      return message;
    }
    if (/missing|failed|mismatch/i.test(message)) {
      return message;
    }
  }

  if (step === "policy_engine") {
    if (/co-pay|copay/i.test(message)) return message;
    return "We checked your claim against your health policy.";
  }

  if (step === "submission_validator") {
    if (/date|hospital|match|documents/i.test(message)) return message;
    return "We verified your form details against your documents.";
  }

  if (step === "decision_consolidator") {
    if (/co-pay|copay|₹|final/i.test(message)) return message;
    return "Your payout amount has been confirmed.";
  }

  return message;
}

/** Drop duplicate final step when it repeats the policy step message */
export function getMemberVisibleTrace(trace: TraceEntry[]): TraceEntry[] {
  const filtered = filterTraceForView(trace, "member");

  return filtered.filter((entry, index, list) => {
    if (entry.step !== "decision_consolidator") return true;

    const policyStep = list.find((e) => e.step === "policy_engine");
    if (policyStep && policyStep.message === entry.message) return false;

    const earlierSame = list
      .slice(0, index)
      .some((e) => e.message === entry.message && e.step !== "gatekeeper_agent");
    return !earlierSame;
  });
}

export function memberNextSteps(result: ClaimResult): string | null {
  const amount = result.approved_amount;

  switch (result.decision) {
    case "APPROVED":
      return amount > 0
        ? `Payment of ₹${amount.toLocaleString("en-IN")} will be sent to your registered bank account within 5–7 business days.`
        : "Your claim is approved. Payment details will follow your policy terms.";
    case "PARTIAL":
      return amount > 0
        ? `Payment of ${formatInr(amount)} will be sent to your registered bank account within 5–7 business days.`
        : "Part of your claim was approved. Ask me if you'd like help understanding what was covered.";
    case "REJECTED":
      if (result.rejection_reasons?.includes("MEMBER_NOT_FOUND")) {
        return "Check your member ID matches what's on your Plum policy, then submit again. If you're unsure, ask your HR team or contact Plum support.";
      }
      return "If you think this is a mistake, you can ask me to explain further or contact Plum support to appeal.";
    case "MANUAL_REVIEW":
      return "Our claims team is reviewing your submission. We'll update you within 2–3 business days — no action needed from you right now.";
    case "PENDING":
      if (result.rejection_reasons?.includes("INVALID_TREATMENT_DATE")) {
        return "Enter a valid treatment date (YYYY-MM-DD) and submit your claim again.";
      }
      if (result.rejection_reasons?.includes("INVALID_CLAIM_AMOUNT")) {
        return "Enter a valid claim amount greater than zero and submit again.";
      }
      if (
        result.rejection_reasons?.includes("TREATMENT_DATE_MISMATCH") ||
        result.rejection_reasons?.includes("DOCUMENT_DATE_INCONSISTENT")
      ) {
        return "Update the treatment date to match your documents, or upload documents for the date you entered, then submit again.";
      }
      if (result.rejection_reasons?.includes("HOSPITAL_NAME_MISMATCH")) {
        return "Update the hospital name to match your bill, or upload the correct bill, then submit again.";
      }
      return "Please fix the issue mentioned above and submit your claim again with the correct documents.";
    default:
      return null;
  }
}

export function formatInr(amount: number): string {
  return `₹${amount.toLocaleString("en-IN")}`;
}

export type MemberLineItemView = {
  description: string;
  amount: number;
  approved: boolean;
  statusLabel: string;
  reason?: string;
};

export type MemberAmountDetail = {
  narrative: string[];
  lineItems: MemberLineItemView[];
  rows: Array<{ key: string; label: string; value: string; hint?: string }>;
};

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function resolveSubmittedAmount(
  result: ClaimResult,
  breakdown: Record<string, unknown>
): number | null {
  const fromBreakdown = asNumber(breakdown.submitted_claimed_amount);
  if (fromBreakdown != null) return fromBreakdown;
  const submission = result.submission as { claimed_amount?: number } | undefined;
  return asNumber(submission?.claimed_amount);
}

function resolveStartingAmount(result: ClaimResult, breakdown: Record<string, unknown>): number | null {
  const fromDocuments = asNumber(breakdown.document_total_amount);
  if (fromDocuments != null) return fromDocuments;

  const items = result.line_item_decisions ?? [];
  if (items.length > 0) {
    return items.reduce((sum, item) => sum + item.amount, 0);
  }
  const fromBreakdown = asNumber(breakdown.claimed_amount);
  if (fromBreakdown != null) return fromBreakdown;
  return resolveSubmittedAmount(result, breakdown);
}

function hintForBreakdownKey(key: string): string | undefined {
  if (key === "submitted_claimed_amount") return "Amount entered on the claim form";
  if (key === "document_total_amount") return "Total read from uploaded bill or prescription";
  if (key === "claimed_amount") return "Amount used for policy calculation after line-item review";
  if (key === "approved_amount") return "Final amount after all policy adjustments";
  if (key.endsWith("_percent")) return undefined;
  if (PAYOUT_DEDUCTIONS.some((d) => d.amountKey === key)) return "Policy adjustment";
  if (key.includes("limit") || key.includes("remaining")) return "Policy limit information";
  return undefined;
}

function formatBreakdownValue(key: string, raw: unknown): string {
  if (typeof raw === "number") {
    if (key.includes("percent") || key.endsWith("_rate")) {
      return raw <= 1 ? `${Math.round(raw * 100)}%` : `${raw}%`;
    }
    return formatInr(raw);
  }
  return String(raw);
}

export function buildMemberLineItems(result: ClaimResult): MemberLineItemView[] {
  return (result.line_item_decisions ?? []).map((item) => ({
    description: item.description,
    amount: item.amount,
    approved: Boolean(item.approved),
    statusLabel: item.approved ? "Approved" : "Not approved",
    reason: item.approved
      ? undefined
      : item.rejection_reason
        ? memberRejectionReason(item.rejection_reason)
        : "Not covered under your policy.",
  }));
}

/** Build member-facing amount detail purely from adjudication result fields */
export function buildMemberAmountDetail(result: ClaimResult): MemberAmountDetail {
  const breakdown = result.financial_breakdown ?? {};
  const lineItems = buildMemberLineItems(result);
  const narrative: string[] = [];

  const submittedAmount = resolveSubmittedAmount(result, breakdown);
  const documentTotal = asNumber(breakdown.document_total_amount);
  if (submittedAmount != null) {
    narrative.push(`Amount you entered on the form: ${formatInr(submittedAmount)}.`);
  }
  if (documentTotal != null && submittedAmount != null && documentTotal !== submittedAmount) {
    narrative.push(
      `Total read from your documents: ${formatInr(documentTotal)}. We used the document amounts for this decision.`
    );
  } else if (documentTotal != null && submittedAmount == null) {
    narrative.push(`Total read from your documents: ${formatInr(documentTotal)}.`);
  }

  const startingAmount = resolveStartingAmount(result, breakdown);
  if (lineItems.length > 0) {
    narrative.push(`Your bill has ${lineItems.length} line item(s).`);
  } else if (
    startingAmount != null &&
    submittedAmount == null &&
    documentTotal == null
  ) {
    narrative.push(`Starting amount: ${formatInr(startingAmount)}.`);
  } else if (
    startingAmount != null &&
    documentTotal != null &&
    submittedAmount != null &&
    documentTotal !== submittedAmount
  ) {
    narrative.push(`Bill total used for review: ${formatInr(startingAmount)}.`);
  }

  const eligibleAmount = asNumber(breakdown.claimed_amount);
  if (
    eligibleAmount != null &&
    documentTotal != null &&
    eligibleAmount !== documentTotal
  ) {
    narrative.push(`Amount eligible for reimbursement after review: ${formatInr(eligibleAmount)}.`);
  } else if (
    eligibleAmount != null &&
    submittedAmount != null &&
    documentTotal == null &&
    eligibleAmount !== submittedAmount
  ) {
    narrative.push(`Amount eligible for reimbursement: ${formatInr(eligibleAmount)}.`);
  }

  for (const { amountKey, percentKey } of PAYOUT_DEDUCTIONS) {
    const amount = asNumber(breakdown[amountKey]);
    if (amount == null || amount <= 0) continue;
    const pct = percentKey ? asNumber(breakdown[percentKey]) : null;
    const label = memberBreakdownLabel(amountKey);
    narrative.push(
      `${label}${pct != null ? ` (${pct}%)` : ""}: −${formatInr(amount)}.`
    );
  }

  const finalAmount =
    asNumber(breakdown.approved_amount) ?? (result.approved_amount > 0 ? result.approved_amount : null);
  if (finalAmount != null) {
    narrative.push(`Final reimbursement: ${formatInr(finalAmount)}.`);
  }

  const rowPriority = [
    "submitted_claimed_amount",
    "document_total_amount",
    "claimed_amount",
    ...PAYOUT_DEDUCTIONS.map((d) => d.amountKey),
    "after_network_discount",
    "annual_opd_remaining",
    "sub_limit",
    "remaining_limit",
    "total_deducted",
    "approved_amount",
  ];

  const rows = Object.entries(breakdown)
    .filter(([, value]) => value !== null && value !== undefined)
    .filter(([key]) => {
      if (!key.endsWith("_percent")) return true;
      const amountKey = key.replace("_percent", "_amount");
      return asNumber(breakdown[amountKey]) == null;
    })
    .map(([key, value]) => ({
      key,
      label: memberBreakdownLabel(key),
      value: formatBreakdownValue(key, value),
      hint: hintForBreakdownKey(key),
      order: rowPriority.indexOf(key),
    }))
    .sort((a, b) => (a.order === -1 ? 99 : a.order) - (b.order === -1 ? 99 : b.order))
    .map(({ key, label, value, hint }) => ({ key, label, value, hint }));

  return { narrative, lineItems, rows };
}

export function hasMemberAmountDetail(result: ClaimResult): boolean {
  const breakdown = result.financial_breakdown ?? {};
  return (
    result.approved_amount > 0 ||
    (result.line_item_decisions?.length ?? 0) > 0 ||
    Object.keys(breakdown).length > 0
  );
}
