"""Generate EVAL_REPORT.md from test_cases.json and OCR cases."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

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

REPORT_INTRO = (
    "> Show the **summary tables** first, then **TC001** and **TC004** for live demos. "
    "OCR image cases (OCR-001–OCR-006) validate Groq vision on `sample-documents/`.\n\n"
    "> Each case lists **Reason (ops / audit)** and **Member-facing summary** (`member_reason`). "
    "Ops traces may include codes like `COSMETIC_EXCLUSION`; member copy does not.\n\n"
)


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


def write_result_summary(f: TextIO, result: Any, status: str) -> None:
    f.write("| Field | Value |\n|-------|-------|\n")
    f.write(f"| Decision | `{result.decision.value}` |\n")
    f.write(f"| Approved amount | INR {result.approved_amount:,.0f} |\n")
    f.write(f"| Confidence | {result.confidence_score} |\n")
    f.write(f"| Match | **{status}** |\n\n")
    write_reason_sections(f, result)


def write_reason_sections(f: TextIO, result: Any) -> None:
    f.write(f"**Reason (ops / audit):** {result.reason}\n\n")
    if result.member_reason:
        f.write(f"**Member-facing summary:** {result.member_reason}\n\n")
    if result.rejection_reasons:
        f.write(f"**Rejection reasons:** {', '.join(result.rejection_reasons)}\n\n")


def write_failures(f: TextIO, failures: list[str]) -> None:
    if not failures:
        return
    f.write("**Failures:**\n")
    for fail in failures:
        f.write(f"- {fail}\n")
    f.write("\n")


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


def write_assignment_case_section(
    f: TextIO,
    case: dict,
    result: Any,
    ok: bool,
    failures: list[str],
) -> None:
    status = "PASS" if ok else "FAIL"
    f.write(f"## {case['case_id']}: {case['case_name']} — **{status}**\n\n")
    f.write(f"{case.get('description', '')}\n\n")
    f.write(f"**Expected:** {expected_summary(case)}\n\n")
    write_result_summary(f, result, status)
    write_failures(f, failures)
    f.write("### Execution trace\n\n")
    f.write(format_trace(result.execution_trace))
    f.write("\n\n---\n\n")


def write_ocr_case_section(
    f: TextIO,
    case: dict,
    result: object | None,
    ok: bool,
    failures: list[str],
) -> None:
    status = "PASS" if ok else "FAIL"
    f.write(f"### {case['case_id']}: {case['case_name']} — **{status}**\n\n")
    f.write(f"{case.get('description', '')}\n\n")

    if case.get("ocr_only"):
        write_failures(f, failures)
        f.write("---\n\n")
        return

    write_result_summary(f, result, status)  # type: ignore[arg-type]
    write_failures(f, failures)
    f.write("### Execution trace\n\n")
    f.write(format_trace(result.execution_trace))  # type: ignore[union-attr]
    f.write("\n\n---\n\n")


def extract_preserved_ocr_sections(report_path: Path) -> tuple[str, str, str]:
    """Return (ocr_summary_block, ocr_detail_block, ocr_score) from an existing report."""
    if not report_path.is_file():
        return "", "", f"?/?"

    text = report_path.read_text(encoding="utf-8")
    summary_start = text.find("## OCR image cases — summary")
    assignment_start = text.find("## Assignment cases — detail")
    ocr_detail_start = text.find("## OCR image cases — detail")

    summary = ""
    detail = ""
    if summary_start != -1 and assignment_start != -1:
        summary = text[summary_start:assignment_start].rstrip() + "\n\n"
    if ocr_detail_start != -1:
        detail = text[ocr_detail_start:]

    match = re.search(r"(\d+/\d+) OCR cases matched expected outcomes", text)
    ocr_score = match.group(1) if match else "?/?"
    return summary, detail, ocr_score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate EVAL_REPORT.md")
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Regenerate assignment cases only; reuse OCR sections from existing EVAL_REPORT.md",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_cases()
    rows: list[tuple[dict, Any, bool, list[str]]] = []
    passed = 0

    for case in cases:
        result = run_adjudication(build_submission_from_dict(case["input"]))
        ok, failures = evaluate_case(case, result)
        if ok:
            passed += 1
        rows.append((case, result, ok, failures))

    ocr_cases = load_ocr_cases()
    out_path = PLATFORM / "EVAL_REPORT.md"
    ocr_rows: list[tuple[dict, object | None, bool, list[str]]] = []
    ocr_passed = 0
    preserved_summary = ""
    preserved_detail = ""

    if args.skip_ocr:
        preserved_summary, preserved_detail, ocr_summary = extract_preserved_ocr_sections(out_path)
        if not preserved_summary or not preserved_detail:
            print("Warning: --skip-ocr set but OCR sections missing in existing EVAL_REPORT.md")
    else:
        for case in ocr_cases:
            ok, result, failures = run_ocr_case(case)
            if ok:
                ocr_passed += 1
            ocr_rows.append((case, result, ok, failures))
        ocr_summary = f"{ocr_passed}/{len(ocr_cases)}"

    pytest_count = count_pytest()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Eval Report — Plum Claims Adjudication\n\n")
        f.write(REPORT_INTRO)
        f.write(f"Generated: {generated}  \n")
        f.write("Sources: `assignment/test_cases.json` (12 cases) · `sample-documents/ocr_test_cases.json` (7 cases)  \n")
        if pytest_count:
            f.write(f"Unit tests: **{pytest_count}** (`uv run pytest`)  \n")
        f.write(
            f"**Summary: {passed}/{len(cases)} assignment cases · "
            f"{ocr_summary} OCR cases matched expected outcomes**\n\n"
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

        if args.skip_ocr:
            f.write(preserved_summary)
        else:
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
            f.write("\n")

        f.write("---\n\n## Assignment cases — detail\n\n")
        for case, result, ok, failures in rows:
            write_assignment_case_section(f, case, result, ok, failures)

        if args.skip_ocr:
            f.write(preserved_detail)
        else:
            f.write("## OCR image cases — detail\n\n")
            for case, result, ok, failures in ocr_rows:
                write_ocr_case_section(f, case, result, ok, failures)

    return finish(passed, len(cases), ocr_passed if not args.skip_ocr else -1, len(ocr_cases), out_path)


def finish(assignment_passed: int, assignment_total: int, ocr_passed: int, ocr_total: int, out_path: Path) -> int:
    if ocr_passed >= 0:
        print(f"Wrote {out_path} ({assignment_passed}/{assignment_total} assignment, {ocr_passed}/{ocr_total} OCR)")
        ok = assignment_passed == assignment_total and ocr_passed == ocr_total
    else:
        print(f"Wrote {out_path} ({assignment_passed}/{assignment_total} assignment; OCR sections preserved)")
        ok = assignment_passed == assignment_total
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
