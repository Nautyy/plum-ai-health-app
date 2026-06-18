"use client";

import type { TraceEntry, ViewMode } from "@/types/claim";
import { filterTraceDetails } from "@/types/claim";
import { DetailValue } from "./formatTraceDetails";
import {
  getMemberVisibleTrace,
  memberTraceMessage,
  memberTraceStatusLabel,
  memberTraceStepLabel,
} from "./memberFriendly";
import { getViewCapabilities } from "./viewCapabilities";

const STATUS_STYLES: Record<string, string> = {
  SUCCESS: "border-emerald-200 bg-emerald-50 text-emerald-800",
  APPROVED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  FAILED: "border-rose-200 bg-rose-50 text-rose-800",
  REJECTED: "border-rose-200 bg-rose-50 text-rose-800",
  DEGRADED: "border-amber-200 bg-amber-50 text-amber-800",
  PARTIAL: "border-amber-200 bg-amber-50 text-amber-800",
  MANUAL_REVIEW: "border-sky-200 bg-sky-50 text-sky-800",
  PENDING: "border-slate-200 bg-slate-50 text-slate-700",
};

type Props = {
  trace: TraceEntry[];
  viewMode: ViewMode;
  defaultOpen?: boolean;
};

function TraceDetails({
  details,
  viewMode,
}: {
  details: Record<string, unknown>;
  viewMode: ViewMode;
}) {
  const filtered = filterTraceDetails(details, viewMode);
  const entries = Object.entries(filtered).filter(
    ([, v]) => v !== null && v !== undefined && v !== ""
  );
  if (entries.length === 0) return null;

  return (
    <div className="mt-2 space-y-0.5 rounded-lg bg-black/3 px-3 py-2 text-xs">
      {entries.map(([key, value]) => (
        <DetailValue key={key} label={key} value={value} />
      ))}
    </div>
  );
}

function getVisibleTrace(trace: TraceEntry[], viewMode: ViewMode, showFullTrace: boolean) {
  if (showFullTrace) return trace;
  return getMemberVisibleTrace(trace);
}

export default function ExecutionTracePanel({ trace, viewMode, defaultOpen }: Props) {
  const caps = getViewCapabilities(viewMode);
  const visibleTrace = getVisibleTrace(trace, viewMode, caps.showFullTrace);

  if (!trace.length) return null;
  if (!caps.showFullTrace && visibleTrace.length === 0) return null;

  const timeline = (
    <ol
      className={`relative space-y-3 ${caps.showFullTrace ? "border-l-2 border-plum-brand/20 pl-5" : "space-y-2"}`}
    >
      {visibleTrace.map((entry, i) => {
        const color = STATUS_STYLES[entry.status] ?? "border-border bg-white text-text";
        const stepLabel = caps.useFriendlyLabels
          ? memberTraceStepLabel(entry.step)
          : entry.step.replace(/_/g, " ");
        const statusLabel = caps.useFriendlyLabels
          ? memberTraceStatusLabel(entry.status)
          : `${entry.status}${entry.degraded ? " · degraded" : ""}`;
        const message = caps.useFriendlyLabels
          ? memberTraceMessage(entry.step, entry.message)
          : entry.message;

        return (
          <li key={`${entry.step}-${i}`} className={caps.showFullTrace ? "relative" : undefined}>
            {caps.showFullTrace && (
              <span className="absolute left-[-1.35rem] flex h-5 w-5 items-center justify-center rounded-full bg-plum-brand text-[10px] font-bold text-white">
                {i + 1}
              </span>
            )}
            <div className={`rounded-xl border px-3 py-2.5 ${color}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-semibold text-text">
                  {caps.useFriendlyLabels ? `✓ ${stepLabel}` : stepLabel}
                </span>
                <span
                  className={`font-medium tracking-wide opacity-80 ${
                    caps.showFullTrace ? "text-[11px] uppercase" : "text-xs normal-case"
                  }`}
                >
                  {statusLabel}
                </span>
              </div>
              <p className="mt-1 text-sm leading-relaxed opacity-90">{message}</p>
              {caps.showTraceStepDetails && entry.details && Object.keys(entry.details).length > 0 && (
                <TraceDetails details={entry.details} viewMode={viewMode} />
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );

  if (caps.showFullTrace) {
    return (
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-text-muted">
          Execution trace — ops review
        </h3>
        {timeline}
      </section>
    );
  }

  return (
    <details
      className="group rounded-xl border border-border bg-surface-muted"
      open={defaultOpen ?? !caps.traceCollapsedByDefault}
    >
      <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-text marker:content-none">
        <span className="flex items-center justify-between">
          How we processed your claim
          <span className="text-text-muted transition group-open:rotate-180">▾</span>
        </span>
      </summary>
      <div className="border-t border-border px-4 py-4">{timeline}</div>
    </details>
  );
}
