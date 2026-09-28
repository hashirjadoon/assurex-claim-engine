from src.decision.final_decision import compare_models, make_final_decision
from tests.helpers import preds

T = {"min_confidence": 0.55, "strong_match_max_diff": 0.15, "acceptable_match_max_diff": 0.35}
PASS = {"status": "PASS", "rules_passed": ["ok"], "hard_fail_reasons": [],
        "manual_review_reasons": [], "missing_documents": [], "duplicate": False}
FAIL = {**PASS, "status": "HARD_FAIL", "hard_fail_reasons": ["Excluded fault: X"]}


def test_strong_match():
    assert compare_models(preds("Valid", 0.90), preds("Valid", 0.85), T)["consistency_status"] == "Strong Match"


def test_acceptable_match():
    assert compare_models(preds("Valid", 0.90), preds("Valid", 0.65), T)["consistency_status"] == "Acceptable Match"


def test_weak_match():
    assert compare_models(preds("Valid", 0.95), preds("Valid", 0.58), T)["consistency_status"] == "Weak Match"


def test_uncertain_low_confidence():
    assert compare_models(preds("Valid", 0.50), preds("Valid", 0.90), T)["consistency_status"] == "Uncertain Result"


def test_model_disagreement():
    r = compare_models(preds("Valid", 0.9), preds("Invalid", 0.9), T)
    assert r["consistency_status"] == "Model Disagreement" and r["class_match"] is False


def test_confidence_difference_formula():
    r = compare_models(preds("Valid", 0.80), preds("Valid", 0.60), T)
    assert abs(r["confidence_difference"] - 0.20) < 1e-9


def test_final_likely_valid():
    assert make_final_decision(preds("Valid", 0.9), preds("Valid", 0.88), PASS, [])["final_decision"] == "Likely Valid"


def test_final_likely_invalid_when_rules_and_models_agree():
    assert make_final_decision(preds("Invalid", 0.9), preds("Invalid", 0.9), FAIL, [])["final_decision"] == "Likely Invalid"


def test_hard_fail_not_confirmed_goes_to_manual():
    assert make_final_decision(preds("Valid", 0.9), preds("Valid", 0.9), FAIL, [])["final_decision"] == "Manual Review Required"


def test_contradiction_forces_manual():
    assert make_final_decision(preds("Valid", 0.9), preds("Valid", 0.9), PASS, ["x"])["final_decision"] == "Manual Review Required"


def test_model_disagreement_forces_manual():
    assert make_final_decision(preds("Valid", 0.9), preds("Invalid", 0.9), PASS, [])["final_decision"] == "Manual Review Required"


def test_rule_manual_reason_forces_manual():
    r = {**PASS, "manual_review_reasons": ["Possible duplicate claim"]}
    assert make_final_decision(preds("Valid", 0.9), preds("Valid", 0.9), r, [])["final_decision"] == "Manual Review Required"


def test_low_confidence_forces_manual():
    assert make_final_decision(preds("Valid", 0.5), preds("Valid", 0.5), PASS, [])["final_decision"] == "Manual Review Required"