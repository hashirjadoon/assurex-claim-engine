# %% [markdown]
# # AssureX Claim Engine - Python Classification Model
# Trains and compares 3 classification algorithms (Random Forest, Gradient
# Boosting, Logistic Regression) on the synthetic warranty claim dataset.
# Selects the best-performing model based on validation macro F1-score,
# then reports final unbiased performance on the held-out test set.

import matplotlib
matplotlib.use("Agg")  # headless backend — no display needed, just saves files
# %%
import json
import os
from datetime import datetime

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
                              confusion_matrix, f1_score, precision_score,
                              recall_score)
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler

os.makedirs("model", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# %% [markdown]
# ## 1. Load train / validation / test splits

# %%
train_df = pd.read_csv("data/processed/train.csv")
val_df = pd.read_csv("data/processed/val.csv")
test_df = pd.read_csv("data/processed/test.csv")

print(f"Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

# %% [markdown]
# ## 2. Feature selection and encoding
#
# Categorical fields are label-encoded; boolean fields are cast to int.
# Free-text `fault_description` and identifier/date columns are excluded —
# their signal (warranty status, ambiguity) is already captured in derived
# fields (`product_age_days`, `warranty status via dates`, etc.)

# %%
CATEGORICAL_FEATURES = ["product_category", "fault_type", "damage_type"]
BOOLEAN_FEATURES = ["has_receipt", "has_warranty_card", "has_product_image",
                     "serial_number_match", "repair_authorized",
                     "previous_replacement", "is_duplicate_claim"]
NUMERIC_FEATURES = ["product_age_days", "warranty_duration_days", "repair_count",
                     "purchase_price"]

TARGET = "class_label"

encoders = {}
for col in CATEGORICAL_FEATURES:
    le = LabelEncoder()
    le.fit(pd.concat([train_df[col], val_df[col], test_df[col]]))
    encoders[col] = le

target_encoder = LabelEncoder()
target_encoder.fit(train_df[TARGET])
encoders["class_label"] = target_encoder


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in CATEGORICAL_FEATURES:
        out[col] = encoders[col].transform(out[col])
    for col in BOOLEAN_FEATURES:
        out[col] = out[col].astype(int)
    return out[CATEGORICAL_FEATURES + BOOLEAN_FEATURES + NUMERIC_FEATURES]


X_train = prepare_features(train_df)
y_train = target_encoder.transform(train_df[TARGET])

X_val = prepare_features(val_df)
y_val = target_encoder.transform(val_df[TARGET])

X_test = prepare_features(test_df)
y_test = target_encoder.transform(test_df[TARGET])

print("Feature columns:", list(X_train.columns))
print("Classes:", list(target_encoder.classes_))

# %% [markdown]
# Scale numeric features (helps Logistic Regression converge; harmless for
# tree-based models).

# %%
scaler = StandardScaler()
scaler.fit(X_train[NUMERIC_FEATURES])

for df_ in (X_train, X_val, X_test):
    df_[NUMERIC_FEATURES] = scaler.transform(df_[NUMERIC_FEATURES])

# %% [markdown]
# ## 3. Define candidate models with hyperparameter grids
#
# Small grids are used (time-boxed competition setting) but each model still
# undergoes genuine tuning via cross-validated grid search on the training set.

# %%
model_grids = {
    "RandomForest": {
        "estimator": RandomForestClassifier(random_state=42),
        "param_grid": {
            "n_estimators": [100, 200],
            "max_depth": [8, 12, None],
        },
    },
    "GradientBoosting": {
        "estimator": GradientBoostingClassifier(random_state=42),
        "param_grid": {
            "n_estimators": [100, 150],
            "learning_rate": [0.05, 0.1],
        },
    },
    "LogisticRegression": {
        "estimator": LogisticRegression(max_iter=1000, random_state=42),
        "param_grid": {
            "C": [0.1, 1.0, 10.0],
        },
    },
}

# %% [markdown]
# ## 4. Train + cross-validate + tune each model

# %%
results = {}
fitted_models = {}

for name, cfg in model_grids.items():
    print(f"\n=== {name} ===")

    grid = GridSearchCV(
        cfg["estimator"], cfg["param_grid"],
        cv=5, scoring="f1_macro", n_jobs=-1
    )
    grid.fit(X_train, y_train)

    best_model = grid.best_estimator_
    fitted_models[name] = best_model

    cv_scores = cross_val_score(best_model, X_train, y_train, cv=5, scoring="f1_macro")

    val_preds = best_model.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)
    val_f1 = f1_score(y_val, val_preds, average="macro")
    val_precision = precision_score(y_val, val_preds, average="macro")
    val_recall = recall_score(y_val, val_preds, average="macro")

    results[name] = {
        "best_params": grid.best_params_,
        "cv_f1_macro_mean": cv_scores.mean(),
        "cv_f1_macro_std": cv_scores.std(),
        "val_accuracy": val_acc,
        "val_f1_macro": val_f1,
        "val_precision_macro": val_precision,
        "val_recall_macro": val_recall,
    }

    print(f"Best params: {grid.best_params_}")
    print(f"CV F1 (macro): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    print(f"Val Accuracy: {val_acc:.4f} | Val F1 (macro): {val_f1:.4f}")

# %% [markdown]
# ## 5. Model comparison summary

# %%
comparison_df = pd.DataFrame(results).T
comparison_df = comparison_df.sort_values("val_f1_macro", ascending=False)
print(comparison_df)

comparison_df.to_csv("reports/model_comparison_report.csv")

# %% [markdown]
# ## 6. Select best model (by validation macro F1)

# %%
best_model_name = comparison_df.index[0]
best_model = fitted_models[best_model_name]
print(f"\nSelected best model: {best_model_name}")

# %% [markdown]
# ## 7. Final unbiased evaluation on held-out TEST set

# %%
test_preds = best_model.predict(X_test)
test_probs = best_model.predict_proba(X_test)

test_acc = accuracy_score(y_test, test_preds)
test_f1_macro = f1_score(y_test, test_preds, average="macro")

print(f"\n=== FINAL TEST RESULTS ({best_model_name}) ===")
print(f"Test Accuracy: {test_acc:.4f}")
print(f"Test Macro F1: {test_f1_macro:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, test_preds, target_names=target_encoder.classes_))

# %% [markdown]
# ## 8. Confusion matrix (test set)

# %%
cm = confusion_matrix(y_test, test_preds)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=target_encoder.classes_,
            yticklabels=target_encoder.classes_)
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title(f"Confusion Matrix - {best_model_name} (Test Set)")
plt.tight_layout()
plt.savefig("reports/confusion_matrix_test.png")
plt.close()
print("Saved confusion matrix to reports/confusion_matrix_test.png")

# %% [markdown]
# ## 9. Feature importance (tree-based models only)

# %%
if hasattr(best_model, "feature_importances_"):
    importances = pd.Series(best_model.feature_importances_, index=X_train.columns)
    importances = importances.sort_values(ascending=False)

    plt.figure(figsize=(8, 6))
    importances.plot(kind="barh")
    plt.title(f"Feature Importance - {best_model_name}")
    plt.tight_layout()
    plt.savefig("reports/feature_importance.png")
    plt.close()
    print("Saved feature importance to reports/feature_importance.png")
    print(importances)
else:
    print(f"{best_model_name} does not expose feature_importances_ (e.g. Logistic Regression).")

# %% [markdown]
# ## 10. Sample test predictions (for report/demo)

# %%
sample_output = test_df[["claim_id", "class_label"]].copy()
sample_output["predicted_label"] = target_encoder.inverse_transform(test_preds)
for i, cls in enumerate(target_encoder.classes_):
    sample_output[f"confidence_{cls}"] = test_probs[:, i]

sample_output.to_csv("reports/sample_test_predictions.csv", index=False)
print(sample_output.head(10).to_string(index=False))

# %% [markdown]
# ## 11. Save model, encoders, scaler, and metadata

# %%
joblib.dump(best_model, "model/claim_classifier.pkl")
joblib.dump({"encoders": encoders, "scaler": scaler,
             "feature_columns": list(X_train.columns)}, "model/encoders.pkl")

metadata = {
    "model_name": best_model_name,
    "model_version": "1.0.0",
    "trained_at": datetime.now().isoformat(),
    "best_params": results[best_model_name]["best_params"],
    "test_accuracy": test_acc,
    "test_f1_macro": test_f1_macro,
    "val_accuracy": results[best_model_name]["val_accuracy"],
    "val_f1_macro": results[best_model_name]["val_f1_macro"],
    "cv_f1_macro_mean": results[best_model_name]["cv_f1_macro_mean"],
    "classes": list(target_encoder.classes_),
    "feature_columns": list(X_train.columns),
}

with open("model/model_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

print("\nSaved model/claim_classifier.pkl")
print("Saved model/encoders.pkl")
print("Saved model/model_metadata.json")
print(f"\nFinal Test Accuracy: {test_acc:.4f} (SRS target: >= 0.85)")