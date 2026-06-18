"use client";

import type { ClaimHistorySummary } from "@/types/claim";

const DECISION_DOT: Record<string, string> = {
  APPROVED: "bg-emerald-500",
  PARTIAL: "bg-amber-500",
  REJECTED: "bg-rose-500",
  MANUAL_REVIEW: "bg-sky-500",
  PENDING: "bg-slate-400",
};

function claimTitle(claim: ClaimHistorySummary) {
  const amount = `₹${claim.claimed_amount.toLocaleString("en-IN")}`;
  return `${claim.member_id} · ${claim.claim_category} · ${amount}`;
}

function claimSubtitle(claim: ClaimHistorySummary, section: "claims" | "approved") {
  const date = new Date(claim.submitted_at).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
  const scenario = claim.case_id ? ` · ${claim.case_id}` : "";
  if (section === "approved") {
    return `${claim.decision.replace("_", " ")} · ${date}${scenario} · Approved by team`;
  }
  const hitl =
    claim.decision !== "PENDING" ? " · Awaiting HITL" : "";
  return `${claim.decision.replace("_", " ")} · ${date}${scenario}${hitl}`;
}

type Props = {
  claims: ClaimHistorySummary[];
  section?: "claims" | "approved";
  activeId: string | null;
  loading: boolean;
  open: boolean;
  embedded?: boolean;
  onClose: () => void;
  onNewReview: () => void;
  onSelect: (claim: ClaimHistorySummary) => void;
};

export default function ClaimHistorySidebar({
  claims,
  section = "claims",
  activeId,
  loading,
  open,
  embedded = false,
  onClose,
  onNewReview,
  onSelect,
}: Props) {
  const content = (
    <>
      {!embedded && (
        <div className="border-b border-border p-2">
          <button
            type="button"
            onClick={() => {
              onNewReview();
              onClose();
            }}
            className="flex w-full items-center gap-2 rounded-lg border border-border bg-white px-3 py-2.5 text-sm font-medium text-text shadow-sm transition hover:bg-surface-muted"
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full border border-border text-base leading-none">
              +
            </span>
            New chat
          </button>
        </div>
      )}

      <div className="px-3 pb-2 pt-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">
          {section === "approved" ? "Approved" : "Claims"}
        </p>
      </div>

      <div className="chat-scroll flex-1 overflow-y-auto px-2 pb-3">
        {loading && (
          <p className="px-2 py-3 text-xs text-text-muted">Loading…</p>
        )}

        {!loading && claims.length === 0 && (
          <p className="px-2 py-3 text-xs leading-relaxed text-text-muted">
            {section === "approved"
              ? "Claims you approve for settlement appear here after HITL sign-off."
              : "Adjudicated claims appear here after you run a scenario or submit a claim."}
          </p>
        )}

        <ul className="space-y-0.5">
          {claims.map((claim) => {
            const rowId = claim.id || `${claim.claim_id}-${claim.submitted_at}`;
            const isActive =
              activeId === rowId || activeId === claim.id || activeId === claim.claim_id;
            return (
              <li key={rowId}>
                <button
                  type="button"
                  onClick={() => {
                    onSelect(claim);
                    onClose();
                  }}
                  className={`group flex w-full items-start gap-2 rounded-lg px-2.5 py-2 text-left transition ${
                    isActive
                      ? "bg-surface-muted ring-1 ring-border"
                      : "hover:bg-surface-muted/70"
                  }`}
                >
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                      section === "approved"
                        ? "bg-emerald-500"
                        : DECISION_DOT[claim.decision] ?? DECISION_DOT.PENDING
                    }`}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className="block truncate text-[13px] font-medium text-text">
                        {claimTitle(claim)}
                      </span>
                      {claim.case_id && (
                        <span className="shrink-0 rounded bg-plum-50 px-1.5 py-0.5 text-[10px] font-semibold text-plum-brand">
                          {claim.case_id}
                        </span>
                      )}
                    </span>
                    <span className="mt-0.5 block truncate text-[11px] text-text-muted">
                      {claimSubtitle(claim, section)}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </>
  );

  if (embedded) {
    return <div className="flex min-h-0 flex-1 flex-col">{content}</div>;
  }

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close sidebar"
          className="fixed top-14 right-0 bottom-0 left-0 z-40 bg-black/30 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`flex w-65 shrink-0 flex-col border-r border-border bg-white transition-transform duration-200 lg:relative lg:translate-x-0 ${
          open
            ? "fixed top-14 bottom-0 left-0 z-50 translate-x-0 shadow-xl lg:static lg:shadow-none"
            : "fixed top-14 bottom-0 left-0 z-50 -translate-x-full lg:static lg:translate-x-0"
        }`}
      >
        {content}
      </aside>
    </>
  );
}
