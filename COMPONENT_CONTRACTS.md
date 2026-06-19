# Component Contracts — Plum Claims Adjudication

Precise interfaces for each significant component. Another engineer could reimplement any single component from this document alone.



### Component map (matches LangGraph trace order)

| Order | Component | Section | Input → Output (one line) |
|-------|-----------|---------|---------------------------|
| — | Claim submission | §1 | Form + documents → BFF → LangGraph |
| — | Adjudication response | §2 | Graph → BFF → UI (`execution_trace[]`) |
| 1 | OCR agent | §3 | Images/PDFs → `content_summary` text |
| 2 | Gatekeeper agent | §4 | Documents → pass/fail + specific error message |
| 3 | Extraction agent | §5 | Text → structured fields (patient, amounts, diagnosis) |
| 4 | Submission validator | §6 | Form fields vs extracted data → pass/fail |
| 5 | Policy engine | §7 | Submission + extracted → decision + financial breakdown |
| 6 | Decision consolidator | §8 | Policy result + degraded steps → final confidence |
| — | BFF REST API | §10 | HTTP endpoints member/ops call |
| — | Frontend views | §12 | Member friendly vs ops full trace |

### Live demo ↔ contract cross-reference

| Demo case | Components exercised | Contract sections to mention |
|-----------|---------------------|------------------------------|
| **TC001** early stop | Gatekeeper only | §4 Gatekeeper → §2 `PENDING` response |
| **TC004** approval | All 8 graph nodes | §3–§8 full pipeline → §2 `APPROVED` response |

---

## 1. Claim Submission (input contract)

Shared across frontend → BFF → LangGraph. Canonical schema: `ai-agent-python/src/schemas.py` (`ClaimSubmission`).

### Input

```json
{
  "member_id": "EMP001",
  "policy_id": "PLUM_GHI_2024",
  "claim_category": "CONSULTATION | PHARMACY | DENTAL | DIAGNOSTICS | ...",
  "treatment_date": "YYYY-MM-DD",
  "claimed_amount": 1500,
  "documents": [
    {
      "file_id": "F001",
      "file_name": "prescription.jpg",
      "actual_type": "PRESCRIPTION | HOSPITAL_BILL | PHARMACY_BILL | LAB_REPORT",
      "mime_type": "image/jpeg",
      "file_content_base64": "<optional, for OCR>",
      "content_summary": "<optional, pre-filled text skips OCR>",
      "content_source": "prefilled | groq_vision | pypdf | user_paste",
      "quality": "GOOD | UNREADABLE",
      "patient_name_on_doc": "<optional override>"
    }
  ],
  "ytd_claims_amount": 0,
  "claims_history": [{ "claim_id": "...", "date": "...", "amount": 0, "provider": "" }],
  "hospital_name": "<optional>",
  "claim_for": "SELF | SPOUSE | CHILD | PARENT",
  "pre_authorization_id": "<optional>",
  "simulate_component_failure": false,
  "case_id": "<optional, e.g. TC004 for eval/demo runs>"
}
```

### Validation errors (BFF)

- `400 Bad Request` — class-validator failures on required fields
- Missing `member_id`, `policy_id`, `claim_category`, `treatment_date`, `claimed_amount`, or empty `documents`

---

## 2. Adjudication Response (output contract)

Returned by LangGraph → BFF → frontend. Schema: `AdjudicationResponse`.

### Output

```json
{
  "claim_id": "CLM_A1B2C3D4",
  "decision": "APPROVED | PARTIAL | REJECTED | MANUAL_REVIEW | PENDING",
  "approved_amount": 1350,
  "reason": "Ops/adjudication rationale — may include internal codes and audit wording",
  "member_reason": "Plain-language summary for employees — no internal codes",
  "confidence_score": 0.95,
  "execution_trace": [
    {
      "step": "gatekeeper_agent",
      "status": "SUCCESS | FAILED | DEGRADED",
      "message": "Step summary",
      "details": { },
      "degraded": false
    }
  ],
  "rejection_reasons": ["WAITING_PERIOD"],
  "line_item_decisions": [
    { "description": "Teeth Whitening", "amount": 4000, "approved": false, "rejection_reason": "COSMETIC_EXCLUSION" }
  ],
  "financial_breakdown": {
    "claimed_amount": 1500,
    "submitted_claimed_amount": 1500,
    "document_total_amount": 1500,
    "copay_percent": 10,
    "copay_amount": 150,
    "approved_amount": 1350
  }
}
```

### Errors

| Source | Code | Condition |
|--------|------|-----------|
| LangGraph down | 503 | BFF cannot reach `:2024` |
| Invalid submission | 400 | DTO validation |
| Claim not found | 404 | `GET /claims/:id` |
| Duplicate record | 409 | `POST /claims/record` with existing `claim_id` |
| Already approved | 409 | `POST /claims/approve` on settled claim |
| Cannot approve PENDING | 409 | `POST /claims/approve` on document-validation stop |

