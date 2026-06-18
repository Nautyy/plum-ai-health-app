# Eval Report — Plum Claims Adjudication

> Show the **summary tables** first, then **TC001** and **TC004** for live demos. OCR image cases (OCR-001–OCR-006) validate Groq vision on `sample-documents/`.

Generated: 2026-06-18 19:09 UTC  
Sources: `assignment/test_cases.json` (12 cases) · `sample-documents/ocr_test_cases.json` (7 cases)  
**Summary: 12/12 assignment cases · 7/7 OCR cases matched expected outcomes**

## Demo guide — show this table first

| Case | Scenario | Decision | Approved | Match | Live demo? |
|------|----------|----------|----------|-------|------------|
| TC001 | Wrong Document Uploaded | `PENDING` | INR 0 | PASS | **Yes** — early stop |
| TC002 | Unreadable Document | `PENDING` | INR 0 | PASS | — |
| TC003 | Documents Belong to Different Patients | `PENDING` | INR 0 | PASS | — |
| TC004 | Clean Consultation — Full Approval | `APPROVED` | INR 1,350 | PASS | **Yes** — full approval |
| TC005 | Waiting Period — Diabetes | `REJECTED` | INR 0 | PASS | — |
| TC006 | Dental Partial Approval — Cosmetic Exclusion | `PARTIAL` | INR 8,000 | PASS | — |
| TC007 | MRI Without Pre-Authorization | `REJECTED` | INR 0 | PASS | — |
| TC008 | Per-Claim Limit Exceeded | `REJECTED` | INR 0 | PASS | — |
| TC009 | Fraud Signal — Multiple Same-Day Claims | `MANUAL_REVIEW` | INR 0 | PASS | — |
| TC010 | Network Hospital — Discount Applied | `APPROVED` | INR 3,240 | PASS | — |
| TC011 | Component Failure — Graceful Degradation | `APPROVED` | INR 4,000 | PASS | — |
| TC012 | Excluded Treatment | `REJECTED` | INR 0 | PASS | — |

**Record live:** TC001 + TC004 on http://localhost:3000/ops. **Verify offline:** traces below.

## OCR image cases — summary

| Case | Scenario | Decision | Approved | Match |
|------|----------|----------|----------|-------|
| OCR-001 | Image OCR — Clean Consultation Approval | `APPROVED` | INR 1,350 | PASS |
| OCR-002 | Image OCR — Wrong Document (Two Prescriptions) | `PENDING` | INR 0 | PASS |
| OCR-003 | Image OCR — Patient Name Mismatch | `PENDING` | INR 0 | PASS |
| OCR-004 | Image OCR — Unreadable Blurry Bill | `PENDING` | INR 0 | PASS |
| OCR-005 | Image OCR — Pharmacy Claim | `APPROVED` | INR 800 | PASS |
| OCR-006 | Image OCR — Dental Partial Approval | `PARTIAL` | INR 8,000 | PASS |
| OCR-007 | OCR-only smoke test | OCR smoke | — | PASS |

---

## Assignment cases — detail

## TC001: Wrong Document Uploaded — **PASS**

Member submits two prescriptions for a consultation claim that requires a prescription and a hospital bill.

**Expected:** Early stop (`PENDING`) · System must: Stop before making any claim decision; Tell the member specifically what document type was uploaded and what is needed instead…

| Field | Value |
|-------|-------|
| Decision | `PENDING` |
| Approved amount | INR 0 |
| Confidence | 1.0 |
| Match | **PASS** |

**Reason:** You uploaded 2 Prescription(s) but a Hospital Bill is required for CONSULTATION claims. Please upload the missing Hospital Bill.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP001 (CONSULTATION)
   ```json
   {
  "member_id": "EMP001",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 1500.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F001: no content extracted; F002: no content extracted
   ```json
   {
  "logs": [
    "F001: no content extracted",
    "F002: no content extracted"
  ]
}
   ```
**3. gatekeeper_agent** — `FAILED`
   You uploaded 2 Prescription(s) but a Hospital Bill is required for CONSULTATION claims. Please upload the missing Hospital Bill.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "PRESCRIPTION"
  ],
  "missing_types": [
    "HOSPITAL_BILL"
  ],
  "patient_names": [],
  "used_llm": false,
  "error": null
}
   ```
**4. decision_consolidator** — `PENDING`
   You uploaded 2 Prescription(s) but a Hospital Bill is required for CONSULTATION claims. Please upload the missing Hospital Bill.
   ```json
   {
  "early_stop": true
}
   ```
**5. format_response** — `SUCCESS`
   Response ready: PENDING — INR 0
   ```json
   {
  "decision": "PENDING",
  "approved_amount": 0.0,
  "confidence_score": 1.0
}
   ```

---

## TC002: Unreadable Document — **PASS**

Member uploads a valid prescription but a blurry, unreadable photo of their pharmacy bill.

**Expected:** Early stop (`PENDING`) · System must: Identify that the pharmacy bill cannot be read; Ask the member to re-upload that specific document…

| Field | Value |
|-------|-------|
| Decision | `PENDING` |
| Approved amount | INR 0 |
| Confidence | 1.0 |
| Match | **PASS** |

