"""Adjudication intent rules — kept in code; policy_terms.json is not modified."""

from typing import Any

PER_CLAIM_LIMIT_EXEMPT_CATEGORIES = frozenset({"dental"})

LINE_ITEM_CATEGORY_KEYS: dict[str, dict[str, str]] = {
    "dental": {
        "covered_key": "covered_procedures",
        "excluded_key": "excluded_procedures",
        "excluded_reason": "COSMETIC_EXCLUSION",
    },
    "vision": {
        "covered_key": "covered_items",
        "excluded_key": "excluded_items",
        "excluded_reason": "EXCLUSION",
    },
}

EXCLUSION_RULES: list[dict[str, Any]] = [
    {
        "reason_code": "EXCLUDED_CONDITION",
        "label": "Obesity and weight loss programs",
        "scope": "claim",
        "match_fields": ["diagnosis", "treatment", "line_items"],
        "intent_phrases": [
            "morbid obesity",
            "weight loss program",
            "weight loss",
            "diet program",
            "nutrition program",
            "personalised diet",
            "personalized diet",
            "obesity treatment",
            "obesity",
        ],
    },
    {
        "reason_code": "EXCLUDED_CONDITION",
        "label": "Bariatric surgery",
        "scope": "claim",
        "match_fields": ["diagnosis", "treatment", "line_items"],
        "intent_phrases": ["bariatric surgery", "bariatric consultation", "bariatric"],
    },
    {
        "reason_code": "EXCLUDED_CONDITION",
        "label": "Cosmetic or aesthetic procedures",
        "scope": "claim_primary_intent",
        "defer_to_line_items_for_categories": ["dental", "vision"],
        "match_fields": ["diagnosis", "treatment"],
        "intent_phrases": [
            "cosmetic surgery",
            "cosmetic procedure",
            "aesthetic procedure",
            "plastic surgery",
            "liposuction",
            "rhinoplasty",
            "botox",
            "hair transplant",
        ],
    },
    {
        "reason_code": "EXCLUDED_CONDITION",
        "label": "Infertility and assisted reproduction",
        "scope": "claim",
        "match_fields": ["diagnosis", "treatment", "line_items"],
        "intent_phrases": [
            "infertility",
            "assisted reproduction",
            "in vitro fertilization",
            "in vitro",
            "ivf",
            "iui",
        ],
    },
    {
        "reason_code": "EXCLUDED_CONDITION",
        "label": "Substance abuse treatment",
        "scope": "claim",
        "match_fields": ["diagnosis", "treatment", "line_items"],
        "intent_phrases": [
            "substance abuse",
            "drug rehabilitation",
            "alcohol rehabilitation",
            "de-addiction",
        ],
    },
    {
        "reason_code": "EXCLUDED_CONDITION",
        "label": "Experimental treatments",
        "scope": "claim",
        "match_fields": ["diagnosis", "treatment", "line_items"],
        "intent_phrases": ["experimental treatment", "clinical trial", "unapproved therapy"],
    },
]

WAITING_CONDITION_INTENTS: dict[str, list[str]] = {
    "diabetes": ["diabetes", "diabetic", "t2dm", "type 2 diabetes", "type 2 diabetes mellitus"],
    "hypertension": ["hypertension", "htn", "high blood pressure"],
    "thyroid_disorders": ["thyroid", "hypothyroid", "hyperthyroid", "thyroid disorder"],
    "joint_replacement": ["joint replacement", "knee replacement", "hip replacement"],
    "maternity": ["maternity", "pregnancy", "prenatal", "antenatal"],
    "mental_health": ["mental health", "depression", "anxiety disorder", "psychiatric"],
    "obesity_treatment": ["obesity treatment", "morbid obesity", "bariatric", "weight loss program"],
    "hernia": ["hernia"],
    "cataract": ["cataract"],
}

PRE_AUTH_TEST_INTENTS: dict[str, list[str]] = {
    "MRI": ["mri", "magnetic resonance imaging"],
    "CT Scan": ["ct scan", "computed tomography"],
    "PET Scan": ["pet scan", "positron emission tomography"],
}

DOCUMENT_TYPE_SIGNALS: dict[str, dict[str, Any]] = {
    "LAB_REPORT": {
        "intent_phrases": ["test name", "nabl", "pathologist", "reference range", "lab report", "specimen"],
        "boost_if_tests_ordered": True,
    },
    "PRESCRIPTION": {
        "intent_phrases": ["prescription", "medicines prescribed", "rx", "diagnosis"],
        "boost_if_clinical_only": True,
    },
    "PHARMACY_BILL": {
        "intent_phrases": ["drug lic", "drug license", "pharmacy", "dispensed", "batch no"],
        "requires_amount": True,
    },
    "HOSPITAL_BILL": {
        "intent_phrases": [
            "consultation fee",
            "hospital bill",
            "clinic bill",
            "gstin",
            "procedure",
            "dental treatment",
        ],
        "requires_amount": True,
    },
}

DOCUMENT_READABILITY: dict[str, dict[str, list[str]]] = {
    "PHARMACY_BILL": {"required_signals": ["patient_name", "amount"]},
    "HOSPITAL_BILL": {"required_signals": ["amount"]},
    "PRESCRIPTION": {"required_signals": ["patient_name"]},
    "LAB_REPORT": {"required_signals": ["patient_name"]},
}
