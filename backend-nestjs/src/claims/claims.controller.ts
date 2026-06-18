import { Body, Controller, Get, Param, Post, Query } from '@nestjs/common';
import { ClaimsService } from './claims.service';
import { ClaimChatDto } from './dto/claim-chat.dto';
import { ClaimSubmissionDto } from './dto/claim-submission.dto';
import { RecordClaimDto } from './dto/record-claim.dto';
import { ApproveClaimDto } from './dto/approve-claim.dto';
import { TestCasesService } from './test-cases.service';

@Controller('claims')
export class ClaimsController {
  constructor(
    private readonly claimsService: ClaimsService,
    private readonly testCasesService: TestCasesService,
  ) {}

  @Post('submit')
  submit(@Body() dto: ClaimSubmissionDto) {
    return this.claimsService.submitClaim(dto);
  }

  @Post('adjudicate')
  adjudicate(@Body() dto: ClaimSubmissionDto) {
    return this.claimsService.adjudicateClaim(dto);
  }

  @Post('record')
  record(@Body() dto: RecordClaimDto) {
    return this.claimsService.recordClaim(dto);
  }

  @Post('approve')
  approve(@Body() dto: ApproveClaimDto) {
    return this.claimsService.approveClaim(dto);
  }

  @Post('chat')
  chat(@Body() dto: ClaimChatDto) {
    return this.claimsService.askAboutClaim(dto);
  }

  @Get('test-cases')
  listTestCases() {
    return this.testCasesService.listTestCases();
  }

  @Get('test-cases/:caseId/payload')
  getTestCasePayload(@Param('caseId') caseId: string) {
    return this.testCasesService.buildPayload(caseId);
  }

  @Get('history')
  history(
    @Query('decision') decision?: string,
    @Query('limit') limit?: string,
    @Query('case_id') caseId?: string,
  ) {
    const parsedLimit = limit ? Number(limit) : undefined;
    return this.claimsService.getClaimHistory(decision, parsedLimit, caseId);
  }

  @Get(':claimId')
  getOne(@Param('claimId') claimId: string) {
    return this.claimsService.getClaimById(claimId);
  }
}