### Dual-audience messaging

| Field | Audience | Content |
|-------|----------|---------|
| `reason` | Ops, audit, eval traces | Adjudication rationale — may embed codes like `COSMETIC_EXCLUSION`, amount-mismatch audit notes |
| `member_reason` | Member UI, member chat | Plain-language summary built by `member_messages.py` — no internal codes |
| `rejection_reasons[]` | Ops | Machine-readable policy failure codes |
| `line_item_decisions[].rejection_reason` | Ops | Per-item codes; member UI maps these to friendly copy via `memberFriendly.ts` |

The member portal shows `member_reason` under **In plain English**. Ops console shows `reason`, rejection codes, line items, and full trace.

---

## 3. OCR Agent

**Module:** `ai-agent-python/src/ocr/document_ocr.py`

### Input

`list[ClaimDocument]` — each document may have `file_content_base64`, `mime_type`, `content_summary`.

### Output

```python
(updated_documents: list[ClaimDocument], logs: list[str], degraded: bool)
```

Each updated document gets:
- `content_summary` — extracted text (empty if unreadable)
- `content_source` — `"groq_vision" | "pypdf" | "text_decode" | "prefilled"`

### Behavior

1. Skip OCR if `content_summary` already present (unless base64 provided without summary).
2. **Images** — autocontrast/sharpen preprocessing (phone photos), then Groq vision with Indian medical document prompt (`ocr/prompts.py` aligned with `sample_documents_guide.md`).
3. **PDF text** — pypdf text extraction (multi-page joined).
4. **Scanned PDF** — if pypdf returns empty, rasterize each page (PyMuPDF) and vision OCR per page.
5. **Partial/stamped/handwritten** — best-effort text; `OCR_NOTE:` lines flag obscured, regional, or partial fields (degraded, not UNREADABLE).
6. On fully illegible image → `UNREADABLE` → `quality=UNREADABLE`.
7. On API failure → `degraded=True`, empty summary.

### Errors

- Does not raise — failures captured in `degraded` flag and trace logs.

---

## 4. Gatekeeper Agent

**Module:** `ai-agent-python/src/validators/document_validator.py` + `agents.GatekeeperAgent`

### Input

`ClaimSubmission` (with OCR-populated documents)

### Output

```python
GatekeeperResult(
  passed: bool,
  message: str,
  detected_types: list[str],
  missing_types: list[str],
  unreadable_files: list[str],
  patient_names_found: list[str],
  used_llm: bool
)
```

### Rules (deterministic, in order)

1. **Unreadable** — empty OCR, `quality=UNREADABLE`, OCR `UNREADABLE` token, or missing required fields per doc type (`document_readability` in `policy/rules_config.py`) → stop with re-upload message.
2. **Missing required types** — from `policy_terms.json → document_requirements[category].required`.
3. **Wrong document** — e.g. two prescriptions for CONSULTATION → specific message naming uploaded vs required type.
4. **Patient mismatch across docs** — different names on prescription vs bill.
5. **Member ID mismatch** — document patient not on member's roster (primary + dependents).

Document type inference: `validators/document_type.py` scores intent phrases from `policy/rules_config.py` (not added to policy JSON). Patient names: label parse → LLM fallback (`llm/patient.py`) for OCR-sourced docs.

### LLM fallback

Runs when `detected_types` contains `UNKNOWN`, or when inferred type confidence is below threshold (`needs_type_verification`). Model: `GATEKEEPER_MODEL`. On LLM failure → `passed=false`, degraded → MANUAL_REVIEW.

### Early stop effect

`passed=false` → graph sets `skip_to_decision`; routes to `decision_consolidator`, skipping extraction, submission validation, and policy. `decision=PENDING`, `approved_amount=0`.

---

## 5. Extraction Agent

**Module:** `ai-agent-python/src/agents.py` (`ExtractionAgent`)

### Input

`ClaimSubmission` with `content_summary` on documents; optional `simulate_component_failure: true` (TC011).

### Output

```python
(extracted: ExtractedMedicalData, degraded: bool, error: str | None)
```

### ExtractedMedicalData fields

| Field | Type | Description |
|-------|------|-------------|
| `patient_name` | string? | From document labels |
| `diagnosis` | string? | e.g. Viral Fever, T2DM |
| `treatment` | string? | Procedure or visit type |
| `doctor_name` | string? | |
| `doctor_registration` | string? | |
| `hospital_name` | string? | |
| `treatment_date` | string? | ISO date |
| `line_items` | LineItem[] | `{ description, amount }` |
| `total_amount` | float? | Bill total |
| `tests_ordered` | string[] | Lab tests |
| `medicines` | string[] | Prescribed drugs |
| `extraction_tier` | string | `tier-1-regex`, `tier-2-llm`, `tier-3-fallback`, `degraded` |
| `confidence` | float | 0.5–0.95 |

