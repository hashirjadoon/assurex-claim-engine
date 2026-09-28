import pandas as pd
import pytest
from src.ml.predict import predict_claim

TEST = pd.read_csv("data/processed/test.csv")


def test_output_shape_and_probabilities_sum_to_one():
    r = predict_claim(TEST.iloc[0].to_dict())
    assert set(r["confidences"]) == {"Valid", "Invalid", "ManualReview"}
    assert abs(sum(r["confidences"].values()) - 1) < 1e-6
    assert r["predicted_class"] in r["confidences"]


def test_unknown_category_rejected():
    c = TEST.iloc[0].to_dict()
    c["fault_type"] = "Not A Real Fault"
    with pytest.raises(ValueError):
        predict_claim(c)


def test_accuracy_meets_srs_threshold():
    ok = sum(predict_claim(r.to_dict())["predicted_class"] == r["class_label"] for _, r in TEST.iterrows())
    assert ok / len(TEST) >= 0.85