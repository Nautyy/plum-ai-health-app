import { IsOptional, IsString } from 'class-validator';

export class ApproveClaimDto {
  @IsString()
  claim_id!: string;

  @IsOptional()
  @IsString()
  ops_note?: string;
}
