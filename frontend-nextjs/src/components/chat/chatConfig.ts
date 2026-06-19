import type { ChatMessage, ViewMode } from "@/types/claim";

export type Audience = "member" | "ops" | "test";

export type AudienceConfig = {
  viewMode: ViewMode;
  title: string;
  subtitle: string;
  newClaimLabel: string;
  initialMessages: ChatMessage[];
  followUpSuggestions: string[];
  placeholderAfter: string;
  decisionIntro: (decision: string) => string;
  chatAudience: "member" | "ops";
};

export const PORTAL_SECTIONS: { audience: Audience; href: string; label: string }[] = [
  { audience: "member", href: "/", label: "Employee" },
  { audience: "ops", href: "/ops", label: "Claims team" },
];

const MEMBER_WELCOME_ID = "welcome";
const MEMBER_FORM_ID = "claim-form";
const OPS_WELCOME_ID = "ops-welcome";
const OPS_FORM_ID = "ops-form";

export const AUDIENCE_CONFIG: Record<Audience, AudienceConfig> = {
  member: {
    viewMode: "member",
    title: "Claims Assistant",
    subtitle: "Employee health benefits · plumhq.com",
    newClaimLabel: "New claim",
    initialMessages: [
      {
        id: MEMBER_WELCOME_ID,
        role: "assistant",
        kind: "text",
        content:
          "Hi, I'm your Plum Claims Assistant.\n\nI can help you submit a health insurance claim and walk you through your result. Most reimbursement claims with Plum are settled within a week.",
      },
      {
        id: MEMBER_FORM_ID,
        role: "assistant",
        kind: "claim-form",
        content: "Fill in your claim details below to get an instant decision.",
      },
    ],
    followUpSuggestions: [
      "Why did I get this amount?",
      "What documents did you check?",
      "Can I appeal this?",
      "When will I get paid?",
    ],
    placeholderAfter: "Ask me anything about your claim…",
    decisionIntro: (decision) =>
      decision === "PENDING"
        ? "We couldn't complete your claim yet — see what's missing below."
        : "Here's your claim decision. Review the details below, then submit to Plum when you're ready.",
    chatAudience: "member",
  },
  ops: {
    viewMode: "ops",
    title: "Claims Review Console",
    subtitle: "Internal ops · adjudication, scenarios & trace",
    newClaimLabel: "New chat",
    initialMessages: [
      {
        id: OPS_WELCOME_ID,
        role: "assistant",
        kind: "text",
        content:
          "Plum Claims Review Console.\n\nProcess a claim submission and inspect the full adjudication pipeline — gatekeeper, OCR, extraction, policy engine, and decision trace.\n\nUse this view to validate AI decisions before settlement.",
      },
      {
        id: OPS_FORM_ID,
        role: "assistant",
        kind: "claim-form",
        content: "Enter claim details below to run adjudication and review the full execution trace.",
      },
    ],
    followUpSuggestions: [
      "Walk me through the execution trace",
      "Were any pipeline steps degraded?",
      "Why was this amount approved?",
      "What policy rules were applied?",
    ],
    placeholderAfter: "Ask about this claim's trace, policy, or decision…",
    decisionIntro: (decision) =>
      decision === "PENDING"
        ? "Early stop — gatekeeper or document validation failed. Review the trace and member-facing message below."
        : "Adjudication complete. Review the trace below — this is an AI recommendation until you approve for settlement.",
    chatAudience: "ops",
  },
  test: {
    viewMode: "test",
    title: "Test Lab",
    subtitle: "Assignment scenarios · one-click run",
    newClaimLabel: "Clear",
    initialMessages: [
      {
        id: "test-welcome",
        role: "assistant",
        kind: "text",
        content:
          "Assignment test lab.\n\nPick a scenario from the left panel (TC001–TC012) to run adjudication instantly — no form fill needed. The full pipeline trace appears here so you can validate each case.",
      },
    ],
    followUpSuggestions: [
      "Walk me through the execution trace",
      "Were any pipeline steps degraded?",
      "Why was this amount approved?",
      "What policy rules were applied?",
    ],
    placeholderAfter: "Ask about this test run…",
    decisionIntro: (decision) =>
      decision === "PENDING"
        ? "Early stop — document validation failed. Compare the trace and message against the test case expectations."
        : "Test run complete. Review the decision, trace, and financial output against the expected result.",
    chatAudience: "ops",
  },
};

export function getInitialMessages(audience: Audience): ChatMessage[] {
  return AUDIENCE_CONFIG[audience].initialMessages;
}