### Tier selection

- **Tier 2 (primary):** Groq structured extraction for OCR-sourced docs, free-form text, and any non-prefilled upload.
- **Tier 1 (gap-fill):** Regex/label parser on structured prefilled fixtures (`content_source: prefilled`, or `line_items:` JSON in summary). Merged after LLM to fill missing fields.
- **Tier 3:** Fallback with `claimed_amount` as total; confidence ≤ 0.65 if LLM fails.

### Errors

- `simulate_component_failure` → degraded tier, confidence 0.5.
- LLM failure → fallback to tier 1/3, `degraded=True`.

---

## 6. Submission Validator

**Module:** `ai-agent-python/src/validators/submission_validator.py` + `graph/nodes/submission_validator.py`

### Input

```python
validate_submission_against_extracted(
  submission: ClaimSubmission,
  extracted: ExtractedMedicalData,
) -> SubmissionValidationResult
```

Requires extraction to have run (uses document `content_summary` and extracted fields).

### Output

```python
SubmissionValidationResult(
  passed: bool,
  message: str,
  rejection_reasons: list[str],  # e.g. TREATMENT_DATE_MISMATCH, HOSPITAL_NAME_MISMATCH
  submitted_treatment_date: str | None,
  document_dates: list[str],
  submitted_hospital_name: str | None,
  document_hospital_names: list[str],
)
```

### Rules (in order)

1. **Inconsistent document dates** — multiple documents with different visit dates → `DOCUMENT_DATE_INCONSISTENT`.
2. **Treatment date mismatch** — form `treatment_date` ≠ date(s) on bill/prescription → `TREATMENT_DATE_MISMATCH` with specific dates in message.
3. **Hospital name mismatch** — form `hospital_name` ≠ hospital on bill (fuzzy match) → `HOSPITAL_NAME_MISMATCH`.
4. Hospital check skipped when form field is blank; date check skipped when no parseable document dates.

### Early stop effect

`passed=false` → graph sets `skip_to_decision`; routes to `decision_consolidator`, skipping `policy_engine`. `decision=PENDING`, `approved_amount=0`.

### Errors

- Does not raise — failures returned as `passed=false` with actionable message.

---

## 7. Policy Engine

**Module:** `ai-agent-python/src/engine.py` (`DynamicPolicyEngine`)

### Input

```python
evaluate(submission: ClaimSubmission, extracted: ExtractedMedicalData) -> PolicyEvaluationResult
```

Policy loaded from `config/policy_terms.json` at startup (reload per call via `load_policy()`). **Assignment policy JSON is not extended** — clinical intent phrases (exclusions, waiting conditions, pre-auth tests, document-type signals) live in `policy/rules_config.py`.

Supporting modules: `policy/exclusion_intent.py`, `policy/waiting_intent.py`, `policy/pre_auth_intent.py`, `policy/line_items.py`, `policy/intent_match.py`.

### Output

```python
PolicyEvaluationResult(
  decision: DecisionType,
  approved_amount: float,
  reason: str,
  rejection_reasons: list[str],
  line_item_decisions: list[LineItem],
  financial_breakdown: dict,
  eligible_from_date: str | None,
  fraud_signals: list[str],
  confidence: float
)
```

### Rules applied (in order)

1. Member exists in policy roster
2. Category covered under plan
3. Waiting period — intent match on diagnosis/treatment (`waiting_intent.py` + days from JSON)
4. Claim-level exclusions — intent match (`exclusion_intent.py`); cosmetic dental deferred to line items
5. Pre-authorization — intent match on test names (`pre_auth_intent.py` + threshold from JSON)
6. Per-claim and annual sub-limits (dental exempt from per-claim limit — code constant)
7. Line-item adjudication for dental/vision — covered/excluded lists from JSON (`line_items.py`)
8. Co-pay calculation
9. Network hospital discount
10. Fraud: same-day multiple claims → MANUAL_REVIEW

### Errors

- Does not raise — unknown member/category returns REJECTED with reason.

---

## 8. Decision Consolidator

**Module:** `ai-agent-python/src/graph/nodes/decision.py`

### Input

Graph state: `gatekeeper`, `policy_result`, `degraded_steps`, `confidence_score`

### Output

Final `decision`, `approved_amount`, `reason`, `confidence_score` (minimum of component confidences, minus cumulative degraded-step penalties).

### Confidence penalties

Defined in `graph/state.py` (`ConfidencePenalty`):

