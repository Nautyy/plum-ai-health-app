"use client";

import type { DemoTestCase } from "@/types/claim";

const EXPECTED_BADGE: Record<string, string> = {
  APPROVED: "text-emerald-700 bg-emerald-50",
  PARTIAL: "text-amber-800 bg-amber-50",
  REJECTED: "text-rose-700 bg-rose-50",
  MANUAL_REVIEW: "text-sky-800 bg-sky-50",
  PENDING: "text-slate-700 bg-slate-100",
};

type Props = {
  demoCases: DemoTestCase[];
  runningCaseId: string | null;
  claimLoading: boolean;
  open: boolean;
  embedded?: boolean;
  onClose: () => void;
  onNewReview: () => void;
  onRunCase: (testCase: DemoTestCase) => void;
};

function expectedLabel(tc: DemoTestCase): string {
  if (tc.expectedDecision == null) return "Early stop";
  let label = tc.expectedDecision.replace("_", " ");
  if (tc.expectedAmount != null) {
    label += ` · ₹${tc.expectedAmount.toLocaleString("en-IN")}`;
  }
  return label;
}

export default function DemoSidebar({
  demoCases,
  runningCaseId,
  claimLoading,
  open,
  embedded = false,
  onClose,
  onNewReview,
  onRunCase,
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
            Clear results
          </button>
        </div>
      )}

      <div className="chat-scroll flex-1 overflow-y-auto px-2 py-2">
        <p className="px-1 pb-2 text-[11px] font-semibold uppercase tracking-wide text-text-muted">
          Assignment & OCR scenarios
        </p>
        <ul className="space-y-1">
          {demoCases.map((tc) => {
            const isRunning = runningCaseId === tc.case_id;
            const exp = tc.expectedDecision ?? "PENDING";
            const badge = EXPECTED_BADGE[exp] ?? EXPECTED_BADGE.PENDING;

            return (
              <li key={tc.case_id}>
                <button
                  type="button"
                  disabled={claimLoading}
                  onClick={() => onRunCase(tc)}
                  className={`w-full rounded-lg border px-2.5 py-2.5 text-left transition ${
                    isRunning
                      ? "border-plum-brand/40 bg-plum-50 ring-1 ring-plum-brand/20"
                      : "border-border bg-white hover:border-plum-brand/30 hover:bg-surface-muted/50 disabled:opacity-50"
                  }`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-plum-brand">{tc.case_id}</span>
                    <span className="flex items-center gap-1">
                      {tc.source && (
                        <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[9px] font-medium uppercase text-slate-600">
                          {tc.source}
                        </span>
                      )}
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${badge}`}>
                        {expectedLabel(tc)}
                      </span>
                    </span>
                  </span>
                  <span className="mt-1 block text-[13px] font-medium leading-snug text-text">
                    {tc.case_name}
                  </span>
                  <span className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-text-muted">
                    {tc.description}
                  </span>
                  {isRunning && (
                    <span className="mt-2 block text-[11px] font-medium text-plum-brand">
                      Running…
                    </span>
                  )}
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
        className={`flex w-72 shrink-0 flex-col border-r border-border bg-white transition-transform duration-200 lg:relative lg:translate-x-0 ${
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
