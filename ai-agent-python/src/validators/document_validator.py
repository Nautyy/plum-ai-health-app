"""Document validation — deterministic gatekeeper rules."""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from engine import load_policy
from extractors.structured_parser import (
    extract_patient_name,
    is_plausible_person_name,
    parse_text_summary,
)
from llm.patient import extract_patient_name_llm
from ocr.document_ocr import OCR_SOURCES
from schemas import ClaimDocument, ClaimSubmission, GatekeeperResult
from validators.document_type import infer_document_type, is_document_unreadable


def _find_member(policy: dict, member_id: str) -> Optional[dict]:
    for member in policy.get("members", []):
        if member.get("member_id") == member_id:
            return member
    return None


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _allowed_patient_names(
    policy: dict,
    member_id: str,
    claim_for: Optional[str] = None,
) -> list[str]:
    member = _find_member(policy, member_id)
    if not member:
        return []

    if member.get("primary_member_id"):
        self_name = str(member.get("name", "")).strip()
        return [self_name] if self_name else []

    claim_for_key = (claim_for or "").strip().upper()
    self_name = str(member.get("name", "")).strip()

    if claim_for_key == "SELF":
        return [self_name] if self_name else []

    relationship_map = {
        "SPOUSE": "SPOUSE",
        "CHILD": "CHILD",
        "PARENT": "PARENT",
    }
    target_rel = relationship_map.get(claim_for_key)
    if target_rel:
        names: list[str] = []
        for dep in policy.get("members", []):
            if dep.get("primary_member_id") == member.get("member_id"):
                if str(dep.get("relationship", "")).upper() == target_rel:
                    dep_name = str(dep.get("name", "")).strip()
                    if dep_name:
                        names.append(dep_name)
        return names

    names = []
    if self_name:
        names.append(self_name)

    for dep in policy.get("members", []):
        if dep.get("primary_member_id") == member.get("member_id"):
            dep_name = str(dep.get("name", "")).strip()
            if dep_name:
                names.append(dep_name)

    return names


def _claim_for_coverage_message(claim_for: str) -> str:
    label = claim_for.lower().replace("_", " ")
    return (
        f"No {label} is enrolled on your policy under employee ID entered. "
        "Check your employee ID or select who the claim is for."
    )


def _patient_matches_member(patient: str, allowed: list[str]) -> bool:
    patient_norm = _normalize_name(patient)
    return any(_normalize_name(name) == patient_norm for name in allowed if name)


def _find_member_id_by_patient_name(policy: dict, patient_name: str) -> Optional[str]:
    target = _normalize_name(patient_name)
    for member in policy.get("members", []):
        name = str(member.get("name", "")).strip()
        if name and _normalize_name(name) == target:
            return str(member.get("member_id", "")) or None
    return None


def _member_id_mismatch_message(
    submission: ClaimSubmission,
    patient_names: list[str],
    policy: dict,
) -> str:
    for patient in dict.fromkeys(patient_names):
        doc_member_id = _find_member_id_by_patient_name(policy, patient)
        if doc_member_id and doc_member_id != submission.member_id:
            return (
                f"Member ID mismatch: claim submitted for {submission.member_id}, "
                f"but documents match member {doc_member_id}. "
                "Please use the correct member ID or upload documents for the member you entered."
            )
    return (
        f"Documents do not match member ID {submission.member_id}. "
        "Please verify your member ID and upload documents for that member."
    )


def _clean_patient_name(name: str) -> str:
    cleaned = re.sub(r"^[\s*\-•]+", "", name).strip().strip("*")
    return re.sub(r"\s+", " ", cleaned)


def _extract_patient_name(doc: ClaimDocument) -> Optional[str]:
    if doc.patient_name_on_doc:
        return _clean_patient_name(doc.patient_name_on_doc)
    summary = doc.content_summary or ""
    if not summary.strip():
        return None

    for candidate in (
        extract_patient_name(summary),
        parse_text_summary(summary).patient_name,
    ):
        if candidate and is_plausible_person_name(candidate):
            return _clean_patient_name(candidate)

    if doc.content_source in OCR_SOURCES or doc.file_content_base64:
        llm_name = extract_patient_name_llm(summary)
        if llm_name and is_plausible_person_name(llm_name):
            return _clean_patient_name(llm_name)

    return None


def _apply_submission_patient_hint(submission: ClaimSubmission) -> ClaimSubmission:
    hint = (submission.patient_name or "").strip()
    if not hint:
        return submission

    updated_docs: list[ClaimDocument] = []
    for doc in submission.documents:
        if doc.patient_name_on_doc or _extract_patient_name(doc):
            updated_docs.append(doc)
            continue
        updated_docs.append(doc.model_copy(update={"patient_name_on_doc": hint}))
    return submission.model_copy(update={"documents": updated_docs})


