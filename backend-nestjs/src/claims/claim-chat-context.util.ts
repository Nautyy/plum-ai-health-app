/** Trim adjudication payload before sending to Groq chat (drops base64, heavy trace details). */

type TraceEntry = {
  step?: string;
  status?: string;
  message?: string;
  degraded?: boolean;
  details?: Record<string, unknown>;
};

type DocumentRef = {
  file_id?: string;
  file_name?: string;
  actual_type?: string;
  mime_type?: string;
  has_content?: boolean;
};

export function buildChatContext(
  raw: Record<string, unknown>,
  audience: 'member' | 'ops',
): Record<string, unknown> {
  const submission = raw.submission as Record<string, unknown> | undefined;

  let cleanSubmission: Record<string, unknown> | undefined;
  if (submission) {
    const docs = (submission.documents as DocumentRef[]) ?? [];
    cleanSubmission = {
      member_id: submission.member_id,
      policy_id: submission.policy_id,
      claim_category: submission.claim_category,
      treatment_date: submission.treatment_date,
      claimed_amount: submission.claimed_amount,
      hospital_name: submission.hospital_name,
      documents: docs.map((doc) => ({
        file_id: doc.file_id,
        file_name: doc.file_name,
        actual_type: doc.actual_type,
        has_content: Boolean((doc as { file_content_base64?: string }).file_content_base64),
      })),
    };
  }

  const trace = (raw.execution_trace as TraceEntry[]) ?? [];
  const execution_trace =
    audience === 'ops'
      ? trace.map((entry) => ({
          step: entry.step,
          status: entry.status,
          message: truncate(entry.message, 400),
          degraded: entry.degraded,
        }))
      : trace
          .filter((entry) =>
            ['gatekeeper_agent', 'policy_engine', 'decision_consolidator'].includes(
              entry.step ?? '',
            ),
          )
          .map((entry) => ({
            step: entry.step,
            status: entry.status,
            message: truncate(entry.message, 300),
          }));

  return {
    claim_id: raw.claim_id,
    decision: raw.decision,
    approved_amount: raw.approved_amount,
    reason: raw.reason,
    confidence_score: raw.confidence_score,
    rejection_reasons: raw.rejection_reasons,
    line_item_decisions: raw.line_item_decisions,
    financial_breakdown: raw.financial_breakdown,
    recorded: raw.recorded,
    submitted_at: raw.submitted_at,
    submission: cleanSubmission,
    execution_trace,
  };
}

function truncate(value: unknown, maxLen: number): string | undefined {
  if (typeof value !== 'string') return undefined;
  return value.length <= maxLen ? value : `${value.slice(0, maxLen)}…`;
}
