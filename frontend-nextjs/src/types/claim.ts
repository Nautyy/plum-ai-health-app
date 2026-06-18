export type TraceEntry = {
  step: string;
  status: string;
  message: string;
  details?: Record<string, unknown>;
  degraded?: boolean;
};

export type LineItemDecision = {
  description: string;
  amount: number;
  approved?: boolean | null;
  rejection_reason?: string | null;
};

export type ClaimResult = {
  /** Present when loaded from saved runs */
  id?: string;
  claim_id: string;
  decision: string;
  approved_amount: number;
  reason: string;
  /** Plain-language summary for members (no internal codes) */
  member_reason?: string;
  confidence_score: number;
  execution_trace: TraceEntry[];
  rejection_reasons?: string[];
  line_item_decisions?: LineItemDecision[];
  financial_breakdown?: Record<string, unknown>;
  /** Present when loading a stored claim (ops audit) */
  submission?: Record<string, unknown>;
  submitted_at?: string;
  /** Member has sent this claim to Plum / ops queue */
  recorded?: boolean;
  /** Ops reviewer has signed off for settlement (HITL) */
  ops_approved?: boolean;
  ops_approved_at?: string;
  ops_approval_note?: string;
  /** Assignment / OCR scenario id (e.g. TC001, OCR-003) */
  case_id?: string;
  /** Optional message from member when submitting to ops */
  member_note?: string;
};

export type ViewMode = "member" | "ops" | "test";

export type ClaimSubmissionPayload = Record<string, unknown>;

export type ChatMessage =
  | { id: string; role: "user"; kind: "text"; content: string }
  | { id: string; role: "assistant"; kind: "text"; content: string }
  | { id: string; role: "assistant"; kind: "claim-form"; content: string }
  | {
      id: string;
      role: "assistant";
      kind: "decision";
      content: string;
      result: ClaimResult;
    }
  | { id: string; role: "assistant"; kind: "typing"; content: string };

export type ClaimHistorySummary = {
  /** MongoDB record id — unique per saved run */
  id?: string;
  claim_id: string;
  member_id: string;
  policy_id: string;
  claim_category: string;
  claimed_amount: number;
  approved_amount: number;
  decision: string;
  reason: string;
  confidence_score: number;
  submitted_at: string;
  ops_approved?: boolean;
  case_id?: string;
  documents: Array<{ file_name?: string; actual_type?: string; has_content?: boolean }>;
};

export type DemoTestCase = {
  case_id: string;
  case_name: string;
  description: string;
  source?: "assignment" | "ocr";
  expectedDecision?: string | null;
  expectedAmount?: number;
};

export function isActionRequired(result: ClaimResult): boolean {
  if (result.decision === "PENDING") return true;
  const failedStep = result.execution_trace.find(
    (e) =>
      (e.step === "gatekeeper_agent" || e.step === "submission_validator") && e.status === "FAILED"
  );
  return Boolean(failedStep);
}

export function formatBreakdownKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Internal pipeline steps — full detail only in ops review */
export const OPS_ONLY_TRACE_STEPS = new Set([
  "ingest_submission",
  "ocr_agent",
  "extraction_agent",
  "format_response",
]);

/** Trace detail keys already shown in the ops decision card summary */
export const CARD_LEVEL_DETAIL_KEYS = new Set([
  "financial_breakdown",
  "line_item_decisions",
  "approved_amount",
  "rejection_reasons",
  "confidence_score",
  "degraded_steps",
  "fraud_signals",
]);

export function filterTraceForView(trace: TraceEntry[], viewMode: ViewMode): TraceEntry[] {
  if (viewMode !== "member") return trace;
  return trace.filter((entry) => !OPS_ONLY_TRACE_STEPS.has(entry.step));
}

export function filterTraceDetails(
  details: Record<string, unknown>,
  viewMode: ViewMode
): Record<string, unknown> {
  if (viewMode === "member") {
    return {};
  }

  return Object.fromEntries(
    Object.entries(details).filter(([key]) => !CARD_LEVEL_DETAIL_KEYS.has(key))
  );
}
