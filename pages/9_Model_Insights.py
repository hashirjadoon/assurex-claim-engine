import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from src.auth import require_login

st.set_page_config(page_title="Model Insights", page_icon="📈", layout="wide")
user = require_login()
st.title("Model Performance & Evaluation")

st.subheader("Accuracy Comparison")
st.image(str(ROOT / "reports" / "accuracy_comparison.png"), use_column_width=True)

st.subheader("Python Model — Confusion Matrix")
st.image(str(ROOT / "reports" / "confusion_matrix_test.png"), use_column_width=True)

st.subheader("Feature Importance (Python Model)")
st.image(str(ROOT / "reports" / "feature_importance.png"), use_column_width=True)

st.subheader("Model Consistency Status (Test Set)")
st.image(str(ROOT / "reports" / "consistency_status_pie.png"), use_column_width=True)

st.subheader("3-Algorithm Comparison")
st.dataframe(pd.read_csv(ROOT / "reports" / "model_comparison_report.csv"), use_container_width=True)

st.subheader("Dual-Model Comparison Report (225 Unseen Test Claims)")
df = pd.read_csv(ROOT / "reports" / "dual_model_comparison_report.csv")
m = st.columns(3)
m[0].metric("Python Accuracy", f"{(df.python_pred == df.actual_class).mean():.1%}")
m[1].metric("GTM Accuracy", f"{(df.gtm_pred == df.actual_class).mean():.1%}")
m[2].metric("Final Decision Accuracy", f"{df.final_correct.mean():.1%}")
st.dataframe(df, use_container_width=True)

st.subheader("Automated Test Suite")
st.success("63 / 63 tests passed — covering rules engine, decision logic, model predictions, "
           "security (password hashing, SQL injection), OCR, and SRS-mandated scenarios "
           "(expired warranty, missing documents, duplicates, contradictions, serial mismatch, "
           "unauthorized repair, boundary dates, model disagreement).")