import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model, Types } from 'mongoose';
import { ClaimSubmissionDto } from './dto/claim-submission.dto';
import { ClaimRecord, ClaimRecordDocument } from './schemas/claim-record.schema';

export type AdjudicationResult = {
  claim_id: unknown;
  decision: unknown;
  approved_amount: unknown;
  reason: unknown;
  member_reason?: unknown;
  confidence_score: unknown;
  execution_trace: unknown[];
  rejection_reasons: unknown[];
  line_item_decisions: unknown[];
  financial_breakdown: Record<string, unknown>;
};

function stripDocumentContent(dto: ClaimSubmissionDto): Record<string, unknown> {
  return {
    ...dto,
    documents: dto.documents.map(({ file_content_base64, ...rest }) => ({
      ...rest,
      has_content: Boolean(file_content_base64),
    })),
  };
}

@Injectable()
export class ClaimsRepository {
  constructor(
    @InjectModel(ClaimRecord.name)
    private readonly claimModel: Model<ClaimRecordDocument>,
  ) {}

  async saveClaim(
    submission: ClaimSubmissionDto,
    result: AdjudicationResult,
    memberNote?: string,
  ) {
    const record = new this.claimModel({
      claim_id: String(result.claim_id),
      member_id: submission.member_id,
      policy_id: submission.policy_id,
      claim_category: submission.claim_category,
      treatment_date: submission.treatment_date,
      claimed_amount: submission.claimed_amount,
      decision: String(result.decision),
      approved_amount: Number(result.approved_amount ?? 0),
      reason: String(result.reason ?? ''),
      confidence_score: Number(result.confidence_score ?? 0),
      submission: stripDocumentContent(submission),
      execution_trace: result.execution_trace ?? [],
      rejection_reasons: result.rejection_reasons ?? [],
      line_item_decisions: result.line_item_decisions ?? [],
      financial_breakdown: result.financial_breakdown ?? {},
      ops_approved: false,
      ...(submission.case_id?.trim() ? { case_id: submission.case_id.trim() } : {}),
      ...(memberNote?.trim() ? { member_note: memberNote.trim() } : {}),
    });

    return record.save();
  }

  async findHistory(options: { decision?: string; limit?: number; case_id?: string }) {
    const limit = Math.min(options.limit ?? 50, 100);
    const filter: Record<string, unknown> = {};
    if (options.decision) filter.decision = options.decision;
    if (options.case_id) filter.case_id = options.case_id;

    return this.claimModel
      .find(filter)
      .sort({ submitted_at: -1 })
      .limit(limit)
      .select(
        'claim_id member_id policy_id claim_category claimed_amount approved_amount decision reason confidence_score submitted_at ops_approved case_id submission.documents',
      )
      .lean()
      .exec();
  }

  async findByClaimId(claimId: string) {
    return this.claimModel.findOne({ claim_id: claimId }).sort({ submitted_at: -1 }).lean().exec();
  }

  async findByRecordId(recordId: string) {
    if (!Types.ObjectId.isValid(recordId)) {
      return null;
    }
    return this.claimModel.findById(new Types.ObjectId(recordId)).lean().exec();
  }

  async markOpsApproved(claimId: string, opsNote?: string) {
    const update: Record<string, unknown> = {
      ops_approved: true,
      ops_approved_at: new Date(),
    };
    if (opsNote?.trim()) {
      update.ops_approval_note = opsNote.trim();
    }

    return this.claimModel
      .findOneAndUpdate({ claim_id: claimId }, { $set: update }, { new: true })
      .lean()
      .exec();
  }
}
