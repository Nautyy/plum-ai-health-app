"""Generate EVAL_REPORT.md from test_cases.json."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORM = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from adjudication_api import build_submission_from_dict, run_adjudication  # noqa: E402
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

    out_path = PLATFORM / "EVAL_REPORT.md"
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Eval Report — Plum Claims Adjudication\n\n")
        f.write("> **Demo recording?** Show the **summary table below** first, then scroll to **TC001** and **TC004** for the two live demos.\n\n")
        f.write(f"Generated: {generated}  \n")
        f.write("Source: `assignment/test_cases.json` (12 assignment cases)  \n")
        f.write(f"**Summary: {passed}/{len(cases)} matched expected outcomes**\n\n")

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
        f.write("\n**Record live:** TC001 + TC004 on http://localhost:3000/ops. **Verify offline:** all 12 traces below.\n\n")
        f.write("---\n\n")

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

    print(f"Wrote {out_path} ({passed}/{len(cases)} passed)")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
