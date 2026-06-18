import type { DemoTestCase } from "@/types/claim";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchTestCases(): Promise<DemoTestCase[]> {
  const res = await fetch(`${API_URL}/claims/test-cases`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load test cases (${res.status})`);
  }
  const rows = (await res.json()) as Array<{
    case_id: string;
    case_name: string;
    description: string;
    source: "assignment" | "ocr";
    expected_decision?: string | null;
    expected_amount?: number;
  }>;
  return rows.map((tc) => ({
    case_id: tc.case_id,
    case_name: tc.case_name,
    description: tc.description,
    source: tc.source,
    expectedDecision: tc.expected_decision,
    expectedAmount: tc.expected_amount,
  }));
}

export async function fetchTestCasePayload(caseId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_URL}/claims/test-cases/${encodeURIComponent(caseId)}/payload`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to load payload for ${caseId}`);
  }
  return res.json() as Promise<Record<string, unknown>>;
}
