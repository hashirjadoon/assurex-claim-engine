import json
from pathlib import Path

THRESHOLDS_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "thresholds.json"


def load_thresholds() -> dict:
    with open(THRESHOLDS_PATH) as f:
        return json.load(f)


def compare_models(py: dict, gtm: dict, t: dict = None) -> dict:
    t = t or load_thresholds()
    p_cls, g_cls = py["predicted_class"], gtm["predicted_class"]
    p_conf, g_conf = py["confidences"][p_cls], gtm["confidences"][g_cls]
    diff = abs(p_conf - g_conf)
    if p_cls != g_cls:
        status = "Model Disagreement"
    elif min(p_conf, g_conf) < t["min_confidence"]:
        status = "Uncertain Result"
    elif diff <= t["strong_match_max_diff"]:
        status = "Strong Match"
    elif diff <= t["acceptable_match_max_diff"]:
        status = "Acceptable Match"
    else:
        status = "Weak Match"
    return {"class_match": p_cls == g_cls, "confidence_difference": diff,
            "consistency_status": status}


def make_final_decision(py: dict, gtm: dict, rules: dict, contradictions: list) -> dict:
    cmp_ = compare_models(py, gtm)
    p_cls, g_cls = py["predicted_class"], gtm["predicted_class"]
    status = cmp_["consistency_status"]
    reasons = []

    if contradictions:
        decision = "Manual Review Required"
        reasons.append("Contradictions detected")
    elif rules["hard_fail_reasons"]:
        if p_cls == "Invalid" and g_cls != "Valid":
            decision = "Likely Invalid"
        else:
            decision = "Manual Review Required"
            reasons.append("Rule hard-fail not confirmed by both models")
    elif rules["manual_review_reasons"]:
        decision = "Manual Review Required"
        reasons.append("Rule-based manual review triggers")
    elif status in ("Model Disagreement", "Uncertain Result", "Weak Match"):
        decision = "Manual Review Required"
        reasons.append(f"Model consistency: {status}")
    elif p_cls == "Valid":
        decision = "Likely Valid"
    elif p_cls == "Invalid":
        decision = "Likely Invalid"
    else:
        decision = "Manual Review Required"
        reasons.append("Both models predict Manual Review")

    return {
        "final_decision": decision,
        "consistency": cmp_,
        "explanation": {
            "supporting": [f"Python model: {p_cls}", f"GTM model: {g_cls}"] + rules["rules_passed"],
            "opposing": rules["hard_fail_reasons"] + rules["manual_review_reasons"],
            "contradictions": contradictions,
            "additional_evidence_required": rules["missing_documents"],
            "routing_reasons": reasons,
        },
    }