def validate_documents(submission: ClaimSubmission, policy: Optional[dict] = None) -> GatekeeperResult:
    policy = policy or load_policy()
    submission = _apply_submission_patient_hint(submission)
    requirements = policy.get("document_requirements", {}).get(submission.claim_category, {})
    required_types = requirements.get("required", [])

    member = _find_member(policy, submission.member_id)
    claim_for = (submission.claim_for or "").strip().upper()
    if member and claim_for and claim_for != "SELF" and not member.get("primary_member_id"):
        allowed_for_selection = _allowed_patient_names(policy, submission.member_id, claim_for)
        if not allowed_for_selection:
            return GatekeeperResult(
                passed=False,
                message=_claim_for_coverage_message(claim_for),
                detected_types=[],
                missing_types=required_types,
                patient_names_found=[],
            )

    detected: list[str] = []
    unreadable: list[str] = []
    patient_names: list[str] = []

    for doc in submission.documents:
        type_result = infer_document_type(doc, policy)
        doc_type = type_result.doc_type
        detected.append(doc_type)

        patient = _extract_patient_name(doc)
        if is_document_unreadable(doc, doc_type, policy, patient):
            unreadable.append(doc.file_name or doc.file_id)
            continue

        if patient:
            patient_names.append(patient)

    type_counts = Counter(detected)
    missing = [t for t in required_types if t not in type_counts]

    if unreadable:
        files = ", ".join(unreadable)
        return GatekeeperResult(
            passed=False,
            message=(
                f"The following document(s) could not be read: {files}. "
                "Please re-upload clear photos or scans of those documents."
            ),
            detected_types=detected,
            missing_types=missing,
            unreadable_files=unreadable,
            patient_names_found=patient_names,
        )

    if missing:
        uploaded = ", ".join(sorted(set(detected)))
        needed = ", ".join(required_types)
        wrong_types = [t for t in detected if t not in required_types and t != "UNKNOWN"]
        if wrong_types and missing:
            wrong_label = wrong_types[0].replace("_", " ").title()
            need_label = missing[0].replace("_", " ").title()
            return GatekeeperResult(
                passed=False,
                message=(
                    f"You uploaded a {wrong_label} but a {need_label} is required for "
                    f"{submission.claim_category} claims. Please upload the correct document."
                ),
                detected_types=detected,
                missing_types=missing,
                patient_names_found=patient_names,
            )
        extra_uploaded = [t for t, c in type_counts.items() if c > 1 and t in required_types]
        if extra_uploaded and missing:
            dup = extra_uploaded[0].replace("_", " ").title()
            need = missing[0].replace("_", " ").title()
            return GatekeeperResult(
                passed=False,
                message=(
                    f"You uploaded {type_counts.get(extra_uploaded[0], 0)} {dup}(s) but a "
                    f"{need} is required for {submission.claim_category} claims. "
                    f"Please upload the missing {need}."
                ),
                detected_types=detected,
                missing_types=missing,
                patient_names_found=patient_names,
            )
        return GatekeeperResult(
            passed=False,
            message=(
                f"Missing required document(s) for {submission.claim_category}. "
                f"Uploaded: {uploaded or 'none'}. Required: {needed}."
            ),
            detected_types=detected,
            missing_types=missing,
            patient_names_found=patient_names,
        )

    unique_patients = {_normalize_name(n) for n in patient_names if n}
    if len(unique_patients) > 1:
        names_display = " and ".join(
            sorted({_clean_patient_name(n) for n in patient_names if n})
        )
        return GatekeeperResult(
            passed=False,
            message=(
                f"Documents belong to different patients: {names_display}. "
                "All documents must be for the same patient. Please verify and re-upload."
            ),
            detected_types=detected,
            missing_types=missing,
            patient_names_found=patient_names,
        )

    allowed_names = _allowed_patient_names(
        policy,
        submission.member_id,
        claim_for or None,
    )
    if patient_names and allowed_names and member:
        for patient in dict.fromkeys(patient_names):
            if not _patient_matches_member(patient, allowed_names):
                return GatekeeperResult(
                    passed=False,
                    message=_member_id_mismatch_message(submission, patient_names, policy),
                    detected_types=detected,
                    missing_types=missing,
                    patient_names_found=patient_names,
                )

    return GatekeeperResult(
        passed=True,
        message="All required documents present and readable.",
        detected_types=detected,
        missing_types=[],
        patient_names_found=patient_names,
    )
