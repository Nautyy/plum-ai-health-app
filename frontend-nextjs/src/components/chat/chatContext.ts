import type { ClaimResult } from "@/types/claim";

/** Lightweight claim context for chat — no base64 or full trace payloads. */
export function buildChatClaimContext(result: ClaimResult): Record<string, unknown> {
  const submission = result.submission as Record<string, unknown> | undefined;
  const docs = (submission?.documents as Array<Record<string, unknown>>) ?? [];

  return {
    claim_id: result.claim_id,
    decision: result.decision,
    approved_amount: result.approved_amount,
    reason: result.reason,
    member_reason: result.member_reason,
    confidence_score: result.confidence_score,
    rejection_reasons: result.rejection_reasons,
    line_item_decisions: result.line_item_decisions,
    financial_breakdown: result.financial_breakdown,
    recorded: result.recorded,
    submitted_at: result.submitted_at,
    ops_approved: result.ops_approved,
    ops_approved_at: result.ops_approved_at,
    member_note: result.member_note,
    submission: submission
      ? {
          member_id: submission.member_id,
          claim_category: submission.claim_category,
          treatment_date: submission.treatment_date,
          claimed_amount: submission.claimed_amount,
          documents: docs.map((doc) => ({
            file_name: doc.file_name,
            actual_type: doc.actual_type,
          })),
        }
      : undefined,
  };
}

export function parseChatError(raw: string): string {
  if (raw.includes("Request too large") || raw.includes("rate_limit_exceeded")) {
    return "The claim details were too large to send to the assistant. This is fixed on the server — please restart the backend and try again.";
  }
  try {
    const outer = JSON.parse(raw) as { message?: string };
    if (typeof outer.message === "string") {
      try {
        const inner = JSON.parse(outer.message) as { error?: { message?: string } };
        if (inner.error?.message) return inner.error.message;
      } catch {
        return outer.message;
      }
    }
  } catch {
    /* not JSON */
  }
  return raw.length > 280 ? `${raw.slice(0, 280)}…` : raw;
}
