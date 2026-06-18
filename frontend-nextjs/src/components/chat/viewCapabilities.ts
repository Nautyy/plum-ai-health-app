import type { ViewMode } from "@/types/claim";

/**
 * Single source of truth for what each portal shows.
 *
 * Member → outcome + plain English + what to do next
 * Ops    → outcome + full trace + policy/financial detail + audit history
 * Test   → one-click assignment scenarios + full trace
 */
export type ViewCapabilities = {
  showConfidence: boolean;
  showFullTrace: boolean;
  showTraceStepDetails: boolean;
  showFinancialBreakdown: boolean;
  showLineItems: boolean;
  showMemberPayoutSummary: boolean;
  showWhatHappensNext: boolean;
  showSubmissionAudit: boolean;
  showHistorySidebar: boolean;
  showDemoSidebar: boolean;
  showSubmitClaimButton: boolean;
  showOpsApproval: boolean;
  useFriendlyLabels: boolean;
  traceCollapsedByDefault: boolean;
};

const VIEW_CAPABILITIES: Record<ViewMode, ViewCapabilities> = {
  member: {
    showConfidence: false,
    showFullTrace: false,
    showTraceStepDetails: false,
    showFinancialBreakdown: false,
    showLineItems: false,
    showMemberPayoutSummary: true,
    showWhatHappensNext: true,
    showSubmissionAudit: false,
    showHistorySidebar: false,
    showDemoSidebar: false,
    showSubmitClaimButton: true,
    showOpsApproval: false,
    useFriendlyLabels: true,
    traceCollapsedByDefault: true,
  },
  ops: {
    showConfidence: true,
    showFullTrace: true,
    showTraceStepDetails: true,
    showFinancialBreakdown: true,
    showLineItems: true,
    showMemberPayoutSummary: false,
    showWhatHappensNext: false,
    showSubmissionAudit: true,
    showHistorySidebar: true,
    showDemoSidebar: true,
    showSubmitClaimButton: false,
    showOpsApproval: true,
    useFriendlyLabels: false,
    traceCollapsedByDefault: false,
  },
  test: {
    showConfidence: true,
    showFullTrace: true,
    showTraceStepDetails: true,
    showFinancialBreakdown: true,
    showLineItems: true,
    showMemberPayoutSummary: false,
    showWhatHappensNext: false,
    showSubmissionAudit: true,
    showHistorySidebar: false,
    showDemoSidebar: true,
    showSubmitClaimButton: false,
    showOpsApproval: false,
    useFriendlyLabels: false,
    traceCollapsedByDefault: false,
  },
};

export function getViewCapabilities(viewMode: ViewMode): ViewCapabilities {
  return VIEW_CAPABILITIES[viewMode];
}
