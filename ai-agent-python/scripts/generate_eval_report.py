"""Generate EVAL_REPORT.md from test_cases.json and OCR cases."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORM = ROOT.parent
SAMPLES = PLATFORM / "sample-documents"
sys.path.insert(0, str(ROOT / "src"))

from adjudication_api import build_submission_from_dict, run_adjudication  # noqa: E402
from ocr.document_ocr import run_ocr_on_documents  # noqa: E402
from run_ocr_test_cases import (  # noqa: E402
    build_documents,
    build_submission,
    check_adjudication,
    check_ocr_only,
)
from run_test_cases import evaluate_case, load_cases  # noqa: E402


def format_trace(trace) -> str:
    lines = []
    for i, entry in enumerate(trace, 1):
        lines.append(f"**{i}. {entry.step}** — `{entry.status}`")
        if entry.message:
            lines.append(f"   {entry.message}")
        if entry.details:
            lines.append(f"   ```json\n   {json.dumps(entry.details, indent=2)}\n   ```")
        if entry.degraded:
            lines.append("   _(degraded)_")
    return "\n".join(lines)


def expected_summary(case: dict) -> str:
    exp = case["expected"]
    parts = []
    if exp.get("decision") is None:
        parts.append("Early stop (`PENDING`)")
    else:
        parts.append(f"Decision: `{exp['decision']}`")
    if exp.get("approved_amount") is not None:
        parts.append(f"Approved: INR {exp['approved_amount']:,}")
    if exp.get("rejection_reasons"):
        parts.append(f"Rejection reasons: {', '.join(exp['rejection_reasons'])}")
    if exp.get("confidence_score"):
        parts.append(f"Confidence: {exp['confidence_score']}")
    if exp.get("system_must"):
        parts.append("System must: " + "; ".join(exp["system_must"][:2]) + ("…" if len(exp["system_must"]) > 2 else ""))
    return " · ".join(parts)


def count_pytest() -> int | None:
    try:
        proc = subprocess.run(
            ["uv", "run", "pytest", "-q", "--co", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip().endswith(".py")]
        return len(lines) if lines else None
    except OSError:
        return None


def load_ocr_cases() -> list[dict]:
    path = SAMPLES / "ocr_test_cases.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["test_cases"]


def run_ocr_case(case: dict) -> tuple[bool, object | None, list[str]]:
    if not all((SAMPLES / ref["path"]).is_file() for ref in case.get("files", [])):
        return False, None, ["Missing sample image file(s)"]

    if case.get("ocr_only"):
        documents = build_documents(case)
        updated, _, _ = run_ocr_on_documents(documents)
        ok, failures = check_ocr_only(case, updated)
        return ok, updated, failures

    result = run_adjudication(build_submission(case))
    ok, failures = check_adjudication(case, result)
    return ok, result, failures


def main() -> int:
    cases = load_cases()
    rows = []
    passed = 0

    for case in cases:
        result = run_adjudication(build_submission_from_dict(case["input"]))
        ok, failures = evaluate_case(case, result)
        if ok:
            passed += 1
        rows.append((case, result, ok, failures))

    ocr_cases = load_ocr_cases()
    ocr_rows: list[tuple[dict, object | None, bool, list[str]]] = []
    ocr_passed = 0
    for case in ocr_cases:
        ok, result, failures = run_ocr_case(case)
        if ok:
            ocr_passed += 1
        ocr_rows.append((case, result, ok, failures))

    pytest_count = count_pytest()

    out_path = PLATFORM / "EVAL_REPORT.md"
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Eval Report — Plum Claims Adjudication\n\n")
        f.write("> Show the **summary tables** first, then **TC001** and **TC004** for live demos. ")
        f.write("OCR image cases (OCR-001–OCR-006) validate Groq vision on `sample-documents/`.\n\n")
        f.write(f"Generated: {generated}  \n")
        f.write("Sources: `assignment/test_cases.json` (12 cases) · `sample-documents/ocr_test_cases.json` (7 cases)  \n")
        if pytest_count:
            f.write(f"Unit tests: **{pytest_count}** (`uv run pytest`)  \n")
        f.write(
            f"**Summary: {passed}/{len(cases)} assignment cases · "
            f"{ocr_passed}/{len(ocr_cases)} OCR cases matched expected outcomes**\n\n"
        )

        f.write("## Demo guide — show this table first\n\n")
        f.write("| Case | Scenario | Decision | Approved | Match | Live demo? |\n")
        f.write("|------|----------|----------|----------|-------|------------|\n")
        for case, result, ok, _ in rows:
            status = "PASS" if ok else "FAIL"
            decision = result.decision.value
            amount = f"INR {result.approved_amount:,.0f}"
            live = "**Yes** — early stop" if case["case_id"] == "TC001" else (
                "**Yes** — full approval" if case["case_id"] == "TC004" else "—"
            )
            f.write(
                f"| {case['case_id']} | {case['case_name']} | `{decision}` | {amount} | {status} | {live} |\n"
            )
        f.write("\n**Record live:** TC001 + TC004 on http://localhost:3000/ops. **Verify offline:** traces below.\n\n")
        f.write("## OCR image cases — summary\n\n")
        f.write("| Case | Scenario | Decision | Approved | Match |\n")
        f.write("|------|----------|----------|----------|-------|\n")
        for case, result, ok, _ in ocr_rows:
            status = "PASS" if ok else "FAIL"
            if case.get("ocr_only"):
                f.write(f"| {case['case_id']} | {case['case_name']} | OCR smoke | — | {status} |\n")
                continue
            decision = result.decision.value  # type: ignore[union-attr]
            amount = f"INR {result.approved_amount:,.0f}"  # type: ignore[union-attr]
            f.write(f"| {case['case_id']} | {case['case_name']} | `{decision}` | {amount} | {status} |\n")
        f.write("\n---\n\n")
        f.write("## Assignment cases — detail\n\n")

        for case, result, ok, failures in rows:
            status = "PASS" if ok else "FAIL"
            f.write(f"## {case['case_id']}: {case['case_name']} — **{status}**\n\n")
            f.write(f"{case.get('description', '')}\n\n")
            f.write(f"**Expected:** {expected_summary(case)}\n\n")
            f.write("| Field | Value |\n|-------|-------|\n")
            f.write(f"| Decision | `{result.decision.value}` |\n")
            f.write(f"| Approved amount | INR {result.approved_amount:,.0f} |\n")
            f.write(f"| Confidence | {result.confidence_score} |\n")
            f.write(f"| Match | **{status}** |\n\n")
            f.write(f"**Reason:** {result.reason}\n\n")
            if result.rejection_reasons:
                f.write(f"**Rejection reasons:** {', '.join(result.rejection_reasons)}\n\n")
            if failures:
                f.write("**Failures:**\n")
                for fail in failures:
                    f.write(f"- {fail}\n")
                f.write("\n")
            f.write("### Execution trace\n\n")
            f.write(format_trace(result.execution_trace))
            f.write("\n\n---\n\n")

        f.write("## OCR image cases — detail\n\n")
        for case, result, ok, failures in ocr_rows:
            status = "PASS" if ok else "FAIL"
            f.write(f"### {case['case_id']}: {case['case_name']} — **{status}**\n\n")
            f.write(f"{case.get('description', '')}\n\n")
            if case.get("ocr_only"):
                if failures:
                    f.write("**Failures:**\n")
                    for fail in failures:
                        f.write(f"- {fail}\n")
                f.write("\n---\n\n")
                continue
            f.write("| Field | Value |\n|-------|-------|\n")
            f.write(f"| Decision | `{result.decision.value}` |\n")  # type: ignore[union-attr]
            f.write(f"| Approved amount | INR {result.approved_amount:,.0f} |\n")  # type: ignore[union-attr]
            f.write(f"| Confidence | {result.confidence_score} |\n\n")  # type: ignore[union-attr]
            f.write(f"**Reason:** {result.reason}\n\n")  # type: ignore[union-attr]
            if failures:
                f.write("**Failures:**\n")
                for fail in failures:
                    f.write(f"- {fail}\n")
                f.write("\n")
            f.write("### Execution trace\n\n")
            f.write(format_trace(result.execution_trace))  # type: ignore[union-attr]
            f.write("\n\n---\n\n")

    print(f"Wrote {out_path} ({passed}/{len(cases)} assignment, {ocr_passed}/{len(ocr_cases)} OCR)")
    return 0 if passed == len(cases) and ocr_passed == len(ocr_cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
