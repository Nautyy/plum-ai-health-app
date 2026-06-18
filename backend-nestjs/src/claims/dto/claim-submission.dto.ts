import { IsArray, IsBoolean, IsNumber, IsOptional, IsString, ValidateNested } from 'class-validator';
import { Type } from 'class-transformer';

export class ClaimDocumentDto {
  @IsString()
  file_id: string;

  @IsOptional()
  @IsString()
  file_name?: string;

  @IsOptional()
  @IsString()
  actual_type?: string;

  @IsOptional()
  @IsString()
  mime_type?: string;

  @IsOptional()
  @IsString()
  file_content_base64?: string;

  @IsOptional()
  @IsString()
  content_summary?: string;

  @IsOptional()
  @IsString()
  content_source?: string;

  @IsOptional()
  @IsString()
  patient_name_on_doc?: string;

  @IsOptional()
  @IsString()
  quality?: string;
}

export class ClaimHistoryDto {
  @IsString()
  claim_id: string;

  @IsString()
  date: string;

  @IsNumber()
  amount: number;

  @IsOptional()
  @IsString()
  provider?: string;
}

export class ClaimSubmissionDto {
  @IsString()
  member_id: string;

  @IsString()
  policy_id: string;

  @IsString()
  claim_category: string;

  @IsString()
  treatment_date: string;

  @IsNumber()
  claimed_amount: number;

  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => ClaimDocumentDto)
  documents: ClaimDocumentDto[];

  @IsOptional()
  @IsNumber()
  ytd_claims_amount?: number;

  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => ClaimHistoryDto)
  claims_history?: ClaimHistoryDto[];

  @IsOptional()
  @IsString()
  hospital_name?: string;

  @IsOptional()
  @IsString()
  pre_authorization_id?: string;

  /** SELF | SPOUSE | CHILD | PARENT — who the claim is for */
  @IsOptional()
  @IsString()
  claim_for?: string;

  @IsOptional()
  @IsString()
  patient_name?: string;

  @IsOptional()
  @IsBoolean()
  simulate_component_failure?: boolean;

  /** Scenario id when submitting from assignment / OCR test lab */
  @IsOptional()
  @IsString()
  case_id?: string;
}
