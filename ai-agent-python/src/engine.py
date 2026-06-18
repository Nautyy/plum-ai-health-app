"""Dynamic policy engine — all rules loaded from policy_terms.json."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from policy.exclusion_intent import check_claim_exclusions
from policy.line_items import category_supports_line_items, evaluate_category_line_items
from policy.pre_auth_intent import check_pre_auth_required
from policy.rules_config import PER_CLAIM_LIMIT_EXEMPT_CATEGORIES
from policy.waiting_intent import matches_waiting_condition
from schemas import (
    ClaimSubmission,
    DecisionType,
    ExtractedMedicalData,
    LineItem,
    PolicyEvaluationResult,
)

POLICY_PATH = Path(__file__).resolve().parent.parent / "config" / "policy_terms.json"


def load_policy(path: Optional[Path] = None) -> dict[str, Any]:
    policy_file = path or POLICY_PATH
    with open(policy_file, encoding="utf-8") as f:
        return json.load(f)


def _normalize_category(category: str) -> str:
    return category.lower().replace(" ", "_")


def _document_total(extracted: ExtractedMedicalData) -> Optional[float]:
    if extracted.total_amount is not None and extracted.total_amount > 0:
        return float(extracted.total_amount)
    if extracted.line_items:
        total = sum(float(item.amount or 0) for item in extracted.line_items)
        return total if total > 0 else None
    return None


def _amounts_differ_significantly(a: float, b: float, tolerance: float = 0.05) -> bool:
    if a <= 0 or b <= 0:
        return abs(a - b) > 0.01
    return abs(a - b) / max(a, b) > tolerance


def _enrich_financial_breakdown(
    submission: ClaimSubmission,
    extracted: ExtractedMedicalData,
    breakdown: dict[str, Any],
) -> dict[str, Any]:
    enriched = dict(breakdown)
    enriched["submitted_claimed_amount"] = round(float(submission.claimed_amount), 2)
    doc_total = _document_total(extracted)
    if doc_total is not None:
        enriched["document_total_amount"] = round(doc_total, 2)
    return enriched


def _claimed_amount_mismatch_note(submission: ClaimSubmission, extracted: ExtractedMedicalData) -> str:
    doc_total = _document_total(extracted)
    if doc_total is None:
        return ""
    submitted = float(submission.claimed_amount)
    if not _amounts_differ_significantly(submitted, doc_total):
        return ""
    return (
        f" Submitted amount ₹{submitted:,.0f} differs from document total "
        f"₹{doc_total:,.0f}; adjudication used extracted document amounts."
    )


def _find_member(policy: dict, member_id: str) -> Optional[dict]:
    for member in policy.get("members", []):
        if member.get("member_id") == member_id:
            return member
    return None


def _policy_effective_date(policy: dict) -> str:
    holder = policy.get("policy_holder", {})
    return (
        holder.get("policy_start_date")
        or policy.get("policy_metadata", {}).get("effective_date")
        or policy.get("policy_metadata", {}).get("start_date")
        or "2024-04-01"
    )


def _parse_date(value: str) -> datetime:
    cleaned = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unparseable date: {value!r}")


def _parse_date_safe(value: Optional[str]) -> Optional[datetime]:
    if value is None or not str(value).strip():
        return None
    try:
        return _parse_date(str(value))
    except (ValueError, TypeError):
        return None


def _member_join_date(
    policy: dict,
    member: dict,
    visited: Optional[set[str]] = None,
) -> datetime:
    """Resolve join date — dependents inherit from primary; guard circular refs."""
    visited = visited or set()
    member_id = str(member.get("member_id", ""))
    if member_id and member_id in visited:
        return _parse_date(_policy_effective_date(policy))
    if member_id:
        visited.add(member_id)

    if member.get("join_date"):
        return _parse_date(str(member["join_date"]))

    primary_id = member.get("primary_member_id")
    if primary_id:
        primary = _find_member(policy, str(primary_id))
        if primary:
            return _member_join_date(policy, primary, visited)

    return _parse_date(_policy_effective_date(policy))


def _check_waiting_period(
    policy: dict,
    member: dict,
    extracted: ExtractedMedicalData,
    treat_date: datetime,
) -> tuple[list[str], Optional[str]]:
    reasons: list[str] = []
    eligible_from: Optional[str] = None
    join_date = _member_join_date(policy, member)
    clinical = " ".join(filter(None, [extracted.diagnosis or "", extracted.treatment or ""]))

    waiting = policy.get("waiting_periods", {})
    initial_days = int(waiting.get("initial_waiting_period_days", 0) or 0)
    if (treat_date - join_date).days < initial_days:
        reasons.append("WAITING_PERIOD")
        eligible_from = (join_date + timedelta(days=initial_days)).strftime("%Y-%m-%d")
        return reasons, eligible_from

    for condition, days in waiting.get("specific_conditions", {}).items():
        try:
            wait_days = int(days)
        except (TypeError, ValueError):
            continue
        if matches_waiting_condition(policy, clinical, condition):
            eligible = join_date + timedelta(days=wait_days)
            if treat_date < eligible:
                reasons.append("WAITING_PERIOD")
                eligible_from = eligible.strftime("%Y-%m-%d")
                break

    return reasons, eligible_from


def _is_network_hospital(policy: dict, hospital_name: Optional[str]) -> bool:
    if not hospital_name:
        return False
    networks = policy.get("network_hospitals", [])
    return any(n.lower() in hospital_name.lower() or hospital_name.lower() in n.lower() for n in networks)


def _apply_financials(
    policy: dict,
    category: str,
    base_amount: float,
    hospital_name: Optional[str],
    ytd_claims: float,
) -> tuple[float, dict[str, Any]]:
    cat_key = _normalize_category(category)
    cat_rules = policy.get("opd_categories", {}).get(cat_key, {})
    coverage = policy.get("coverage", {})

    base_amount = max(0.0, float(base_amount or 0))
    ytd_claims = max(0.0, float(ytd_claims or 0))

    breakdown: dict[str, Any] = {"claimed_amount": base_amount}
    amount = base_amount

    network_discount_pct = cat_rules.get("network_discount_percent", 0)
    if network_discount_pct and _is_network_hospital(policy, hospital_name):
        discount = round(amount * network_discount_pct / 100, 2)
        amount -= discount
        breakdown["network_discount_percent"] = network_discount_pct
        breakdown["network_discount_amount"] = discount
        breakdown["after_network_discount"] = amount

    copay_pct = cat_rules.get("copay_percent", 0)
    if copay_pct:
        copay = round(amount * copay_pct / 100, 2)
        amount -= copay
        breakdown["copay_percent"] = copay_pct
        breakdown["copay_amount"] = copay

    annual_limit = coverage.get("annual_opd_limit")
    remaining_annual = annual_limit - ytd_claims if annual_limit else None
    if remaining_annual is not None:
        amount = min(amount, max(0, remaining_annual))
        breakdown["annual_opd_remaining"] = remaining_annual

    breakdown["approved_amount"] = round(amount, 2)
    return round(amount, 2), breakdown


def _check_fraud(policy: dict, submission: ClaimSubmission) -> list[str]:
    signals: list[str] = []
    fraud = policy.get("fraud_thresholds", {})
    same_day_limit = fraud.get("same_day_claims_limit", 2)

    same_day_count = sum(
        1 for h in submission.claims_history if h.date == submission.treatment_date
    )
    if same_day_count > same_day_limit:
        signals.append(
            f"Same-day claims pattern: {same_day_count} prior claims on {submission.treatment_date}"
        )

    return signals


class DynamicPolicyEngine:
    def __init__(self, policy: Optional[dict] = None):
        self.policy = policy or load_policy()

    def evaluate(
        self,
        submission: ClaimSubmission,
        extracted: ExtractedMedicalData,
    ) -> PolicyEvaluationResult:
        policy = self.policy

        if submission.claimed_amount is None or submission.claimed_amount <= 0:
            return PolicyEvaluationResult(
                decision=DecisionType.PENDING,
                reason="Claim amount must be greater than zero.",
                rejection_reasons=["INVALID_CLAIM_AMOUNT"],
            )

        treat_date = _parse_date_safe(submission.treatment_date)
        if treat_date is None:
            return PolicyEvaluationResult(
                decision=DecisionType.PENDING,
                reason="Invalid or missing treatment date. Please use format YYYY-MM-DD.",
                rejection_reasons=["INVALID_TREATMENT_DATE"],
            )

        member = _find_member(policy, submission.member_id)
        if not member:
            return PolicyEvaluationResult(
                decision=DecisionType.REJECTED,
                reason="Member not found in policy roster.",
                rejection_reasons=["MEMBER_NOT_FOUND"],
            )

        if member.get("primary_member_id") and not member.get("join_date"):
            primary = _find_member(policy, str(member["primary_member_id"]))
            if not primary:
                return PolicyEvaluationResult(
                    decision=DecisionType.MANUAL_REVIEW,
                    reason=(
                        f"Dependent {submission.member_id} is linked to missing primary member "
                        f"{member['primary_member_id']}. Routed for manual review."
                    ),
                    rejection_reasons=["PRIMARY_MEMBER_NOT_FOUND"],
                )

        cat_key = _normalize_category(submission.claim_category)
        cat_rules = policy.get("opd_categories", {}).get(cat_key)
        if not cat_rules or not cat_rules.get("covered", False):
            return PolicyEvaluationResult(
                decision=DecisionType.REJECTED,
                reason=f"Category {submission.claim_category} is not covered.",
                rejection_reasons=["CATEGORY_NOT_COVERED"],
            )

        fraud_signals = _check_fraud(policy, submission)
        if fraud_signals:
            return PolicyEvaluationResult(
                decision=DecisionType.MANUAL_REVIEW,
                reason="Unusual claim pattern detected. Routed for manual review.",
                fraud_signals=fraud_signals,
            )

        exclusion = check_claim_exclusions(policy, extracted, submission.claim_category)
        if exclusion:
            return PolicyEvaluationResult(
                decision=DecisionType.REJECTED,
                reason=f"Treatment falls under policy exclusions ({exclusion.label}).",
                rejection_reasons=[exclusion.reason_code],
                confidence=0.95,
            )

        waiting_reasons, eligible_from = _check_waiting_period(
            policy, member, extracted, treat_date
        )
        if waiting_reasons:
            msg = "Claim rejected due to waiting period."
            if eligible_from:
                msg += f" Eligible from {eligible_from}."
            return PolicyEvaluationResult(
                decision=DecisionType.REJECTED,
                reason=msg,
                rejection_reasons=waiting_reasons,
                eligible_from_date=eligible_from,
            )

        pre_auth_test = check_pre_auth_required(
            policy,
            submission.claim_category,
            extracted,
            submission.claimed_amount,
            submission.pre_authorization_id,
        )
        if pre_auth_test:
            return PolicyEvaluationResult(
                decision=DecisionType.REJECTED,
                reason=(
                    f"Pre-authorization required for {pre_auth_test} above the policy threshold "
                    "but was not obtained. Please obtain pre-authorization and resubmit."
                ),
                rejection_reasons=["PRE_AUTH_MISSING"],
            )

        per_claim_limit = policy.get("coverage", {}).get("per_claim_limit")
        if (
            cat_key not in PER_CLAIM_LIMIT_EXEMPT_CATEGORIES
            and per_claim_limit
            and submission.claimed_amount > per_claim_limit
        ):
            return PolicyEvaluationResult(
                decision=DecisionType.REJECTED,
                reason=(
                    f"Claimed amount ₹{submission.claimed_amount:,.0f} exceeds "
                    f"per-claim limit of ₹{per_claim_limit:,.0f}."
                ),
                rejection_reasons=["PER_CLAIM_EXCEEDED"],
            )

        hospital = extracted.hospital_name or submission.hospital_name

        if category_supports_line_items(policy, cat_key):
            line_decisions, approved_base = evaluate_category_line_items(
                policy, cat_key, extracted
            )
            if approved_base <= 0:
                return PolicyEvaluationResult(
                    decision=DecisionType.REJECTED,
                    reason="No covered procedures found in the claim.",
                    rejection_reasons=["NO_COVERED_ITEMS"],
                    line_item_decisions=line_decisions,
                )
            partial = approved_base < (extracted.total_amount or submission.claimed_amount)
            approved, breakdown = _apply_financials(
                policy, submission.claim_category, approved_base, hospital, submission.ytd_claims_amount
            )
            breakdown = _enrich_financial_breakdown(submission, extracted, breakdown)
            decision = DecisionType.PARTIAL if partial else DecisionType.APPROVED
            reason = "Partial approval: covered procedures approved; excluded items rejected."
            if partial:
                rejected = [d for d in line_decisions if not d.approved]
                if rejected:
                    reason += " " + "; ".join(
                        f"{d.description}: {d.rejection_reason}" for d in rejected
                    )
            reason += _claimed_amount_mismatch_note(submission, extracted)
            return PolicyEvaluationResult(
                decision=decision,
                approved_amount=approved,
                reason=reason,
                line_item_decisions=line_decisions,
                financial_breakdown=breakdown,
            )

        base_amount = extracted.total_amount or submission.claimed_amount
        approved, breakdown = _apply_financials(
            policy, submission.claim_category, base_amount, hospital, submission.ytd_claims_amount
        )
        breakdown = _enrich_financial_breakdown(submission, extracted, breakdown)

        return PolicyEvaluationResult(
            decision=DecisionType.APPROVED,
            approved_amount=approved,
            reason=self._build_approval_reason(breakdown) + _claimed_amount_mismatch_note(submission, extracted),
            financial_breakdown=breakdown,
        )

    def _build_approval_reason(self, breakdown: dict[str, Any]) -> str:
        parts = []
        if breakdown.get("network_discount_amount"):
            parts.append(
                f"Network discount ({breakdown['network_discount_percent']}%) applied first "
                f"on ₹{breakdown['claimed_amount']:,.0f} = ₹{breakdown['after_network_discount']:,.0f}."
            )
        if breakdown.get("copay_amount"):
            base = breakdown.get("after_network_discount", breakdown["claimed_amount"])
            parts.append(
                f"Co-pay ({breakdown['copay_percent']}%) applied on ₹{base:,.0f} = "
                f"₹{breakdown['copay_amount']:,.0f} deducted."
            )
        if parts:
            parts.append(f"Final: ₹{breakdown['approved_amount']:,.0f}.")
            return " ".join(parts)
        return f"Claim approved for ₹{breakdown['approved_amount']:,.0f}."
