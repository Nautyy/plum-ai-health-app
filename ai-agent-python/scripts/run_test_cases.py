"""Run all test cases from test_cases.json against the adjudication graph."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from adjudication_api import build_submission_from_dict, run_adjudication  # noqa: E402


def load_cases() -> list[dict]:
    candidates = [
        ROOT.parent / "assignment" / "test_cases.json",
        ROOT.parent.parent / "test_cases.json",
        ROOT / "test_cases.json",
    ]
    for path in candidates:
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                return json.load(f)["test_cases"]
    raise FileNotFoundError(
        "test_cases.json not found. Expected at assignment/test_cases.json, repo root, or ai-agent-python/"
    )


def evaluate_case(case: dict, result) -> tuple[bool, list[str]]:
    expected = case["expected"]
    failures: list[str] = []
    case_id = case["case_id"]

    exp_decision = expected.get("decision")
    if exp_decision is None:
        if result.decision.value not in ("PENDING",):
            failures.append(f"Expected early stop (PENDING), got {result.decision.value}")
    else:
        if result.decision.value != exp_decision:
            failures.append(f"Expected decision {exp_decision}, got {result.decision.value}")

    if expected.get("approved_amount") is not None:
        if result.approved_amount != expected["approved_amount"]:
            failures.append(
                f"Expected approved_amount {expected['approved_amount']}, got {result.approved_amount}"
            )

    for reason in expected.get("rejection_reasons", []):
        if reason not in result.rejection_reasons:
            failures.append(f"Missing rejection reason: {reason}")

    if expected.get("confidence_score") == "above 0.85":
        if result.confidence_score <= 0.85:
            failures.append(f"Expected confidence > 0.85, got {result.confidence_score}")

    if expected.get("confidence_score") == "above 0.90":
        if result.confidence_score <= 0.90:
            failures.append(f"Expected confidence > 0.90, got {result.confidence_score}")

    combined = (result.reason + " " + json.dumps([t.model_dump() for t in result.execution_trace])).lower()

    for requirement in expected.get("system_must", []):
        req_lower = requirement.lower()
        if "wrong document" in case["case_name"].lower() or case_id == "TC001":
            if "prescription" not in combined and "hospital" not in combined:
                failures.append("TC001: message must name uploaded and required document types")
        if case_id == "TC002":
            if "re-upload" not in combined and "upload" not in combined:
                failures.append("TC002: must ask member to re-upload unreadable document")
        if case_id == "TC003":
            if "rajesh" not in combined or "arjun" not in combined:
                failures.append("TC003: must surface patient names from documents")
        if case_id == "TC005":
            if "eligible" not in combined and "waiting" not in combined:
                failures.append("TC005: must state waiting period / eligibility date")
        if case_id == "TC007":
            if "pre-auth" not in combined and "pre-authorization" not in combined:
                failures.append("TC007: must explain pre-authorization requirement")
        if case_id == "TC008":
            if "5000" not in combined and "5,000" not in combined:
                failures.append("TC008: must state per-claim limit")
        if case_id == "TC009":
            if "same-day" not in combined and "same day" not in combined:
                failures.append("TC009: must flag same-day claim pattern")
        if case_id == "TC011":
            if result.confidence_score >= 0.95:
                failures.append("TC011: confidence should be reduced after component failure")
            if "manual review" not in combined and "component" not in combined and "degraded" not in combined:
                failures.append("TC011: must indicate degraded/failed component")
        if "network discount" in req_lower and case_id == "TC010":
            if "network" not in combined:
                failures.append("TC010: must mention network discount in output")

    return len(failures) == 0, failures


def main() -> int:
    cases = load_cases()
    passed = 0
    print(f"Running {len(cases)} test cases...\n")

    for case in cases:
        submission = build_submission_from_dict(case["input"])
        result = run_adjudication(submission)
        ok, failures = evaluate_case(case, result)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['case_id']}: {case['case_name']}")
        print(f"       decision={result.decision.value} approved=INR {result.approved_amount} confidence={result.confidence_score}")
        if not ok:
            for f in failures:
                print(f"       X {f}")
            print(f"       reason: {result.reason[:120].encode('ascii', 'replace').decode()}...")
        print()
        if ok:
            passed += 1

    print(f"Results: {passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