**Reason:** The following document(s) could not be read: blurry_bill.jpg. Please re-upload clear photos or scans of those documents.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP004 (PHARMACY)
   ```json
   {
  "member_id": "EMP004",
  "claim_category": "PHARMACY",
  "document_count": 2,
  "claimed_amount": 800.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F003: no content extracted; F004: no content extracted
   ```json
   {
  "logs": [
    "F003: no content extracted",
    "F004: no content extracted"
  ]
}
   ```
**3. gatekeeper_agent** — `FAILED`
   The following document(s) could not be read: blurry_bill.jpg. Please re-upload clear photos or scans of those documents.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "PHARMACY_BILL"
  ],
  "missing_types": [],
  "patient_names": [],
  "used_llm": false,
  "error": null
}
   ```
**4. decision_consolidator** — `PENDING`
   The following document(s) could not be read: blurry_bill.jpg. Please re-upload clear photos or scans of those documents.
   ```json
   {
  "early_stop": true
}
   ```
**5. format_response** — `SUCCESS`
   Response ready: PENDING — INR 0
   ```json
   {
  "decision": "PENDING",
  "approved_amount": 0.0,
  "confidence_score": 1.0
}
   ```

---

## TC003: Documents Belong to Different Patients — **PASS**

The prescription is for Rajesh Kumar but the hospital bill is for a different patient, Arjun Mehta.

**Expected:** Early stop (`PENDING`) · System must: Detect that the documents belong to different people; Surface this to the member with the specific names found on each document…

| Field | Value |
|-------|-------|
| Decision | `PENDING` |
| Approved amount | INR 0 |
| Confidence | 1.0 |
| Match | **PASS** |

