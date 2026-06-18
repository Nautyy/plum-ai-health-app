"use client";

import { useState } from "react";
import type { ClaimHistorySummary, DemoTestCase } from "@/types/claim";
import ClaimHistorySidebar from "./ClaimHistorySidebar";
import DemoSidebar from "./DemoSidebar";

type Tab = "scenarios" | "claims" | "approved";

type Props = {
  demoCases: DemoTestCase[];
  runningCaseId: string | null;
  claimLoading: boolean;
  claims: ClaimHistorySummary[];
  activeId: string | null;
  historyLoading: boolean;
  open: boolean;
  onClose: () => void;
  onNewReview: () => void;
  onRunCase: (testCase: DemoTestCase) => void;
  onSelectClaim: (claim: ClaimHistorySummary) => void;
};

export default function OpsSidebar({
  demoCases,
  runningCaseId,
  claimLoading,
  claims,
  activeId,
  historyLoading,
  open,
  onClose,
  onNewReview,
  onRunCase,
  onSelectClaim,
}: Props) {
  const [tab, setTab] = useState<Tab>("scenarios");

  const pendingClaims = claims.filter((c) => !c.ops_approved);
  const approvedClaims = claims.filter((c) => c.ops_approved);

  const tabClass = (active: boolean) =>
    `flex-1 rounded-md px-1.5 py-2 text-[11px] font-semibold transition ${
      active ? "bg-surface-muted text-text" : "text-text-muted hover:text-text"
    }`;

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

        <div className="flex border-b border-border p-1">
          <button type="button" onClick={() => setTab("scenarios")} className={tabClass(tab === "scenarios")}>
            Scenarios
          </button>
          <button type="button" onClick={() => setTab("claims")} className={tabClass(tab === "claims")}>
            Claims
          </button>
          <button type="button" onClick={() => setTab("approved")} className={tabClass(tab === "approved")}>
            Approved
          </button>
        </div>

        {tab === "scenarios" ? (
          <DemoSidebar
            embedded
            demoCases={demoCases}
            runningCaseId={runningCaseId}
            claimLoading={claimLoading}
            open
            onClose={onClose}
            onNewReview={onNewReview}
            onRunCase={onRunCase}
          />
        ) : tab === "claims" ? (
          <ClaimHistorySidebar
            embedded
            section="claims"
            claims={pendingClaims}
            activeId={activeId}
            loading={historyLoading}
            open
            onClose={onClose}
            onNewReview={onNewReview}
            onSelect={onSelectClaim}
          />
        ) : (
          <ClaimHistorySidebar
            embedded
            section="approved"
            claims={approvedClaims}
            activeId={activeId}
            loading={historyLoading}
            open
            onClose={onClose}
            onNewReview={onNewReview}
            onSelect={onSelectClaim}
          />
        )}
      </aside>
    </>
  );
}
