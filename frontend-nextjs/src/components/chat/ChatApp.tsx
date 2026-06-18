"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { Audience } from "./chatConfig";
import { AUDIENCE_CONFIG, getInitialMessages } from "./chatConfig";
import ClaimHistorySidebar from "./ClaimHistorySidebar";
import type { DemoTestCase } from "@/types/claim";
import type { ChatMessage, ClaimHistorySummary, ClaimResult } from "@/types/claim";
import ChatHeader from "./ChatHeader";
import ChatInput from "./ChatInput";
import ChatMessageView from "./ChatMessage";
import { getViewCapabilities } from "./viewCapabilities";
import { buildChatClaimContext, parseChatError } from "./chatContext";
import { fetchTestCasePayload } from "@/data/demoTestCases";

const DemoSidebar = dynamic(() => import("./DemoSidebar"), { ssr: false });
const OpsSidebar = dynamic(() => import("./OpsSidebar"), { ssr: false });

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function deploymentConfigError(): string | null {
  if (typeof window === "undefined") return null;
  const onLocalhost =
    window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
  const apiIsLocal = API_URL.includes("localhost") || API_URL.includes("127.0.0.1");
  if (!onLocalhost && apiIsLocal) {
    return `This app is deployed at ${window.location.origin} but NEXT_PUBLIC_API_URL is still "${API_URL}". Set it to your deployed backend URL (e.g. https://your-bff.onrender.com/api/v1) in Vercel/Render env vars and redeploy.`;
  }
  return null;
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function buildHistoryViewMessages(claim: ClaimResult, intro: string): ChatMessage[] {
  const scenario = claim.case_id ? ` (${claim.case_id})` : "";
  return [
    {
      id: uid(),
      role: "assistant",
      kind: "text",
      content: `Loaded claim #${claim.claim_id}${scenario} from saved runs. Full trace and decision are below — ask me anything about this adjudication.`,
    },
    {
      id: uid(),
      role: "assistant",
      kind: "decision",
      content: intro,
      result: claim,
    },
  ];
}

type Props = {
  audience: Audience;
  demoCases?: DemoTestCase[];
};

export default function ChatApp({ audience, demoCases }: Props) {
  const config = AUDIENCE_CONFIG[audience];
  const caps = getViewCapabilities(config.viewMode);

  const [messages, setMessages] = useState<ChatMessage[]>(() => getInitialMessages(audience));
  const [input, setInput] = useState("");
  const [claimLoading, setClaimLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [claimResult, setClaimResult] = useState<ClaimResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const [historyClaims, setHistoryClaims] = useState<ClaimHistorySummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(caps.showHistorySidebar);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loadingClaimId, setLoadingClaimId] = useState<string | null>(null);
  const [pendingSubmission, setPendingSubmission] = useState<Record<string, unknown> | null>(null);
  const [recordLoading, setRecordLoading] = useState(false);
  const [recordError, setRecordError] = useState<string | null>(null);
  const [opsApproveLoading, setOpsApproveLoading] = useState(false);
  const [opsApproveError, setOpsApproveError] = useState<string | null>(null);
  const [runningCaseId, setRunningCaseId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const loadHistory = useCallback(async () => {
    if (!caps.showHistorySidebar) return;

    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_URL}/claims/history?limit=50`);
      if (!res.ok) return;
      const data = (await res.json()) as ClaimHistorySummary[];
      setHistoryClaims(data);
    } catch {
      setHistoryClaims([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [caps.showHistorySidebar]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    const configError = deploymentConfigError();
    if (configError) setError(configError);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const addMessage = (msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  };

  const replaceTyping = (replacement: ChatMessage) => {
    setMessages((prev) => {
      const withoutTyping = prev.filter((m) => m.kind !== "typing");
      return [...withoutTyping, replacement];
    });
  };

  const handleNewChat = () => {
    setMessages(getInitialMessages(audience));
    setClaimResult(null);
    setPendingSubmission(null);
    setRecordError(null);
    setOpsApproveError(null);
    setActiveClaimId(null);
    setInput("");
    setError(null);
  };

  const openHistoricalClaim = async (item: ClaimHistorySummary) => {
    if (loadingClaimId) return;

    const rowId = item.id || `${item.claim_id}-${item.submitted_at}`;
    setLoadingClaimId(rowId);
    setError(null);
    setActiveClaimId(rowId);

    const fetchIds = [...new Set([item.id, item.claim_id].filter(Boolean))] as string[];
    let lastError = "Could not load claim";

    try {
      let data: ClaimResult | null = null;
      for (const id of fetchIds) {
        const res = await fetch(`${API_URL}/claims/${encodeURIComponent(id)}`);
        if (res.ok) {
          data = (await res.json()) as ClaimResult;
          break;
        }
        const text = await res.text();
        lastError = text || `Failed to load claim (${res.status})`;
        if (res.status !== 404) {
          throw new Error(lastError);
        }
      }

      if (!data) {
        throw new Error(lastError);
      }

      const loaded: ClaimResult = { ...data, recorded: true };
      setClaimResult(loaded);
      setActiveClaimId(loaded.id ?? rowId);
      setMessages(buildHistoryViewMessages(loaded, config.decisionIntro(data.decision)));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not load claim";
      setError(msg);
      setActiveClaimId(null);
    } finally {
      setLoadingClaimId(null);
    }
  };

  const handleClaimSubmit = async (
    payload: Record<string, unknown>,
    userLabel?: string
  ) => {
    setClaimLoading(true);
    setError(null);
    setRecordError(null);
    setOpsApproveError(null);
    setActiveClaimId(null);
    setPendingSubmission(payload);

    const submitLabel =
      userLabel ??
      (audience === "ops"
        ? `Run adjudication for ${payload.member_id} — ₹${Number(payload.claimed_amount).toLocaleString("en-IN")} (${payload.claim_category})`
        : `Check claim for ${payload.member_id} — ₹${Number(payload.claimed_amount).toLocaleString("en-IN")} (${payload.claim_category})`);

    addMessage({ id: uid(), role: "user", kind: "text", content: submitLabel });
    addMessage({ id: uid(), role: "assistant", kind: "typing", content: "" });

    const endpoint = caps.showSubmitClaimButton ? "adjudicate" : "submit";

    try {
      const res = await fetch(`${API_URL}/claims/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed (${res.status})`);
      }

      const data = (await res.json()) as ClaimResult;
      const testCaseId = payload.case_id ? String(payload.case_id) : undefined;
      const savedAsScenario = Boolean(testCaseId);
      const result: ClaimResult = caps.showSubmissionAudit
        ? {
            ...data,
            submission: payload,
            submitted_at: new Date().toISOString(),
            recorded: savedAsScenario,
            ops_approved: false,
            case_id: testCaseId,
          }
        : {
            ...data,
            submission: payload,
            recorded: savedAsScenario,
            case_id: testCaseId,
          };

      setClaimResult(result);
      setActiveClaimId(result.claim_id);

      replaceTyping({
        id: uid(),
        role: "assistant",
        kind: "decision",
        content: config.decisionIntro(result.decision),
        result,
      });

      if (caps.showHistorySidebar) {
        loadHistory();
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Submission failed";
      const configError = deploymentConfigError();
      setError(configError ?? msg);
      setPendingSubmission(null);
      replaceTyping({
        id: uid(),
        role: "assistant",
        kind: "text",
        content: configError
          ? configError
          : `Could not process claim: ${msg}. Backend URL: ${API_URL}. If deployed, set NEXT_PUBLIC_API_URL (frontend) and LANGGRAPH_BASE_URL (backend) in your host env vars.`,
      });
    } finally {
      setClaimLoading(false);
    }
  };

  const updateDecisionInMessages = (updated: ClaimResult) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.kind === "decision" && msg.result.claim_id === updated.claim_id
          ? { ...msg, result: updated }
          : msg
      )
    );
  };

  const handleRecordClaim = async (memberNote?: string) => {
    if (!claimResult || !pendingSubmission || recordLoading || claimResult.recorded) return;

    setRecordLoading(true);
    setRecordError(null);

    try {
      const res = await fetch(`${API_URL}/claims/record`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          submission: pendingSubmission,
          claim_id: claimResult.claim_id,
          decision: claimResult.decision,
          approved_amount: claimResult.approved_amount,
          reason: claimResult.reason,
          confidence_score: claimResult.confidence_score,
          execution_trace: claimResult.execution_trace,
          rejection_reasons: claimResult.rejection_reasons,
          line_item_decisions: claimResult.line_item_decisions,
          financial_breakdown: claimResult.financial_breakdown,
          ...(memberNote ? { member_note: memberNote } : {}),
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed (${res.status})`);
      }

      const data = (await res.json()) as ClaimResult;
      const updated: ClaimResult = {
        ...claimResult,
        ...data,
        submission: pendingSubmission,
        recorded: true,
        member_note: data.member_note ?? memberNote,
        submitted_at: data.submitted_at ?? new Date().toISOString(),
      };

      setClaimResult(updated);
      updateDecisionInMessages(updated);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not submit claim";
      setRecordError(msg);
    } finally {
      setRecordLoading(false);
    }
  };

  const handleAsk = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || chatLoading || claimLoading || !claimResult) return;

    setChatLoading(true);
    setError(null);
    addMessage({ id: uid(), role: "user", kind: "text", content: trimmed });
    addMessage({ id: uid(), role: "assistant", kind: "typing", content: "" });
    setInput("");

    const history = messages
      .filter((m) => m.kind === "text")
      .slice(-8)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await fetch(`${API_URL}/claims/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: trimmed,
          claim_context: buildChatClaimContext(claimResult),
          history,
          audience: config.chatAudience,
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed (${res.status})`);
      }

      const data = (await res.json()) as { answer: string };
      replaceTyping({ id: uid(), role: "assistant", kind: "text", content: data.answer });
    } catch (err) {
      const raw = err instanceof Error ? err.message : "Could not get an answer";
      const msg = parseChatError(raw);
      setError(msg);
      replaceTyping({
        id: uid(),
        role: "assistant",
        kind: "text",
        content: `Sorry, I couldn't answer that: ${msg}`,
      });
    } finally {
      setChatLoading(false);
    }
  };

  const handleOpsApprove = async (opsNote?: string) => {
    if (!claimResult || opsApproveLoading || claimResult.ops_approved) return;

    setOpsApproveLoading(true);
    setOpsApproveError(null);

    try {
      const res = await fetch(`${API_URL}/claims/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_id: claimResult.claim_id,
          ...(opsNote ? { ops_note: opsNote } : {}),
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed (${res.status})`);
      }

      const data = (await res.json()) as ClaimResult;
      const updated: ClaimResult = { ...claimResult, ...data, ops_approved: true };
      setClaimResult(updated);
      updateDecisionInMessages(updated);
      loadHistory();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not approve claim";
      setOpsApproveError(msg);
    } finally {
      setOpsApproveLoading(false);
    }
  };

  const handleRunDemoCase = async (testCase: DemoTestCase) => {
    setRunningCaseId(testCase.case_id);
    setSidebarOpen(false);
    try {
      const payload = await fetchTestCasePayload(testCase.case_id);
      await handleClaimSubmit(payload, `${testCase.case_id}: ${testCase.case_name}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not run scenario";
      setError(msg);
    } finally {
      setRunningCaseId(null);
    }
  };

  const handleSuggestion = (text: string) => {
    handleAsk(text);
  };

  const suggestions = config.followUpSuggestions;
  const inputDisabled = claimLoading || chatLoading || Boolean(loadingClaimId);
  const showOpsSidebar = Boolean(caps.showDemoSidebar && caps.showHistorySidebar && demoCases);
  const showSidebar =
    showOpsSidebar || caps.showHistorySidebar || Boolean(caps.showDemoSidebar && demoCases);

  return (
    <div className="flex h-dvh flex-col bg-[#f7f7f8]">
      <ChatHeader
        audience={audience}
        config={config}
        onNewChat={handleNewChat}
        showSidebarToggle={showSidebar}
        onToggleSidebar={() => setSidebarOpen(true)}
      />

      <div className="flex min-h-0 flex-1 overflow-hidden">
        {showOpsSidebar && demoCases && (
          <OpsSidebar
            demoCases={demoCases}
            runningCaseId={runningCaseId}
            claimLoading={claimLoading}
            claims={historyClaims}
            activeId={activeClaimId}
            historyLoading={historyLoading}
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            onNewReview={handleNewChat}
            onRunCase={handleRunDemoCase}
            onSelectClaim={openHistoricalClaim}
          />
        )}

        {!showOpsSidebar && caps.showHistorySidebar && (
          <ClaimHistorySidebar
            claims={historyClaims}
            activeId={activeClaimId}
            loading={historyLoading}
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            onNewReview={handleNewChat}
            onSelect={openHistoricalClaim}
          />
        )}

        {!showOpsSidebar && caps.showDemoSidebar && demoCases && (
          <DemoSidebar
            demoCases={demoCases}
            runningCaseId={runningCaseId}
            claimLoading={claimLoading}
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            onNewReview={handleNewChat}
            onRunCase={handleRunDemoCase}
          />
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="chat-scroll flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-3xl space-y-1 px-4 py-6 sm:px-6">
              {loadingClaimId && (
                <div className="rounded-xl border border-border bg-white px-4 py-3 text-sm text-text-muted">
                  Loading claim #{loadingClaimId}…
                </div>
              )}

              {messages.map((msg) => (
                <ChatMessageView
                  key={msg.id}
                  message={msg}
                  claimLoading={claimLoading}
                  recordLoading={recordLoading}
                  recordError={recordError}
                  viewMode={config.viewMode}
                  claimResult={claimResult}
                  opsApproveLoading={opsApproveLoading}
                  opsApproveError={opsApproveError}
                  onOpsApprove={caps.showOpsApproval ? handleOpsApprove : undefined}
                  onClaimSubmit={handleClaimSubmit}
                  onRecordClaim={caps.showSubmitClaimButton ? handleRecordClaim : undefined}
                />
              ))}

              {error && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {error}
                </div>
              )}

              <div ref={bottomRef} className="h-4" />
            </div>
          </div>

          {claimResult && (
            <ChatInput
              value={input}
              onChange={setInput}
              onSend={() => handleAsk(input)}
              disabled={inputDisabled}
              placeholder={config.placeholderAfter}
              suggestions={suggestions}
              onSuggestion={handleSuggestion}
              onNewChat={handleNewChat}
              newChatLabel={config.newClaimLabel}
            />
          )}
        </div>
      </div>
    </div>
  );
}
