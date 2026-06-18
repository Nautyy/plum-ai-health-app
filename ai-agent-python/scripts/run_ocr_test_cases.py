"""Run OCR test cases from sample-documents/ocr_test_cases.json."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT.parent / "sample-documents"
sys.path.insert(0, str(ROOT / "src"))

from adjudication_api import build_submission_from_dict, run_adjudication  # noqa: E402
from ocr.document_ocr import run_ocr_on_documents  # noqa: E402
from schemas import ClaimDocument  # noqa: E402


def load_file_b64(relative_path: str) -> str:
    path = SAMPLES / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Missing sample file: {path}")
    return base64.b64encode(path.read_bytes()).decode()


def build_documents(case: dict) -> list[ClaimDocument]:
    docs: list[ClaimDocument] = []
    for i, ref in enumerate(case.get("files", []), start=1):
        docs.append(
            ClaimDocument(
                file_id=f"OCR{i:03d}",
                file_name=Path(ref["path"]).name,
                actual_type=ref["actual_type"],
                mime_type=ref.get("mime_type", "image/jpeg"),
                file_content_base64=load_file_b64(ref["path"]),
            )
        )
    return docs


def build_submission(case: dict):
    payload = dict(case.get("input", {}))
    payload["documents"] = [
        {
            "file_id": doc.file_id,
            "file_name": doc.file_name,
            "actual_type": doc.actual_type,
            "mime_type": doc.mime_type,
            "file_content_base64": doc.file_content_base64,
        }
        for doc in build_documents(case)
    ]
    return build_submission_from_dict(payload)


def check_ocr_only(case: dict, docs: list[ClaimDocument]) -> tuple[bool, list[str]]:
    expected = case["expected"]
    failures: list[str] = []
    text = " ".join(d.content_summary or "" for d in docs).lower()
    min_chars = expected.get("min_chars_extracted", 0)
    if len(text) < min_chars:
        failures.append(f"Expected >= {min_chars} chars from OCR, got {len(text)}")
    for needle in expected.get("text_must_include", []):
        if needle.lower() not in text:
            failures.append(f"OCR text missing: {needle}")
    return len(failures) == 0, failures


def check_adjudication(case: dict, result) -> tuple[bool, list[str]]:
    expected = case["expected"]
    failures: list[str] = []
    combined = (
        result.reason
        + " "
        + json.dumps(result.model_dump())
    ).lower()

    exp_decision = expected.get("decision")
    if exp_decision and result.decision.value != exp_decision:
        failures.append(f"Expected decision {exp_decision}, got {result.decision.value}")

    if expected.get("approved_amount") is not None:
        if result.approved_amount != expected["approved_amount"]:
            failures.append(
                f"Expected approved_amount {expected['approved_amount']}, got {result.approved_amount}"
            )

    for needle in expected.get("ocr_must_extract", []):
        if str(needle).lower() not in combined:
            failures.append(f"Output missing expected OCR content: {needle}")

    trace_needle = expected.get("trace_must_include")
    if trace_needle and trace_needle.lower() not in combined:
        failures.append(f"Trace missing: {trace_needle}")

    for req in expected.get("system_must", []):
        req_lower = req.lower()
        if "prescription" in req_lower and "hospital" in req_lower:
            if "prescription" not in combined or "hospital" not in combined:
                failures.append("Must mention Prescription and Hospital Bill")
        elif "re-upload" in req_lower or "unreadable" in req_lower:
            if "upload" not in combined and "read" not in combined:
                failures.append("Must ask to re-upload unreadable document")
        elif "rajesh" in req_lower or "arjun" in req_lower:
            if "rajesh" not in combined or "arjun" not in combined:
                failures.append("Must surface Rajesh and Arjun patient names")

    return len(failures) == 0, failures


def main() -> int:
    cases_path = SAMPLES / "ocr_test_cases.json"
    with open(cases_path, encoding="utf-8") as f:
        data = json.load(f)
    cases = data["test_cases"]

    if not SAMPLES.is_dir():
        print(f"Run generate_sample_documents.py first — missing {SAMPLES}")
        return 1

    passed = 0
    print(f"Running {len(cases)} OCR test cases from {cases_path.name}\n")

    for case in cases:
        ocr_only = case.get("ocr_only", False)
        try:
            documents = build_documents(case)
        except FileNotFoundError as exc:
            print(f"[SKIP] {case['case_id']}: {exc}")
            continue

        if ocr_only:
            updated, logs, degraded = run_ocr_on_documents(documents)
            ok, failures = check_ocr_only(case, updated)
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {case['case_id']}: {case['case_name']}")
            for line in logs:
                print(f"       {line}")
            if degraded:
                print("       (OCR degraded)")
        else:
            submission = build_submission(case)
            result = run_adjudication(submission)
            ok, failures = check_adjudication(case, result)
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {case['case_id']}: {case['case_name']}")
            print(
                f"       decision={result.decision.value} "
                f"approved=INR {result.approved_amount} "
                f"confidence={result.confidence_score}"
            )
            if not ok:
                print(f"       reason: {result.reason[:140]}...")

        if not ok:
            for f in failures:
                print(f"       X {f}")
        print()
        if ok:
            passed += 1

    ran = sum(1 for c in cases if all((SAMPLES / ref["path"]).is_file() for ref in c.get("files", [])))
    print(f"Results: {passed}/{ran} passed")
    return 0 if passed == ran else 1


if __name__ == "__main__":
    raise SystemExit(main())
