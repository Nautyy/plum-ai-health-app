import { Injectable, NotFoundException, ServiceUnavailableException, ConflictException } from '@nestjs/common';
import { Client } from '@langchain/langgraph-sdk';
import { ClaimsRepository, AdjudicationResult } from './claims.repository';
import { buildChatContext } from './claim-chat-context.util';
import { ClaimChatDto } from './dto/claim-chat.dto';
import { ClaimSubmissionDto } from './dto/claim-submission.dto';
import { RecordClaimDto } from './dto/record-claim.dto';
import { ApproveClaimDto } from './dto/approve-claim.dto';

@Injectable()
export class ClaimsService {
  constructor(private readonly claimsRepository: ClaimsRepository) {}
  private readonly langGraphBaseUrl = (
    process.env.LANGGRAPH_BASE_URL || 'http://127.0.0.1:2024'
  ).replace(/\/$/, '');
  private readonly graphId =
    process.env.LANGGRAPH_GRAPH_ID || 'claims_adjudication';
  private readonly langGraphTimeoutMs = Number(process.env.LANGGRAPH_TIMEOUT_MS || 120000);

  async submitClaim(dto: ClaimSubmissionDto) {
    const mapped = await this.adjudicateClaim(dto);
    try {
      await this.claimsRepository.saveClaim(dto, mapped);
    } catch (saveError) {
      console.error('Failed to persist claim to MongoDB:', saveError);
    }
    return mapped;
  }

  async adjudicateClaim(dto: ClaimSubmissionDto) {
    const submission = JSON.parse(JSON.stringify(dto)) as ClaimSubmissionDto;
    const client = new Client({
      apiUrl: this.langGraphBaseUrl,
      timeoutMs: this.langGraphTimeoutMs,
    });

    try {
      const thread = await client.threads.create();
      const result = await client.runs.wait(thread.thread_id, this.graphId, {
        input: { submission },
      });

      const mapped = this.mapLangGraphOutput(result);
      if (!mapped.claim_id || mapped.claim_id === 'UNKNOWN') {
        throw new Error(
          `LangGraph returned an empty response. Check agent at ${this.langGraphBaseUrl} and graph id "${this.graphId}".`,
        );
      }

      if (submission.case_id?.trim()) {
        try {
          await this.claimsRepository.saveClaim(submission, mapped);
        } catch (saveError) {
          console.error('Failed to persist test case run to MongoDB:', saveError);
        }
      }

      return mapped;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'LangGraph invoke failed';
      throw new ServiceUnavailableException(
        `${message} (agent: ${this.langGraphBaseUrl})`,
      );
    }
  }

  async recordClaim(dto: RecordClaimDto) {
    const existing = await this.claimsRepository.findByClaimId(dto.claim_id);
    if (existing) {
      throw new ConflictException(`Claim ${dto.claim_id} is already on file`);
    }

    const result: AdjudicationResult = {
      claim_id: dto.claim_id,
      decision: dto.decision,
      approved_amount: dto.approved_amount,
      reason: dto.reason,
      confidence_score: dto.confidence_score,
      execution_trace: dto.execution_trace ?? [],
      rejection_reasons: dto.rejection_reasons ?? [],
      line_item_decisions: dto.line_item_decisions ?? [],
      financial_breakdown: dto.financial_breakdown ?? {},
    };

    await this.claimsRepository.saveClaim(
      { ...dto.submission, ...(dto.case_id ? { case_id: dto.case_id } : {}) },
      result,
      dto.member_note,
    );
    return this.getClaimById(dto.claim_id);
  }

  async askAboutClaim(dto: ClaimChatDto) {
    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) {
      throw new ServiceUnavailableException('GROQ_API_KEY not configured for claim Q&A');
    }

    const model = process.env.CHAT_MODEL || 'llama-3.1-8b-instant';
    const audience = dto.audience === 'ops' ? 'ops' : 'member';
    const contextJson = JSON.stringify(buildChatContext(dto.claim_context, audience));
    const history = (dto.history ?? []).slice(-6);
    const isOps = audience === 'ops';

    const systemPrompt = isOps
      ? `You are Plum Claims Review Assistant for internal ops/adjudication teams.
Explain claim decisions using the execution trace, policy evaluation, financial breakdown, and rejection reasons.
Reference specific pipeline steps (gatekeeper, OCR, extraction, policy_engine) when relevant.
Note degraded steps and confidence impacts. Use technical but clear language.
Answer ONLY from the adjudication result below. Use INR for amounts. Never invent policy rules.

Adjudication result:
${contextJson}`
      : `You are Plum Claims Assistant — a helpful, empathetic health insurance claims advisor for Plum (plumhq.com).
You explain claim decisions clearly in plain language for employees. Answer ONLY based on the adjudication result below.
If financial_breakdown has submitted_claimed_amount and document_total_amount that differ, explain that the form amount may differ from the bill read from documents and that the decision uses document line items and policy rules.
If the user asks something not covered by the result, say you don't have that information and suggest contacting Plum support.
Keep answers concise (2-4 short paragraphs max). Use INR for amounts. Never invent policy rules or amounts.
Do not expose internal pipeline jargon unless the member asks.

Adjudication result:
${contextJson}`;

    const messages = [
      { role: 'system', content: systemPrompt },
      ...history.map((item) => ({ role: item.role, content: item.content })),
      { role: 'user', content: dto.question },
    ];

