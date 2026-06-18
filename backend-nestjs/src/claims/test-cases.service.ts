import { Injectable, NotFoundException } from '@nestjs/common';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

type RawTestCase = {
  case_id: string;
  case_name: string;
  description: string;
  input?: Record<string, unknown>;
  files?: Array<{ path: string; actual_type: string; mime_type?: string }>;
  expected: Record<string, unknown>;
  ocr_only?: boolean;
};

export type TestCaseSummary = {
  case_id: string;
  case_name: string;
  description: string;
  source: 'assignment' | 'ocr';
  expected_decision?: string | null;
  expected_amount?: number;
};

@Injectable()
export class TestCasesService {
  private readonly repoRoot = join(process.cwd(), '..');

  private readJson(relativePath: string): { test_cases: RawTestCase[] } {
    const path = join(this.repoRoot, relativePath);
    if (!existsSync(path)) {
      throw new NotFoundException(`Test cases file not found: ${relativePath}`);
    }
    return JSON.parse(readFileSync(path, 'utf-8')) as { test_cases: RawTestCase[] };
  }

  private formatContentSummary(content: Record<string, unknown>): string {
    const lines: string[] = [];
    for (const [key, value] of Object.entries(content)) {
      if (key === 'line_items') {
        lines.push(`line_items: ${JSON.stringify(value)}`);
      } else if (Array.isArray(value)) {
        lines.push(`${key}: ${value.map(String).join(', ')}`);
      } else {
        lines.push(`${key.replace(/_/g, ' ')}: ${String(value)}`);
      }
    }
    return lines.join('\n');
  }

  private normalizeAssignmentDoc(doc: Record<string, unknown>): Record<string, unknown> {
    const out = { ...doc };
    const content = doc.content;
    if (content && typeof content === 'object' && !Array.isArray(content)) {
      out.content_summary = this.formatContentSummary(content as Record<string, unknown>);
      out.content_source = 'prefilled';
      delete out.content;
    }
    if (!out.file_name && out.file_id) {
      out.file_name = String(out.file_id);
    }
    return out;
  }

  private loadFileBase64(relativePath: string): string {
    const path = join(this.repoRoot, 'sample-documents', relativePath);
    if (!existsSync(path)) {
      throw new NotFoundException(`Sample document not found: ${relativePath}`);
    }
    return readFileSync(path).toString('base64');
  }

  listTestCases(): TestCaseSummary[] {
    const assignment = this.readJson('assignment/test_cases.json').test_cases;
    const ocr = this.readJson('sample-documents/ocr_test_cases.json').test_cases;

    const assignmentSummaries = assignment.map((tc) => ({
      case_id: tc.case_id,
      case_name: tc.case_name,
      description: tc.description,
      source: 'assignment' as const,
      expected_decision: (tc.expected?.decision as string | null | undefined) ?? null,
      expected_amount: tc.expected?.approved_amount as number | undefined,
    }));

    const ocrSummaries = ocr
      .filter((tc) => !tc.ocr_only)
      .map((tc) => ({
        case_id: tc.case_id,
        case_name: tc.case_name,
        description: tc.description,
        source: 'ocr' as const,
        expected_decision: (tc.expected?.decision as string | null | undefined) ?? null,
        expected_amount: tc.expected?.approved_amount as number | undefined,
      }));

    return [...assignmentSummaries, ...ocrSummaries];
  }

  buildPayload(caseId: string): Record<string, unknown> {
    const assignment = this.readJson('assignment/test_cases.json').test_cases;
    const assignmentCase = assignment.find((tc) => tc.case_id === caseId);
    if (assignmentCase?.input) {
      const input = assignmentCase.input;
      const documents = ((input.documents as Record<string, unknown>[]) ?? []).map((doc) =>
        this.normalizeAssignmentDoc(doc),
      );
      return {
        ...input,
        documents,
        case_id: caseId,
      };
    }

    const ocr = this.readJson('sample-documents/ocr_test_cases.json').test_cases;
    const ocrCase = ocr.find((tc) => tc.case_id === caseId);
    if (!ocrCase) {
      throw new NotFoundException(`Test case ${caseId} not found`);
    }

    const documents = (ocrCase.files ?? []).map((ref, index) => ({
      file_id: `OCR${String(index + 1).padStart(3, '0')}`,
      file_name: ref.path.split('/').pop(),
      actual_type: ref.actual_type,
      mime_type: ref.mime_type ?? 'image/jpeg',
      file_content_base64: this.loadFileBase64(ref.path),
    }));

    return {
      ...(ocrCase.input ?? {}),
      documents,
      case_id: caseId,
    };
  }
}
