"use client";

import type { ChatMessage as ChatMessageType, ClaimResult, ViewMode } from "@/types/claim";
import AssistantAvatar from "./AssistantAvatar";
import ClaimFormCard from "./ClaimFormCard";
import DecisionCard from "./DecisionCard";

type Props = {
  message: ChatMessageType;
  claimLoading: boolean;
  recordLoading?: boolean;
  recordError?: string | null;
  viewMode: ViewMode;
  claimResult?: ClaimResult | null;
  opsApproveLoading?: boolean;
  opsApproveError?: string | null;
  onOpsApprove?: () => void | Promise<void>;
  onClaimSubmit: (payload: Record<string, unknown>) => Promise<void>;
  onRecordClaim?: (memberNote?: string) => void | Promise<void>;
};

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-1 py-1">
      <span className="typing-dot h-1.5 w-1.5 rounded-full bg-text-muted/50" />
      <span className="typing-dot h-1.5 w-1.5 rounded-full bg-text-muted/50" />
      <span className="typing-dot h-1.5 w-1.5 rounded-full bg-text-muted/50" />
    </div>
  );
}

export default function ChatMessage({
  message,
  claimLoading,
  recordLoading,
  recordError,
  viewMode,
  claimResult,
  opsApproveLoading,
  opsApproveError,
  onOpsApprove,
  onClaimSubmit,
  onRecordClaim,
}: Props) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end py-1">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-plum-brand px-4 py-2.5 text-[15px] leading-relaxed text-white">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 py-2">
      <AssistantAvatar className="mt-0.5" />
      <div className="min-w-0 flex-1 space-y-3">
        {message.kind === "typing" && <TypingIndicator />}

        {message.kind === "text" && (
          <p className="max-w-2xl text-[15px] leading-7 text-text whitespace-pre-wrap">
            {message.content}
          </p>
        )}

        {message.kind === "claim-form" && (
          <div className="max-w-2xl space-y-3">
            {message.content && (
              <p className="text-[15px] leading-7 text-text">{message.content}</p>
            )}
            <ClaimFormCard
              loading={claimLoading}
              variant={viewMode === "member" ? "member" : "ops"}
              onSubmit={onClaimSubmit}
            />
          </div>
        )}

        {message.kind === "decision" && (
          <div className="max-w-2xl space-y-3">
            {message.content && (
              <p className="text-[15px] leading-7 text-text">{message.content}</p>
            )}
            {viewMode === "ops" &&
              onOpsApprove &&
              claimResult?.claim_id === message.result.claim_id && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-white px-4 py-2.5 shadow-sm">
                  <p className="text-sm text-text-muted">
                    {message.result.ops_approved
                      ? "Approved by Claims Assistant for settlement"
                      : message.result.decision === "PENDING"
                        ? "Resolve document issues before approval"
                        : "Claims Assistant recommendation — human approval required"}
                  </p>
                  {message.result.ops_approved ? (
                    <span className="shrink-0 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
                      Approved
                    </span>
                  ) : message.result.decision !== "PENDING" ? (
                    <button
                      type="button"
                      onClick={() => onOpsApprove()}
                      disabled={opsApproveLoading}
                      className="shrink-0 rounded-lg bg-plum-brand px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-plum-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {opsApproveLoading ? "Approving…" : "Approve"}
                    </button>
                  ) : null}
                </div>
              )}
            {opsApproveError && viewMode === "ops" && claimResult?.claim_id === message.result.claim_id && (
              <p className="text-sm text-rose-600">{opsApproveError}</p>
            )}
            <DecisionCard
              result={message.result}
              viewMode={viewMode}
              onRecordClaim={onRecordClaim}
              recordLoading={recordLoading}
              recordError={recordError}
            />
          </div>
        )}
      </div>
    </div>
  );
}
