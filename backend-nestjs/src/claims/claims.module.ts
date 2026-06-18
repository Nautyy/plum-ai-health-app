import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { ClaimsController } from './claims.controller';
import { ClaimsRepository } from './claims.repository';
import { ClaimsService } from './claims.service';
import { ClaimRecord, ClaimRecordSchema } from './schemas/claim-record.schema';
import { TestCasesService } from './test-cases.service';

@Module({
  imports: [
    MongooseModule.forFeature([{ name: ClaimRecord.name, schema: ClaimRecordSchema }]),
  ],
  controllers: [ClaimsController],
  providers: [ClaimsService, ClaimsRepository, TestCasesService],
})
export class ClaimsModule {}