**Reason:** Documents belong to different patients: Arjun Mehta and Rajesh Kumar. All documents must be for the same patient. Please verify and re-upload.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP001 (CONSULTATION)
   ```json
   {
  "member_id": "EMP001",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 1500.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F005: no content extracted; F006: no content extracted
   ```json
   {
  "logs": [
    "F005: no content extracted",
    "F006: no content extracted"
  ]
}
   ```
**3. gatekeeper_agent** — `FAILED`
   Documents belong to different patients: Arjun Mehta and Rajesh Kumar. All documents must be for the same patient. Please verify and re-upload.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Rajesh Kumar",
    "Arjun Mehta"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. decision_consolidator** — `PENDING`
   Documents belong to different patients: Arjun Mehta and Rajesh Kumar. All documents must be for the same patient. Please verify and re-upload.
   ```json
   {
  "early_stop": true
}
   ```
**5. format_response** — `SUCCESS`
   Response ready: PENDING — INR 0
   ```json
   {
  "decision": "PENDING",
  "approved_amount": 0.0,
  "confidence_score": 1.0
}
   ```

---

## TC004: Clean Consultation — Full Approval — **PASS**

Complete, valid consultation claim with correct documents, valid member, covered treatment, within all limits.

**Expected:** Decision: `APPROVED` · Approved: INR 1,350 · Confidence: above 0.85

| Field | Value |
|-------|-------|
| Decision | `APPROVED` |
| Approved amount | INR 1,350 |
| Confidence | 0.95 |
| Match | **PASS** |

**Reason:** Co-pay (10%) applied on ₹1,500 = ₹150 deducted. Final: ₹1,350.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP001 (CONSULTATION)
   ```json
   {
  "member_id": "EMP001",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 1500.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F007: using pre-filled content_summary; F008: using pre-filled content_summary
   ```json
   {
  "logs": [
    "F007: using pre-filled content_summary",
    "F008: using pre-filled content_summary"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Rajesh Kumar",
    "Rajesh Kumar"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-1-regex
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": "Rajesh Kumar",
  "diagnosis": "Viral Fever",
  "total_amount": 1500.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-11-01",
  "document_dates": [
    "2024-11-01"
  ],
  "submitted_hospital_name": null,
  "document_hospital_names": [
    "City Clinic, Bengaluru"
  ]
}
   ```
**6. policy_engine** — `APPROVED`
   Co-pay (10%) applied on ₹1,500 = ₹150 deducted. Final: ₹1,350.
   ```json
   {
  "rejection_reasons": [],
  "approved_amount": 1350.0,
  "fraud_signals": [],
  "financial_breakdown": {
    "claimed_amount": 1500.0,
    "copay_percent": 10,
    "copay_amount": 150.0,
    "annual_opd_remaining": 45000.0,
    "approved_amount": 1350.0,
    "submitted_claimed_amount": 1500.0,
    "document_total_amount": 1500.0
  }
}
   ```
**7. decision_consolidator** — `APPROVED`
   Co-pay (10%) applied on ₹1,500 = ₹150 deducted. Final: ₹1,350.
   ```json
   {
  "approved_amount": 1350.0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [],
  "financial_breakdown": {
    "claimed_amount": 1500.0,
    "copay_percent": 10,
    "copay_amount": 150.0,
    "annual_opd_remaining": 45000.0,
    "approved_amount": 1350.0,
    "submitted_claimed_amount": 1500.0,
    "document_total_amount": 1500.0
  }
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: APPROVED — INR 1,350
   ```json
   {
  "decision": "APPROVED",
  "approved_amount": 1350.0,
  "confidence_score": 0.95
}
   ```

---

## TC005: Waiting Period — Diabetes — **PASS**

Member joined 2024-09-01. Claims for diabetes treatment on 2024-10-15, which is within the 90-day waiting period for diabetes.

**Expected:** Decision: `REJECTED` · Rejection reasons: WAITING_PERIOD · System must: State the date from which the member will be eligible for diabetes-related claims

| Field | Value |
|-------|-------|
| Decision | `REJECTED` |
| Approved amount | INR 0 |
| Confidence | 0.95 |
| Match | **PASS** |

**Reason:** Claim rejected due to waiting period. Eligible from 2024-11-30.

**Rejection reasons:** WAITING_PERIOD

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP005 (CONSULTATION)
   ```json
   {
  "member_id": "EMP005",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 3000.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F009: using pre-filled content_summary; F010: using pre-filled content_summary
   ```json
   {
  "logs": [
    "F009: using pre-filled content_summary",
    "F010: using pre-filled content_summary"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Vikram Joshi",
    "Vikram Joshi"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-1-regex
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": "Vikram Joshi",
  "diagnosis": "Type 2 Diabetes Mellitus",
  "total_amount": 3000.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-10-15",
  "document_dates": [
    "2024-10-15"
  ],
  "submitted_hospital_name": null,
  "document_hospital_names": []
}
   ```
**6. policy_engine** — `REJECTED`
   Claim rejected due to waiting period. Eligible from 2024-11-30.
   ```json
   {
  "rejection_reasons": [
    "WAITING_PERIOD"
  ],
  "approved_amount": 0,
  "fraud_signals": [],
  "financial_breakdown": {}
}
   ```
**7. decision_consolidator** — `REJECTED`
   Claim rejected due to waiting period. Eligible from 2024-11-30.
   ```json
   {
  "approved_amount": 0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [],
  "financial_breakdown": {}
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: REJECTED — INR 0
   ```json
   {
  "decision": "REJECTED",
  "approved_amount": 0.0,
  "confidence_score": 0.95
}
   ```

---

## TC006: Dental Partial Approval — Cosmetic Exclusion — **PASS**

Bill includes root canal treatment (covered) and teeth whitening (cosmetic, excluded). System must approve only the covered procedure.

**Expected:** Decision: `PARTIAL` · Approved: INR 8,000 · System must: Itemize which line items were approved and which were rejected; State the reason for each rejection at the line-item level

| Field | Value |
|-------|-------|
| Decision | `PARTIAL` |
| Approved amount | INR 8,000 |
| Confidence | 0.95 |
| Match | **PASS** |

**Reason:** Partial approval: covered procedures approved; excluded items rejected. Teeth Whitening: COSMETIC_EXCLUSION

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP002 (DENTAL)
   ```json
   {
  "member_id": "EMP002",
  "claim_category": "DENTAL",
  "document_count": 1,
  "claimed_amount": 12000.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F011: using pre-filled content_summary
   ```json
   {
  "logs": [
    "F011: using pre-filled content_summary"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Priya Singh"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-1-regex
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": "Priya Singh",
  "diagnosis": null,
  "total_amount": 12000.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-10-15",
  "document_dates": [],
  "submitted_hospital_name": null,
  "document_hospital_names": [
    "Smile Dental Clinic"
  ]
}
   ```
**6. policy_engine** — `PARTIAL`
   Partial approval: covered procedures approved; excluded items rejected. Teeth Whitening: COSMETIC_EXCLUSION
   ```json
   {
  "rejection_reasons": [],
  "approved_amount": 8000.0,
  "fraud_signals": [],
  "financial_breakdown": {
    "claimed_amount": 8000.0,
    "annual_opd_remaining": 50000.0,
    "approved_amount": 8000.0,
    "submitted_claimed_amount": 12000.0,
    "document_total_amount": 12000.0
  }
}
   ```
**7. decision_consolidator** — `PARTIAL`
   Partial approval: covered procedures approved; excluded items rejected. Teeth Whitening: COSMETIC_EXCLUSION
   ```json
   {
  "approved_amount": 8000.0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [
    {
      "description": "Root Canal Treatment",
      "amount": 8000.0,
      "approved": true,
      "rejection_reason": null
    },
    {
      "description": "Teeth Whitening",
      "amount": 4000.0,
      "approved": false,
      "rejection_reason": "COSMETIC_EXCLUSION"
    }
  ],
  "financial_breakdown": {
    "claimed_amount": 8000.0,
    "annual_opd_remaining": 50000.0,
    "approved_amount": 8000.0,
    "submitted_claimed_amount": 12000.0,
    "document_total_amount": 12000.0
  }
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: PARTIAL — INR 8,000
   ```json
   {
  "decision": "PARTIAL",
  "approved_amount": 8000.0,
  "confidence_score": 0.95
}
   ```

---

## TC007: MRI Without Pre-Authorization — **PASS**

MRI scan costing ₹15,000 submitted without pre-authorization. Policy requires pre-auth for MRI above ₹10,000.

**Expected:** Decision: `REJECTED` · Rejection reasons: PRE_AUTH_MISSING · System must: Explain that pre-authorization was required and not obtained; Tell the member what they should do to resubmit with pre-auth

| Field | Value |
|-------|-------|
| Decision | `REJECTED` |
| Approved amount | INR 0 |
| Confidence | 0.95 |
| Match | **PASS** |

**Reason:** Pre-authorization required for MRI above the policy threshold but was not obtained. Please obtain pre-authorization and resubmit.

**Rejection reasons:** PRE_AUTH_MISSING

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP007 (DIAGNOSTIC)
   ```json
   {
  "member_id": "EMP007",
  "claim_category": "DIAGNOSTIC",
  "document_count": 3,
  "claimed_amount": 15000.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F012: using pre-filled content_summary; F013: using pre-filled content_summary; F014: using pre-filled content_summary
   ```json
   {
  "logs": [
    "F012: using pre-filled content_summary",
    "F013: using pre-filled content_summary",
    "F014: using pre-filled content_summary"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "LAB_REPORT",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-1-regex
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": null,
  "diagnosis": "Suspected Lumbar Disc Herniation",
  "total_amount": 15000.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-11-02",
  "document_dates": [],
  "submitted_hospital_name": null,
  "document_hospital_names": []
}
   ```
**6. policy_engine** — `REJECTED`
   Pre-authorization required for MRI above the policy threshold but was not obtained. Please obtain pre-authorization and resubmit.
   ```json
   {
  "rejection_reasons": [
    "PRE_AUTH_MISSING"
  ],
  "approved_amount": 0,
  "fraud_signals": [],
  "financial_breakdown": {}
}
   ```
**7. decision_consolidator** — `REJECTED`
   Pre-authorization required for MRI above the policy threshold but was not obtained. Please obtain pre-authorization and resubmit.
   ```json
   {
  "approved_amount": 0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [],
  "financial_breakdown": {}
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: REJECTED — INR 0
   ```json
   {
  "decision": "REJECTED",
  "approved_amount": 0.0,
  "confidence_score": 0.95
}
   ```

---

## TC008: Per-Claim Limit Exceeded — **PASS**

Claimed amount of ₹7,500 exceeds the per-claim limit of ₹5,000.

**Expected:** Decision: `REJECTED` · Rejection reasons: PER_CLAIM_EXCEEDED · System must: State the per-claim limit and the claimed amount clearly in the rejection message

| Field | Value |
|-------|-------|
| Decision | `REJECTED` |
| Approved amount | INR 0 |
| Confidence | 0.95 |
| Match | **PASS** |

**Reason:** Claimed amount ₹7,500 exceeds per-claim limit of ₹5,000.

**Rejection reasons:** PER_CLAIM_EXCEEDED

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP003 (CONSULTATION)
   ```json
   {
  "member_id": "EMP003",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 7500.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F015: using pre-filled content_summary; F016: using pre-filled content_summary
   ```json
   {
  "logs": [
    "F015: using pre-filled content_summary",
    "F016: using pre-filled content_summary"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-1-regex
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": null,
  "diagnosis": "Gastroenteritis",
  "total_amount": 7500.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-10-20",
  "document_dates": [],
  "submitted_hospital_name": null,
  "document_hospital_names": []
}
   ```
**6. policy_engine** — `REJECTED`
   Claimed amount ₹7,500 exceeds per-claim limit of ₹5,000.
   ```json
   {
  "rejection_reasons": [
    "PER_CLAIM_EXCEEDED"
  ],
  "approved_amount": 0,
  "fraud_signals": [],
  "financial_breakdown": {}
}
   ```
**7. decision_consolidator** — `REJECTED`
   Claimed amount ₹7,500 exceeds per-claim limit of ₹5,000.
   ```json
   {
  "approved_amount": 0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [],
  "financial_breakdown": {}
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: REJECTED — INR 0
   ```json
   {
  "decision": "REJECTED",
  "approved_amount": 0.0,
  "confidence_score": 0.95
}
   ```

---

## TC009: Fraud Signal — Multiple Same-Day Claims — **PASS**

Member EMP008 has already submitted 3 claims today before this one arrives. This is the 4th claim from the same member on the same day.

**Expected:** Decision: `MANUAL_REVIEW` · System must: Flag the unusual same-day claim pattern; Route to manual review rather than auto-rejecting…

| Field | Value |
|-------|-------|
| Decision | `MANUAL_REVIEW` |
| Approved amount | INR 0 |
| Confidence | 0.95 |
| Match | **PASS** |

**Reason:** Unusual claim pattern detected. Routed for manual review.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP008 (CONSULTATION)
   ```json
   {
  "member_id": "EMP008",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 4800.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F017: using pre-filled content_summary; F018: using pre-filled content_summary
   ```json
   {
  "logs": [
    "F017: using pre-filled content_summary",
    "F018: using pre-filled content_summary"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-1-regex
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": null,
  "diagnosis": "Migraine",
  "total_amount": 4800.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-10-30",
  "document_dates": [],
  "submitted_hospital_name": null,
  "document_hospital_names": []
}
   ```
**6. policy_engine** — `MANUAL_REVIEW`
   Unusual claim pattern detected. Routed for manual review.
   ```json
   {
  "rejection_reasons": [],
  "approved_amount": 0,
  "fraud_signals": [
    "Same-day claims pattern: 3 prior claims on 2024-10-30"
  ],
  "financial_breakdown": {}
}
   ```
**7. decision_consolidator** — `MANUAL_REVIEW`
   Unusual claim pattern detected. Routed for manual review.
   ```json
   {
  "approved_amount": 0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [],
  "financial_breakdown": {}
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: MANUAL_REVIEW — INR 0
   ```json
   {
  "decision": "MANUAL_REVIEW",
  "approved_amount": 0.0,
  "confidence_score": 0.95
}
   ```

---

## TC010: Network Hospital — Discount Applied — **PASS**

Valid claim at Apollo Hospitals, a network hospital. Network discount must be applied before co-pay.

**Expected:** Decision: `APPROVED` · Approved: INR 3,240 · System must: Apply network discount before co-pay, not after; Show the breakdown of discount and co-pay in the decision output

| Field | Value |
|-------|-------|
| Decision | `APPROVED` |
| Approved amount | INR 3,240 |
| Confidence | 0.95 |
| Match | **PASS** |

**Reason:** Network discount (20%) applied first on ₹4,500 = ₹3,600. Co-pay (10%) applied on ₹3,600 = ₹360 deducted. Final: ₹3,240.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP010 (CONSULTATION)
   ```json
   {
  "member_id": "EMP010",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 4500.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F019: using pre-filled content_summary; F020: using pre-filled content_summary
   ```json
   {
  "logs": [
    "F019: using pre-filled content_summary",
    "F020: using pre-filled content_summary"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Deepak Shah",
    "Deepak Shah"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-1-regex
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": "Deepak Shah",
  "diagnosis": "Acute Bronchitis",
  "total_amount": 4500.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-11-03",
  "document_dates": [],
  "submitted_hospital_name": "Apollo Hospitals",
  "document_hospital_names": [
    "Apollo Hospitals"
  ]
}
   ```
**6. policy_engine** — `APPROVED`
   Network discount (20%) applied first on ₹4,500 = ₹3,600. Co-pay (10%) applied on ₹3,600 = ₹360 deducted. Final: ₹3,240.
   ```json
   {
  "rejection_reasons": [],
  "approved_amount": 3240.0,
  "fraud_signals": [],
  "financial_breakdown": {
    "claimed_amount": 4500.0,
    "network_discount_percent": 20,
    "network_discount_amount": 900.0,
    "after_network_discount": 3600.0,
    "copay_percent": 10,
    "copay_amount": 360.0,
    "annual_opd_remaining": 42000.0,
    "approved_amount": 3240.0,
    "submitted_claimed_amount": 4500.0,
    "document_total_amount": 4500.0
  }
}
   ```
**7. decision_consolidator** — `APPROVED`
   Network discount (20%) applied first on ₹4,500 = ₹3,600. Co-pay (10%) applied on ₹3,600 = ₹360 deducted. Final: ₹3,240.
   ```json
   {
  "approved_amount": 3240.0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [],
  "financial_breakdown": {
    "claimed_amount": 4500.0,
    "network_discount_percent": 20,
    "network_discount_amount": 900.0,
    "after_network_discount": 3600.0,
    "copay_percent": 10,
    "copay_amount": 360.0,
    "annual_opd_remaining": 42000.0,
    "approved_amount": 3240.0,
    "submitted_claimed_amount": 4500.0,
    "document_total_amount": 4500.0
  }
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: APPROVED — INR 3,240
   ```json
   {
  "decision": "APPROVED",
  "approved_amount": 3240.0,
  "confidence_score": 0.95
}
   ```

---

## TC011: Component Failure — Graceful Degradation — **PASS**

One component of your system fails mid-processing (simulate with the flag below). The overall pipeline must continue, produce a decision, and make the failure visible in the output with an appropriately reduced confidence score.

**Expected:** Decision: `APPROVED` · System must: Not crash or return a 500 error; Indicate in the output that a component failed and was skipped…

| Field | Value |
|-------|-------|
| Decision | `APPROVED` |
| Approved amount | INR 4,000 |
| Confidence | 0.6 |
| Match | **PASS** |

**Reason:** Claim approved for ₹4,000. Manual review recommended due to incomplete processing.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP006 (ALTERNATIVE_MEDICINE)
   ```json
   {
  "member_id": "EMP006",
  "claim_category": "ALTERNATIVE_MEDICINE",
  "document_count": 2,
  "claimed_amount": 4000.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F021: using pre-filled content_summary; F022: using pre-filled content_summary
   ```json
   {
  "logs": [
    "F021: using pre-filled content_summary",
    "F022: using pre-filled content_summary"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `DEGRADED`
   Extraction via degraded
   ```json
   {
  "confidence": 0.5,
  "error": "Simulated component failure",
  "patient_name": null,
  "diagnosis": null,
  "total_amount": 4000.0
}
   ```
   _(degraded)_
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-10-28",
  "document_dates": [],
  "submitted_hospital_name": null,
  "document_hospital_names": [
    "Ayur Wellness Centre"
  ]
}
   ```
**6. policy_engine** — `APPROVED`
   Claim approved for ₹4,000.
   ```json
   {
  "rejection_reasons": [],
  "approved_amount": 4000.0,
  "fraud_signals": [],
  "financial_breakdown": {
    "claimed_amount": 4000.0,
    "annual_opd_remaining": 50000.0,
    "approved_amount": 4000.0,
    "submitted_claimed_amount": 4000.0,
    "document_total_amount": 4000.0
  }
}
   ```
**7. decision_consolidator** — `APPROVED`
   Claim approved for ₹4,000. Manual review recommended due to incomplete processing.
   ```json
   {
  "approved_amount": 4000.0,
  "confidence_score": 0.6,
  "degraded_steps": [
    "extraction"
  ],
  "line_item_decisions": [],
  "financial_breakdown": {
    "claimed_amount": 4000.0,
    "annual_opd_remaining": 50000.0,
    "approved_amount": 4000.0,
    "submitted_claimed_amount": 4000.0,
    "document_total_amount": 4000.0
  }
}
   ```
   _(degraded)_
**8. format_response** — `SUCCESS`
   Response ready: APPROVED — INR 4,000
   ```json
   {
  "decision": "APPROVED",
  "approved_amount": 4000.0,
  "confidence_score": 0.6
}
   ```

---

## TC012: Excluded Treatment — **PASS**

Member claims for bariatric consultation and a diet program. Obesity treatment is explicitly excluded under the policy.

**Expected:** Decision: `REJECTED` · Rejection reasons: EXCLUDED_CONDITION · Confidence: above 0.90

| Field | Value |
|-------|-------|
| Decision | `REJECTED` |
| Approved amount | INR 0 |
| Confidence | 0.95 |
| Match | **PASS** |

**Reason:** Treatment falls under policy exclusions (Obesity and weight loss programs).

**Rejection reasons:** EXCLUDED_CONDITION

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP009 (CONSULTATION)
   ```json
   {
  "member_id": "EMP009",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 8000.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   F023: using pre-filled content_summary; F024: using pre-filled content_summary
   ```json
   {
  "logs": [
    "F023: using pre-filled content_summary",
    "F024: using pre-filled content_summary"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-1-regex
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": null,
  "diagnosis": "Morbid Obesity \u2014 BMI 37",
  "total_amount": 8000.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-10-18",
  "document_dates": [],
  "submitted_hospital_name": null,
  "document_hospital_names": []
}
   ```
**6. policy_engine** — `REJECTED`
   Treatment falls under policy exclusions (Obesity and weight loss programs).
   ```json
   {
  "rejection_reasons": [
    "EXCLUDED_CONDITION"
  ],
  "approved_amount": 0,
  "fraud_signals": [],
  "financial_breakdown": {}
}
   ```
**7. decision_consolidator** — `REJECTED`
   Treatment falls under policy exclusions (Obesity and weight loss programs).
   ```json
   {
  "approved_amount": 0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [],
  "financial_breakdown": {}
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: REJECTED — INR 0
   ```json
   {
  "decision": "REJECTED",
  "approved_amount": 0.0,
  "confidence_score": 0.95
}
   ```

---

## OCR image cases — detail

### OCR-001: Image OCR — Clean Consultation Approval — **PASS**

Upload real JPG images with no pasted text. OCR must extract patient, diagnosis, and line items, then approve with co-pay.

| Field | Value |
|-------|-------|
| Decision | `APPROVED` |
| Approved amount | INR 1,350 |
| Confidence | 0.95 |

**Reason:** Co-pay (10%) applied on ₹1,500 = ₹150 deducted. Final: ₹1,350.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP001 (CONSULTATION)
   ```json
   {
  "member_id": "EMP001",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 1500.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   OCR001: OCR via groq_vision (484 chars); OCR002: OCR via groq_vision (565 chars)
   ```json
   {
  "logs": [
    "OCR001: OCR via groq_vision (484 chars)",
    "OCR002: OCR via groq_vision (565 chars)"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Rajesh Kumar",
    "Rajesh Kumar"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-2-llm
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": "Rajesh Kumar",
  "diagnosis": "Viral Fever (VF)",
  "total_amount": 1500.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-11-01",
  "document_dates": [],
  "submitted_hospital_name": null,
  "document_hospital_names": [
    "City Medical Centre",
    "City Medical Centre, 12 MG Road, Bengaluru"
  ]
}
   ```
**6. policy_engine** — `APPROVED`
   Co-pay (10%) applied on ₹1,500 = ₹150 deducted. Final: ₹1,350.
   ```json
   {
  "rejection_reasons": [],
  "approved_amount": 1350.0,
  "fraud_signals": [],
  "financial_breakdown": {
    "claimed_amount": 1500.0,
    "copay_percent": 10,
    "copay_amount": 150.0,
    "annual_opd_remaining": 45000.0,
    "approved_amount": 1350.0,
    "submitted_claimed_amount": 1500.0,
    "document_total_amount": 1500.0
  }
}
   ```
**7. decision_consolidator** — `APPROVED`
   Co-pay (10%) applied on ₹1,500 = ₹150 deducted. Final: ₹1,350.
   ```json
   {
  "approved_amount": 1350.0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [],
  "financial_breakdown": {
    "claimed_amount": 1500.0,
    "copay_percent": 10,
    "copay_amount": 150.0,
    "annual_opd_remaining": 45000.0,
    "approved_amount": 1350.0,
    "submitted_claimed_amount": 1500.0,
    "document_total_amount": 1500.0
  }
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: APPROVED — INR 1,350
   ```json
   {
  "decision": "APPROVED",
  "approved_amount": 1350.0,
  "confidence_score": 0.95
}
   ```

---

### OCR-002: Image OCR — Wrong Document (Two Prescriptions) — **PASS**

Consultation needs prescription + hospital bill. Upload two prescription images.

| Field | Value |
|-------|-------|
| Decision | `PENDING` |
| Approved amount | INR 0 |
| Confidence | 1.0 |

**Reason:** You uploaded 2 Prescription(s) but a Hospital Bill is required for CONSULTATION claims. Please upload the missing Hospital Bill.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP001 (CONSULTATION)
   ```json
   {
  "member_id": "EMP001",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 1500.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   OCR001: OCR via groq_vision (484 chars); OCR002: OCR via groq_vision (255 chars)
   ```json
   {
  "logs": [
    "OCR001: OCR via groq_vision (484 chars)",
    "OCR002: OCR via groq_vision (255 chars)"
  ]
}
   ```
**3. gatekeeper_agent** — `FAILED`
   You uploaded 2 Prescription(s) but a Hospital Bill is required for CONSULTATION claims. Please upload the missing Hospital Bill.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "PRESCRIPTION"
  ],
  "missing_types": [
    "HOSPITAL_BILL"
  ],
  "patient_names": [
    "Rajesh Kumar",
    "Rajesh Kumar"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. decision_consolidator** — `PENDING`
   You uploaded 2 Prescription(s) but a Hospital Bill is required for CONSULTATION claims. Please upload the missing Hospital Bill.
   ```json
   {
  "early_stop": true
}
   ```
**5. format_response** — `SUCCESS`
   Response ready: PENDING — INR 0
   ```json
   {
  "decision": "PENDING",
  "approved_amount": 0.0,
  "confidence_score": 1.0
}
   ```

---

### OCR-003: Image OCR — Patient Name Mismatch — **PASS**

Prescription for Rajesh Kumar, hospital bill for Arjun Mehta.

| Field | Value |
|-------|-------|
| Decision | `PENDING` |
| Approved amount | INR 0 |
| Confidence | 1.0 |

**Reason:** Documents belong to different patients: Arjun Mehta and Rajesh Kumar. All documents must be for the same patient. Please verify and re-upload.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP001 (CONSULTATION)
   ```json
   {
  "member_id": "EMP001",
  "claim_category": "CONSULTATION",
  "document_count": 2,
  "claimed_amount": 1500.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   OCR001: OCR via groq_vision (473 chars); OCR002: OCR via groq_vision (336 chars)
   ```json
   {
  "logs": [
    "OCR001: OCR via groq_vision (473 chars)",
    "OCR002: OCR via groq_vision (336 chars)"
  ]
}
   ```
**3. gatekeeper_agent** — `FAILED`
   Documents belong to different patients: Arjun Mehta and Rajesh Kumar. All documents must be for the same patient. Please verify and re-upload.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Rajesh Kumar",
    "Arjun Mehta"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. decision_consolidator** — `PENDING`
   Documents belong to different patients: Arjun Mehta and Rajesh Kumar. All documents must be for the same patient. Please verify and re-upload.
   ```json
   {
  "early_stop": true
}
   ```
**5. format_response** — `SUCCESS`
   Response ready: PENDING — INR 0
   ```json
   {
  "decision": "PENDING",
  "approved_amount": 0.0,
  "confidence_score": 1.0
}
   ```

---

### OCR-004: Image OCR — Unreadable Blurry Bill — **PASS**

Good prescription image + heavily blurred pharmacy bill.

| Field | Value |
|-------|-------|
| Decision | `PENDING` |
| Approved amount | INR 0 |
| Confidence | 1.0 |

**Reason:** The following document(s) could not be read: blurry_pharmacy_bill.jpg. Please re-upload clear photos or scans of those documents.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP004 (PHARMACY)
   ```json
   {
  "member_id": "EMP004",
  "claim_category": "PHARMACY",
  "document_count": 2,
  "claimed_amount": 800.0
}
   ```
**2. ocr_agent** — `DEGRADED`
   OCR001: OCR via groq_vision (280 chars); OCR002: vision OCR marked UNREADABLE
   ```json
   {
  "logs": [
    "OCR001: OCR via groq_vision (280 chars)",
    "OCR002: vision OCR marked UNREADABLE"
  ]
}
   ```
   _(degraded)_
**3. gatekeeper_agent** — `FAILED`
   The following document(s) could not be read: blurry_pharmacy_bill.jpg. Please re-upload clear photos or scans of those documents.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "PHARMACY_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Sneha Reddy"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. decision_consolidator** — `PENDING`
   The following document(s) could not be read: blurry_pharmacy_bill.jpg. Please re-upload clear photos or scans of those documents.
   ```json
   {
  "early_stop": true
}
   ```
**5. format_response** — `SUCCESS`
   Response ready: PENDING — INR 0
   ```json
   {
  "decision": "PENDING",
  "approved_amount": 0.0,
  "confidence_score": 1.0
}
   ```

---

### OCR-005: Image OCR — Pharmacy Claim — **PASS**

Full pharmacy claim using image-only documents.

| Field | Value |
|-------|-------|
| Decision | `APPROVED` |
| Approved amount | INR 800 |
| Confidence | 0.95 |

**Reason:** Claim approved for ₹800.

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP004 (PHARMACY)
   ```json
   {
  "member_id": "EMP004",
  "claim_category": "PHARMACY",
  "document_count": 2,
  "claimed_amount": 800.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   OCR001: OCR via groq_vision (280 chars); OCR002: OCR via groq_vision (464 chars)
   ```json
   {
  "logs": [
    "OCR001: OCR via groq_vision (280 chars)",
    "OCR002: OCR via groq_vision (464 chars)"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "PRESCRIPTION",
    "PHARMACY_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Sneha Reddy",
    "Sneha Reddy"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-2-llm
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": "Sneha Reddy",
  "diagnosis": "Common Cold (CC)",
  "total_amount": 800.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-10-25",
  "document_dates": [],
  "submitted_hospital_name": null,
  "document_hospital_names": [
    "Care Plus Clinic, Hyderabad"
  ]
}
   ```
**6. policy_engine** — `APPROVED`
   Claim approved for ₹800.
   ```json
   {
  "rejection_reasons": [],
  "approved_amount": 800.0,
  "fraud_signals": [],
  "financial_breakdown": {
    "claimed_amount": 800.0,
    "annual_opd_remaining": 50000.0,
    "approved_amount": 800.0,
    "submitted_claimed_amount": 800.0,
    "document_total_amount": 800.0
  }
}
   ```
**7. decision_consolidator** — `APPROVED`
   Claim approved for ₹800.
   ```json
   {
  "approved_amount": 800.0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [],
  "financial_breakdown": {
    "claimed_amount": 800.0,
    "annual_opd_remaining": 50000.0,
    "approved_amount": 800.0,
    "submitted_claimed_amount": 800.0,
    "document_total_amount": 800.0
  }
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: APPROVED — INR 800
   ```json
   {
  "decision": "APPROVED",
  "approved_amount": 800.0,
  "confidence_score": 0.95
}
   ```

---

### OCR-006: Image OCR — Dental Partial Approval — **PASS**

Single dental bill image with root canal (covered) + teeth whitening (excluded).

| Field | Value |
|-------|-------|
| Decision | `PARTIAL` |
| Approved amount | INR 8,000 |
| Confidence | 0.95 |

**Reason:** Partial approval: covered procedures approved; excluded items rejected. Teeth Whitening (cosmetic): COSMETIC_EXCLUSION

### Execution trace

**1. ingest_submission** — `SUCCESS`
   Claim ingested for member EMP002 (DENTAL)
   ```json
   {
  "member_id": "EMP002",
  "claim_category": "DENTAL",
  "document_count": 1,
  "claimed_amount": 12000.0
}
   ```
**2. ocr_agent** — `SUCCESS`
   OCR001: OCR via groq_vision (343 chars)
   ```json
   {
  "logs": [
    "OCR001: OCR via groq_vision (343 chars)"
  ]
}
   ```
**3. gatekeeper_agent** — `SUCCESS`
   All required documents present and readable.
   ```json
   {
  "detected_types": [
    "HOSPITAL_BILL"
  ],
  "missing_types": [],
  "patient_names": [
    "Priya Singh"
  ],
  "used_llm": false,
  "error": null
}
   ```
**4. extraction_agent** — `SUCCESS`
   Extraction via tier-2-llm
   ```json
   {
  "confidence": 0.95,
  "error": null,
  "patient_name": "Priya Singh",
  "diagnosis": null,
  "total_amount": 12000.0
}
   ```
**5. submission_validator** — `SUCCESS`
   Submitted details match the extracted document data.
   ```json
   {
  "rejection_reasons": [],
  "submitted_treatment_date": "2024-10-15",
  "document_dates": [],
  "submitted_hospital_name": null,
  "document_hospital_names": [
    "Smile Dental Clinic"
  ]
}
   ```
**6. policy_engine** — `PARTIAL`
   Partial approval: covered procedures approved; excluded items rejected. Teeth Whitening (cosmetic): COSMETIC_EXCLUSION
   ```json
   {
  "rejection_reasons": [],
  "approved_amount": 8000.0,
  "fraud_signals": [],
  "financial_breakdown": {
    "claimed_amount": 8000.0,
    "annual_opd_remaining": 50000.0,
    "approved_amount": 8000.0,
    "submitted_claimed_amount": 12000.0,
    "document_total_amount": 12000.0
  }
}
   ```
**7. decision_consolidator** — `PARTIAL`
   Partial approval: covered procedures approved; excluded items rejected. Teeth Whitening (cosmetic): COSMETIC_EXCLUSION
   ```json
   {
  "approved_amount": 8000.0,
  "confidence_score": 0.95,
  "degraded_steps": [],
  "line_item_decisions": [
    {
      "description": "Root Canal Treatment (molar)",
      "amount": 8000.0,
      "approved": true,
      "rejection_reason": null
    },
    {
      "description": "Teeth Whitening (cosmetic)",
      "amount": 4000.0,
      "approved": false,
      "rejection_reason": "COSMETIC_EXCLUSION"
    }
  ],
  "financial_breakdown": {
    "claimed_amount": 8000.0,
    "annual_opd_remaining": 50000.0,
    "approved_amount": 8000.0,
    "submitted_claimed_amount": 12000.0,
    "document_total_amount": 12000.0
  }
}
   ```
**8. format_response** — `SUCCESS`
   Response ready: PARTIAL — INR 8,000
   ```json
   {
  "decision": "PARTIAL",
  "approved_amount": 8000.0,
  "confidence_score": 0.95
}
   ```

---

### OCR-007: OCR-only smoke test — **PASS**

Runs OCR step only on prescription image — quick check that Groq vision returns text.


---