    try {
      const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model,
          messages,
          temperature: 0.3,
          max_tokens: 600,
        }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Groq request failed (${response.status})`);
      }

      const data = (await response.json()) as {
        choices?: Array<{ message?: { content?: string } }>;
      };
      const answer = data.choices?.[0]?.message?.content?.trim();
      if (!answer) {
        throw new Error('Empty response from Groq');
      }

      return { answer };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Claim Q&A failed';
      throw new ServiceUnavailableException(message);
    }
  }

  async approveClaim(dto: ApproveClaimDto) {
    const record = await this.claimsRepository.findByClaimId(dto.claim_id);
    if (!record) {
      throw new NotFoundException(`Claim ${dto.claim_id} not found`);
    }
    if (record.ops_approved) {
      throw new ConflictException(`Claim ${dto.claim_id} is already approved for settlement`);
    }
    if (record.decision === 'PENDING') {
      throw new ConflictException(
        'Cannot approve a claim that stopped at document validation. Resolve issues first.',
      );
    }

    const updated = await this.claimsRepository.markOpsApproved(dto.claim_id, dto.ops_note);
    if (!updated) {
      throw new NotFoundException(`Claim ${dto.claim_id} not found`);
    }

    return this.getClaimById(dto.claim_id);
  }

  async getClaimHistory(decision?: string, limit?: number, caseId?: string) {
    const records = await this.claimsRepository.findHistory({ decision, limit, case_id: caseId });
    return records.map((record) => ({
      id: String(record._id),
      claim_id: record.claim_id,
      member_id: record.member_id,
      policy_id: record.policy_id,
      claim_category: record.claim_category,
      claimed_amount: record.claimed_amount,
      approved_amount: record.approved_amount,
      decision: record.decision,
      reason: record.reason,
      confidence_score: record.confidence_score,
      submitted_at: record.submitted_at?.toISOString?.() ?? record.submitted_at,
      ops_approved: Boolean(record.ops_approved),
      case_id: record.case_id ?? undefined,
      documents: (record.submission as { documents?: unknown[] })?.documents ?? [],
    }));
  }

  async getClaimById(claimIdOrRecordId: string) {
    const record =
      (await this.claimsRepository.findByRecordId(claimIdOrRecordId)) ??
      (await this.claimsRepository.findByClaimId(claimIdOrRecordId));
    if (!record) {
      throw new NotFoundException(`Claim ${claimIdOrRecordId} not found`);
    }

    return {
      id: String(record._id),
      claim_id: record.claim_id,
      decision: record.decision,
      approved_amount: record.approved_amount,
      reason: record.reason,
      confidence_score: record.confidence_score,
      execution_trace: record.execution_trace,
      rejection_reasons: record.rejection_reasons,
      line_item_decisions: record.line_item_decisions,
      financial_breakdown: record.financial_breakdown,
      submission: record.submission,
      member_note: record.member_note,
      ops_approved: Boolean(record.ops_approved),
      ops_approved_at: record.ops_approved_at?.toISOString?.() ?? record.ops_approved_at,
      ops_approval_note: record.ops_approval_note,
      case_id: record.case_id ?? undefined,
      submitted_at: record.submitted_at?.toISOString?.() ?? record.submitted_at,
    };
  }

  private mapLangGraphOutput(result: unknown): AdjudicationResult {
    const data = this.extractAdjudicationState(result);
    const policyResult = data.policy_result as Record<string, unknown> | undefined;
    const trace = (data.execution_trace as Array<{ details?: Record<string, unknown> }>) ?? [];
    const decisionTrace = [...trace].reverse().find((e) => e.details?.financial_breakdown != null);

    const lineItemDecisions =
      (data.line_item_decisions as unknown[]) ??
      (policyResult?.line_item_decisions as unknown[]) ??
      (decisionTrace?.details?.line_item_decisions as unknown[]) ??
      [];

    const financialBreakdown =
      (data.financial_breakdown as Record<string, unknown>) ??
      (policyResult?.financial_breakdown as Record<string, unknown>) ??
      (decisionTrace?.details?.financial_breakdown as Record<string, unknown>) ??
      {};

    return {
      claim_id: String(data.claim_id ?? 'UNKNOWN'),
      decision: data.decision,
      approved_amount: Number(data.approved_amount ?? 0),
      reason: String(data.reason ?? ''),
      member_reason: String(data.member_reason ?? ''),
      confidence_score: Number(data.confidence_score ?? 1),
      execution_trace: trace,
      rejection_reasons: (data.rejection_reasons as unknown[]) ?? [],
      line_item_decisions: lineItemDecisions,
      financial_breakdown: financialBreakdown,
    };
  }

  /** LangGraph SDK may return flat state or nested { values: ... }. */
  private extractAdjudicationState(result: unknown): Record<string, unknown> {
    const raw = result as Record<string, unknown>;
    if (!raw || typeof raw !== 'object') {
      return {};
    }
    if (raw.claim_id) {
      return raw;
    }
    const values = raw.values as Record<string, unknown> | undefined;
    if (values?.claim_id) {
      return values;
    }
    const output = raw.output as Record<string, unknown> | undefined;
    if (output?.claim_id) {
      return output;
    }
    return raw;
  }
}
