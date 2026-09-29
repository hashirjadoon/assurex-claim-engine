# AssureX Claim Engine

**AI-powered warranty claim validation.** AssureX classifies every warranty claim as **Likely Valid**, **Likely Invalid** or **Manual Review Required**. It combines three independent components:

1. A **Python machine-learning classifier** (scikit-learn) trained on structured claim data.
2. A **Google Teachable Machine** image classifier that reads a generated **Claim Summary Card**.
3. A **configurable, JSON-driven warranty rule engine** with contradiction, duplicate and missing-document checks.

The two models work independently, and their results are compared and combined with the rule-engine output to produce the final decision. No external generative-AI API is used at runtime.

Built for the Aptech TechWiz 7 competition, category **NextWave AI and ML** (theme: AI-Powered Document Ops).

---

## Table of Contents

1. [Features](#features)
2. [How It Works](#how-it-works)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Installation](#installation)
6. [Running the Application](#running-the-application)
7. [Demo Accounts](#demo-accounts)
8. [User Guide](#user-guide)
9. [Dataset](#dataset)
10. [Models](#models)
11. [Rule Engine and Warranty Policies](#rule-engine-and-warranty-policies)
12. [Decision Logic](#decision-logic)
13. [Configuration](#configuration)
14. [Testing](#testing)
15. [Retraining and Regenerating Data](#retraining-and-regenerating-data)
16. [Security and Privacy](#security-and-privacy)
17. [Assumptions and Known Limitations](#assumptions-and-known-limitations)
18. [AI Usage Declaration](#ai-usage-declaration)
19. [License](#license)

---

## 🌐 Live Deployment

The application is deployed and publicly accessible at:

**https://assurex-claim-engine.streamlit.app/**

Demo login credentials:
- Admin: `admin` / `Admin@123`
- Reviewer: `reviewer` / `Review@123`
- Customer: `demo` / `Demo@123`

## Features

| Area | Capability |
|---|---|
| Accounts | Registration, login, role-based access (customer, service employee, reviewer, admin), salted PBKDF2 password hashing |
| Products and warranties | Product registration with unique Product IDs, standard and extended warranties, active / nearing-expiry / expired tracking, configurable expiry alerts |
| Claims | Claim creation with unique Claim IDs, fault and repair details, document upload (PDF, JPG, JPEG, PNG) |
| OCR | Receipt scanning with EasyOCR (purchase date, invoice number, serial number, amount, retailer) with a user verification step |
| Dual-model AI | Python classifier and Teachable Machine classifier, each producing confidences for all three classes |
| Comparison | Class match check, absolute top-class confidence difference, consistency status (Strong / Acceptable / Weak Match, Model Disagreement, Uncertain Result) |
| Rule engine | Warranty expiry, grace period, near-expiry window, fault coverage, exclusions, reporting period, mandatory documents, serial-number match, replacement, repair authorization, ambiguous descriptions |
| Integrity checks | Contradiction detection, missing-document detection, duplicate claim detection, SHA-256 document hashing |
| Explainability | Supporting factors, opposing factors, rules passed and failed, contradictions, additional evidence required |
| Review workflow | Manual-review queue, approve / reject / request information, reviewer comments, override with the original AI result preserved |
| Tracking | Claim status stages, notifications, full audit trail, model-version tracking per prediction |
| Admin | Dashboard (totals, decisions, disagreements, average confidence, trends), anomaly alerts, editable thresholds, CSV export |
| Reporting | Search and filtering, downloadable per-claim report |

---

## How It Works

```
Claim details + documents
        │
        ▼
 Validation and OCR extraction
        │
        ▼
   Pre-processing (Python)
        │
   ┌────┴─────────────────────────┐
   ▼                              ▼
Structured claim data       Claim Summary Card (image)
   │                         (claim facts only, no predictions)
   ▼                              ▼
Python classifier           Google Teachable Machine
   │                              │
   └───────────────┬──────────────┘
                   ▼
   Model prediction and confidence comparison
                   │
      Warranty rules + contradiction checks
                   │
                   ▼
   Likely Valid | Likely Invalid | Manual Review Required
```

The Claim Summary Card contains only claim information. It never contains the Python prediction, a confidence score or the final decision, so the two models stay independent.

---

## Tech Stack

- **Language:** Python 3.10 – 3.12
- **Web UI:** Streamlit
- **Database:** SQLite
- **ML:** scikit-learn (Random Forest, Gradient Boosting, Logistic Regression compared), joblib
- **Image model:** Google Teachable Machine (exported TFLite), run with `ai-edge-litert`
- **OCR:** EasyOCR (PyTorch CPU)
- **Data and imaging:** pandas, NumPy, Pillow, Faker, matplotlib, seaborn
- **Testing:** pytest

---

## Project Structure

```
├── app.py                     Streamlit entry point (home and notifications)
├── pages/                     Streamlit pages
│   ├── 1_Login.py
│   ├── 2_Product_Registration.py
│   ├── 3_Warranty.py
│   ├── 4_New_Claim.py
│   ├── 5_Claim_Status.py
│   ├── 6_Manual_Review.py
│   ├── 7_Admin_Dashboard.py
│   └── 8_Reports.py
├── src/
│   ├── auth.py                Login and role guard
│   ├── db/                    SQLite helpers and schema.sql
│   ├── ml/                    Features, training, prediction, Teachable Machine client
│   ├── cards/                 Claim Summary Card generator
│   ├── ocr/                   Receipt OCR and field extraction
│   ├── rules_engine/          Warranty rules and contradiction checks
│   └── decision/              Model comparison and final decision, comparison report builder
├── policies/                  Warranty policy files (Electronics, Appliances, Furniture)
├── config/thresholds.json     Confidence and alert thresholds
├── dataset_generator/         Synthetic dataset generator
├── data/
│   ├── raw/                   Full generated dataset
│   ├── processed/             train.csv, val.csv, test.csv
│   └── claim_summary_cards/   Card images (train / val / test, by class)
├── model/                     Saved Python model, encoders, metadata
├── gtm_model/                 Exported Teachable Machine model and labels
├── notebooks/                 Model training and comparison notebook
├── reports/                   Model comparison reports, confusion matrix, feature importance
├── tests/                     Automated tests
├── sample_claims/  screenshots/  documentation/  database/
├── AI_USAGE.md                AI tool usage declaration
├── requirements.txt
├── setup.sh / setup.ps1       One-step setup scripts
└── LICENSE
```

---

## Installation

### Prerequisites

- **Python 3.10, 3.11 or 3.12.** Setup scripts refuse 3.13 and newer because the pinned packages (for example NumPy 1.26) have no wheels for those versions.
- About **2 – 4 GB** of free disk space (PyTorch and EasyOCR).
- An internet connection on first run. EasyOCR downloads its language models the first time OCR is used.
- Supported OS: Windows, macOS, Linux.

Do not copy or commit a `venv` folder. Every machine creates its own.

### macOS / Linux

```bash
chmod +x setup.sh
./setup.sh
source venv/bin/activate
```

### Windows (PowerShell)

```powershell
.\setup.ps1
.\venv\Scripts\Activate.ps1
```

If script execution is blocked:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again.

### Manual setup (any OS)

```bash
python3 -m venv venv            # Windows: python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Always run the application in the same terminal where the virtual environment is activated.

---

## Running the Application

```bash
streamlit run app.py
```

Open **http://localhost:8501**.

On first launch the application creates the SQLite database at `database/assurex.db` and seeds the demo accounts. Trained models are already included in `model/` and `gtm_model/`, so no training step is needed to run the app.

**Troubleshooting**

| Problem | Fix |
|---|---|
| `streamlit: command not found` | The virtual environment is not active. Activate it and check `which python` (Windows: `where python`) points inside `venv`. |
| Dependency install fails | Confirm `python --version` is 3.10 – 3.12. |
| First OCR call is slow | EasyOCR is downloading its models. This happens once. |
| Reset the database | Stop the app, delete `database/assurex.db`, start again. |

---

## Demo Accounts

Created automatically on first launch.

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `Admin@123` |
| Reviewer | `reviewer` | `Review@123` |
| Customer | `demo` | `Demo@123` |

New customer and service-employee accounts can be registered on the Login page. Change these passwords before any real deployment.

---

## User Guide

1. **Log in or register** on the *Login* page.
2. **Register a product** on *Product Registration*: name, category, brand, model, serial number, purchase date, price, retailer and warranty duration. A Product ID and the standard warranty record are created automatically.
3. **Review warranties** on *Warranty*: status is shown as Active, Nearing Expiry or Expired. Extended warranties can be added here.
4. **Create a claim** on *New Claim*:
   - Select the product, fault type, damage type, description, fault and claim dates, repair history and serial number shown on the documents.
   - Upload the purchase receipt, warranty card and product / damage image.
   - For an image receipt, click **Extract data from receipt (OCR)**, then check and correct the extracted values.
   - Missing documents are flagged before submission.
5. **Submit the claim.** The application shows:
   - Python prediction with confidences for all three classes
   - The generated Claim Summary Card and the Teachable Machine prediction with confidences
   - Class match, confidence difference and consistency status
   - The final decision with supporting factors, opposing factors, contradictions and required evidence
6. **Track progress** on *Claim Status*: Draft, Submitted, Under Evaluation, Additional Information Required, Manual Review, Approved, Rejected, Closed.
7. **Manual review** (reviewer or admin): open *Manual Review*, inspect the evidence and both model outputs, then approve, reject or request information. A comment is required. The original AI recommendation is kept in the audit history.
8. **Reports and export** on *Reports*: search and filter claims, download a per-claim report, and (admin) export claims, products, warranties, predictions and the audit log as CSV.
9. **Administration** on *Admin Dashboard*: claim statistics, model disagreements, average confidences, trend chart, anomaly alerts, threshold editor and audit trail.

---

## Dataset

One common dataset of **1,500 unique synthetic claims** (500 Valid, 500 Invalid, 500 Manual Review) is used in two formats. It includes normal, incomplete, contradictory, complex and borderline scenarios.

| Split | Claims | Share |
|---|---|---|
| Train | 1,050 | 70% |
| Validation | 225 | 15% |
| Test | 225 | 15% |

The split is stratified by class and performed **before** card generation.

- **Structured format:** `data/processed/{train,val,test}.csv` for the Python model.
- **Image format:** the same claims rendered as Claim Summary Cards in `data/claim_summary_cards/{train,val,test}/{Valid,Invalid,ManualReview}/`. Every training claim has two visual variations (layout, font size, background, spacing) with the same Claim ID and label. Validation and test claims have one image each.
- Each CSV row and its card share the same Claim ID, claim details and class label. A validation or test claim never appears in the training data in either form.
- All records are synthetic. No real customer data is used.

---

## Models

### Python classifier

Three algorithms are trained with hyperparameter search and compared on validation macro F1: **Random Forest, Gradient Boosting, Logistic Regression**. The best model is saved with its encoders and scaler.

| Item | Value |
|---|---|
| Selected model | Gradient Boosting (v1.0.0) |
| Best parameters | `learning_rate=0.1`, `n_estimators=100` |
| Validation accuracy / macro F1 | 91.1% / 0.911 |
| Test accuracy / macro F1 | 92.9% / 0.928 |
| Cross-validation macro F1 (mean) | 0.923 |

Features: product category, fault type, damage type, receipt / warranty card / product image availability, serial-number match, repair authorization, previous replacement, duplicate flag, product age, warranty duration, repair count, purchase price, remaining warranty days and missing-document count.

Categorical fields are label-encoded and numeric fields are scaled. Evidence is in `notebooks/model_training_comparison.ipynb` and `reports/` (`model_comparison_report.csv`, `confusion_matrix_test.png`, `feature_importance.png`, `sample_test_predictions.csv`).

### Google Teachable Machine

An image-classification model trained only on the **training** Claim Summary Cards with three classes (`Valid`, `Invalid`, `ManualReview`). It is exported as TFLite to `gtm_model/` and executed locally by `src/ml/gtm_client.py`.

### Dual-model comparison

`reports/dual_model_comparison_report.csv` holds results for all 225 unseen test claims: both models' predictions and confidences, class match, confidence difference, consistency status, rule result, missing documents, contradictions, duplicate indicator and final decision.

```
Confidence Difference = | Python top-class confidence − Teachable Machine top-class confidence |
```

---

## Rule Engine and Warranty Policies

Rules are **not hard-coded**. Each product category has its own JSON policy in `policies/`: `electronics_policy.json`, `appliances_policy.json`, `furniture_policy.json`.

A policy defines: coverage durations, warranty start condition, covered faults, exclusions, claim-reporting period, grace period, near-expiry window, mandatory documents, authorized-service requirement, unauthorized-repair action, serial-mismatch action, replacement conditions, maximum prior repairs, ambiguous-description keywords, and hard-fail, warning and manual-review rule lists.

Rule outcomes:

- **Hard fail:** warranty expired beyond the grace period, excluded fault, serial mismatch (where policy says hard fail), replacement already used.
- **Manual review:** claim inside the near-expiry window or grace period, fault not listed as covered, ambiguous description, missing mandatory document, unauthorized repair, possible duplicate, late fault reporting.

**Contradiction checks:** claim before purchase, fault before purchase, fault after claim submission, product age inconsistent with dates, receipt serial differing from the entered serial.

**Duplicate detection:** SHA-256 document hashes and product plus fault matches against previous claims.

To add a warranty rule or change a limit, edit the relevant policy file. No code change is needed for policy values.

---

## Decision Logic

Evaluated in this order:

1. **Contradictions found** → Manual Review Required
2. **Rule hard fail** → Likely Invalid only if the Python model says Invalid and the Teachable Machine model does not say Valid; otherwise Manual Review Required
3. **Rule manual-review reasons** → Manual Review Required
4. **Model Disagreement, Uncertain Result or Weak Match** → Manual Review Required
5. **Both models agree** → Likely Valid, Likely Invalid, or Manual Review Required (when the predicted class is Manual Review)

Consistency status (thresholds in `config/thresholds.json`):

| Status | Condition |
|---|---|
| Model Disagreement | The models predict different classes |
| Uncertain Result | Either top confidence is below the minimum |
| Strong Match | Same class, difference ≤ 0.15 |
| Acceptable Match | Same class, difference ≤ 0.35 |
| Weak Match | Same class, difference above 0.35 |

---

## Configuration

`config/thresholds.json` (editable from the Admin Dashboard):

```json
{
  "min_confidence": 0.55,
  "strong_match_max_diff": 0.15,
  "acceptable_match_max_diff": 0.35,
  "expiry_alert_days": 30
}
```

Warranty rules live in `policies/*.json`. The application database is `database/assurex.db` (created automatically, not committed).

---

## Testing

```bash
python -m pytest -q
```

The suite covers:

- **Rule engine:** valid pass, expired warranty, excluded fault, missing documents, serial mismatch, prior replacement, unauthorized repair, duplicate, ambiguous description, late reporting
- **Boundary dates:** 8 and 7 days before expiry, expiry day, grace day 3 (manual review) and grace day 4 (hard fail)
- **Contradictions:** claim / fault before purchase, fault after claim, age mismatch, receipt serial conflict
- **Decision logic:** confidence-difference formula, every consistency status, final decisions, hard-fail handling, forced manual review
- **Python model:** output shape, probabilities sum to 1, unknown category rejected, accuracy at least 85% on the test set

To rebuild the dual-model comparison report:

```bash
python src/decision/build_comparison_report.py
```

---

## Retraining and Regenerating Data

Run from the project root with the virtual environment active.

```bash
# 1. Regenerate the dataset and stratified splits
python dataset_generator/generate_claims.py

# 2. Regenerate Claim Summary Cards (train: 2 variations, val / test: 1)
python src/cards/generate_card.py

# 3. Retrain and compare the Python models
python src/ml/train_model.py

# 4. Rebuild the dual-model comparison report
python src/decision/build_comparison_report.py
```

The Teachable Machine model must be retrained on the new **training** cards at [teachablemachine.withgoogle.com](https://teachablemachine.withgoogle.com/) (Image Project, three classes), then exported as TensorFlow Lite and the files placed in `gtm_model/` (`model_unquant.tflite`, `labels.txt`). Never upload validation or test cards for training.

---

## Security and Privacy

- Passwords are salted and hashed with PBKDF2-HMAC-SHA256 (100,000 iterations).
- Parameterized SQL queries throughout.
- Role-based page access for customer, service employee, reviewer and admin.
- Audit trail for logins, failed logins, registrations, uploads, predictions, submissions, reviewer actions, exports and configuration changes.
- Uploaded documents are hashed for duplicate detection and stored under `data/uploads/`, which is git-ignored.
- The repository contains only synthetic data.

---

## Assumptions and Known Limitations

- The training data is synthetic, so real-world claims may behave differently.
- Live manufacturer databases, payment systems and enterprise warranty platforms are out of scope.
- OCR supports image receipts only. PDF receipts are stored and hashed but must be entered manually.
- OCR accuracy depends on image quality and receipt layout.
- Dates are expected in ISO format (`YYYY-MM-DD`) in the claim record.
- The two models can produce different confidence values because they are trained independently. That difference is a designed signal, not an error.
- SQLite suits a single-server deployment and demonstration workloads.
- Warranty-expiry alerts are shown in the interface and on the Warranty page.

---

## AI Usage Declaration

AI tools used during development are declared in [`AI_USAGE.md`](AI_USAGE.md). Final claim decisions come only from the team's Python classifier, the Teachable Machine model, the JSON-driven rule engine and the application's decision logic.

---

## License

Released under the terms in [`LICENSE`](LICENSE).