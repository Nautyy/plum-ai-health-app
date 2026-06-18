import { IsArray, IsNumber, IsObject, IsOptional, IsString, ValidateNested } from 'class-validator';
import { Type } from 'class-transformer';
import { ClaimSubmissionDto } from './claim-submission.dto';

export class RecordClaimDto {
  @ValidateNested()
  @Type(() => ClaimSubmissionDto)
  submission!: ClaimSubmissionDto;

  @IsString()
  claim_id!: string;

  @IsString()
  decision!: string;

  @IsNumber()
  approved_amount!: number;

  @IsString()
  reason!: string;

  @IsNumber()
  confidence_score!: number;

  @IsOptional()
  @IsArray()
  execution_trace?: unknown[];

  @IsOptional()
  @IsArray()
  rejection_reasons?: unknown[];

  @IsOptional()
  @IsArray()
  line_item_decisions?: unknown[];

  @IsOptional()
  @IsObject()
  financial_breakdown?: Record<string, unknown>;

  @IsOptional()
  @IsString()
  member_note?: string;

  @IsOptional()
  @IsString()
  case_id?: string;
}