| Event | Penalty |
|-------|---------|
| OCR degraded | −0.10 (`OCR_FAILURE`) |
| Extraction degraded | −0.15 (`EXTRACTION_DEGRADED`) |
| Gatekeeper LLM failure | −0.25 (`GATEKEEPER_LLM_FAILURE`) |
| Each entry in `degraded_steps` | −0.25 (`COMPONENT_FAILURE`) at consolidator |

Minimum confidence floor: **0.50**. If an `APPROVED` decision falls below **0.75** after penalties, reason appends manual-review recommendation.

---

## 9. Ingest & Format Response (graph bookends)

**Modules:** `graph/nodes/ingest.py`, `graph/nodes/format_response.py`

### ingest_submission

- **Input:** raw `submission` dict or `ClaimSubmission` in graph state.
- **Output:** initialized state + first trace entry; on parse failure → `skip_to_decision`, `decision=PENDING`, FAILED trace.
- **Errors:** captured in trace; does not abort the graph.

### format_response

- **Input:** final graph state after `decision_consolidator`.
- **Output:** `AdjudicationResponse` fields flattened for API consumers + `member_reason` (plain-language copy from `member_messages.py`) + final SUCCESS trace entry.
- **Errors:** none — always runs.

---

## 10. NestJS BFF — REST API

**Base URL:** `http://localhost:8000/api/v1`

| Endpoint | Input | Output | Errors |
|----------|-------|--------|--------|
| `POST /claims/adjudicate` | `ClaimSubmissionDto` | `AdjudicationResult` | 503 LangGraph |
| `POST /claims/submit` | `ClaimSubmissionDto` | `AdjudicationResult` | 503; Mongo save logged on failure |
| `POST /claims/record` | `RecordClaimDto` | Saved claim | 409 duplicate |
| `POST /claims/approve` | `{ claim_id, ops_note? }` | Updated claim with `ops_approved: true` | 404, 409 |
| `POST /claims/chat` | `{ question, claim_context, history?, audience? }` | `{ answer }` | 503 no GROQ_API_KEY |
| `GET /claims/history` | `?decision=&limit=&case_id=` | `ClaimSummary[]` | — |
| `GET /claims/:claimId` | — | Full claim + trace | 404 |

### MongoDB record schema

`claim_id`, `member_id`, `policy_id`, `claim_category`, `claimed_amount`, `approved_amount`, `decision`, `reason`, `confidence_score`, `execution_trace`, `rejection_reasons`, `line_item_decisions`, `financial_breakdown`, `submission`, `submitted_at`, `case_id`, `ops_approved`, `ops_approved_at`, `ops_note`.

---

## 11. Claim Q&A Chat

**Module:** `backend-nestjs/src/claims/claim-chat-context.util.ts`

### Input

```typescript
{ question: string, claim_context: AdjudicationResult, history?: Message[], audience?: "member" | "ops" }
```

Context is trimmed — base64 document content stripped to avoid token limits.

### Output

```json
{ "answer": "Plain-language or ops-technical explanation" }
```

### Constraints

- Answers only from provided adjudication context
- Member audience: uses `member_reason` (not raw `reason`); no internal pipeline jargon or rejection codes
- Ops audience: may reference trace steps, `reason`, rejection codes, and degraded flags

---

## 12. Frontend views

| Capability | Member (`/`) | Ops (`/ops`) |
|------------|--------------|--------------|
| Submit flow | adjudicate → preview → record | submit (adjudicate + save) |
| Decision summary | `member_reason` — **In plain English** | `reason` — decision rationale |
| Execution trace | Summary | Full expandable trace |
| History sidebar | Hidden | Visible |
| Chat after decision | Yes (member copy) | Yes (technical copy) |
| Financial breakdown | Friendly labels + line items | Full audit keys + raw codes |
| Rejection codes | Hidden (mapped to friendly text) | Shown as `rejection_reasons[]` |
| Ops settlement approve | Hidden | Visible (`POST /claims/approve`) |

Configured via `viewCapabilities.ts` and `chatConfig.ts`.

---

## 13. Test runners

| Script | Input | Output |
|--------|-------|--------|
| `pytest` | `tests/` | 48 unit tests (no API key for policy/gatekeeper) |
| `run_test_cases.py` | `assignment/test_cases.json` | stdout pass/fail (12 cases) |
| `run_ocr_test_cases.py` | `sample-documents/ocr_test_cases.json` | stdout pass/fail (7 cases, live Groq OCR) |
| `generate_eval_report.py` | assignment + OCR cases | `EVAL_REPORT.md` (`--skip-ocr` preserves OCR when Groq rate-limited) |

---

## 14. External dependencies

| Service | Purpose | Required |
|---------|---------|----------|
| Groq API | OCR, extraction, gatekeeper LLM, chat | Yes |
| MongoDB | Claim persistence | Yes (for history/record) |
| LangGraph dev server | Graph execution | Yes |
| LangSmith | Trace debugging | Optional |
