import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.ml.predict import predict_claim
from src.ml.gtm_client import classify_card
from src.rules_engine.warranty_rules import validate_claim
from src.rules_engine.contradiction_checks import detect_contradictions
from src.decision.final_decision import make_final_decision

EXPECTED = {"Valid": "Likely Valid", "Invalid": "Likely Invalid",
            "ManualReview": "Manual Review Required"}

df = pd.read_csv(ROOT / "data" / "processed" / "test.csv")
rows = []
for _, r in df.iterrows():
    claim = r.to_dict()
    card = ROOT / "data" / "claim_summary_cards" / "test" / claim["class_label"] / f"{claim['claim_id']}_v1.png"
    py = predict_claim(claim)
    gtm = classify_card(str(card))
    rules = validate_claim(claim)
    contra = detect_contradictions(claim)
    res = make_final_decision(py, gtm, rules, contra)
    rows.append({
        "claim_id": claim["claim_id"], "actual_class": claim["class_label"],
        "python_pred": py["predicted_class"],
        "py_conf_Valid": py["confidences"]["Valid"], "py_conf_Invalid": py["confidences"]["Invalid"],
        "py_conf_ManualReview": py["confidences"]["ManualReview"],
        "card_filename": card.name, "gtm_pred": gtm["predicted_class"],
        "gtm_conf_Valid": gtm["confidences"]["Valid"], "gtm_conf_Invalid": gtm["confidences"]["Invalid"],
        "gtm_conf_ManualReview": gtm["confidences"]["ManualReview"],
        "class_match": res["consistency"]["class_match"],
        "confidence_difference": res["consistency"]["confidence_difference"],
        "consistency_status": res["consistency"]["consistency_status"],
        "rule_result": rules["status"],
        "missing_documents": ";".join(rules["missing_documents"]),
        "contradictions": ";".join(contra),
        "duplicate_indicator": rules["duplicate"],
        "final_decision": res["final_decision"],
        "final_correct": res["final_decision"] == EXPECTED[claim["class_label"]],
    })

out = pd.DataFrame(rows)
out.to_csv(ROOT / "reports" / "dual_model_comparison_report.csv", index=False)
print("Claims:", len(out))
print("Python accuracy:", (out.python_pred == out.actual_class).mean().round(4))
print("GTM accuracy:", (out.gtm_pred == out.actual_class).mean().round(4))
print("Final decision accuracy:", out.final_correct.mean().round(4))
print(out.consistency_status.value_counts())
print(pd.crosstab(out.actual_class, out.final_decision))