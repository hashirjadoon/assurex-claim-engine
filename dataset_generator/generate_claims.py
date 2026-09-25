"""
AssureX Claim Engine - Synthetic Dataset Generator
====================================================
Generates 1,500 unique warranty claim records (500 Valid, 500 Invalid,
500 Manual Review) as required by the SRS (Section 1.2, Hint box).

Output:
    data/raw/generated_claims.csv          -> all 1,500 records
    data/processed/train.csv               -> 1,050 records (70%)
    data/processed/val.csv                 -> 225 records (15%)
    data/processed/test.csv                -> 225 records (15%)

Run from project root:
    python3 dataset_generator/generate_claims.py
"""

import os
import random
import uuid
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

# ---------------------------------------------------------------------------
# Reference data — matches the 3 warranty policy files in /policies
# ---------------------------------------------------------------------------

PRODUCT_CATEGORIES = {
    "Electronics": {
        "products": ["Smartphone", "Laptop", "Television", "Headphones", "Tablet"],
        "warranty_days_options": [365, 730],
        "covered_faults": ["Screen Malfunction", "Battery Failure", "Charging Port Issue",
                            "Software Fault", "Overheating"],
        "excluded_faults": ["Water Damage", "Physical Impact Damage", "Unauthorized Modification"],
    },
    "Appliances": {
        "products": ["Washing Machine", "Refrigerator", "Microwave Oven", "Air Conditioner", "Dishwasher"],
        "warranty_days_options": [730, 1095],
        "covered_faults": ["Motor Failure", "Compressor Fault", "Electrical Short Circuit",
                            "Thermostat Malfunction", "Drainage Issue"],
        "excluded_faults": ["Improper Installation Damage", "Power Surge Damage", "Rust/Corrosion"],
    },
    "Furniture": {
        "products": ["Sofa", "Dining Table", "Office Chair", "Bed Frame", "Bookshelf"],
        "warranty_days_options": [365, 1095],
        "covered_faults": ["Structural Frame Defect", "Upholstery Tear", "Joint/Hinge Failure",
                            "Material Defect"],
        "excluded_faults": ["Accidental Damage", "Misuse Damage", "Normal Wear and Tear"],
    },
}

DAMAGE_TYPES = ["Manufacturing Defect", "Wear and Tear", "Accidental Damage",
                "Electrical Fault", "Structural Damage", "Cosmetic Damage"]

AMBIGUOUS_FAULT_PHRASES = [
    "Not working properly sometimes",
    "Makes strange noise occasionally",
    "Stopped working, not sure why",
    "Performance seems inconsistent",
    "Minor issue, hard to describe",
]


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_days = random.randint(0, max(delta.days, 0))
    return start + timedelta(days=random_days)


def generate_claim(class_label: str, index: int) -> dict:
    """Generates a single claim record consistent with the target class_label."""

    category = random.choice(list(PRODUCT_CATEGORIES.keys()))
    cat_info = PRODUCT_CATEGORIES[category]

    product_name = random.choice(cat_info["products"])
    warranty_duration_days = random.choice(cat_info["warranty_days_options"])

    today = datetime(2026, 9, 25)  # fixed reference date for reproducibility
    purchase_date = random_date(today - timedelta(days=1500), today - timedelta(days=10))
    warranty_start_date = purchase_date
    warranty_expiry_date = warranty_start_date + timedelta(days=warranty_duration_days)

    purchase_price = round(random.uniform(50, 2500), 2)
    serial_number = f"SN-{uuid.uuid4().hex[:10].upper()}"

    # Defaults (Valid-leaning); overridden per class below
    has_receipt = True
    has_warranty_card = True
    has_product_image = True
    serial_number_match = True
    repair_count = random.randint(0, 1)
    repair_authorized = True
    previous_replacement = False
    is_duplicate_claim = False
    fault_description = ""
    damage_type = random.choice(DAMAGE_TYPES)

    if class_label == "Valid":
        fault_type = random.choice(cat_info["covered_faults"])
        fault_description = f"{fault_type} reported by customer during normal use."
        claim_submission_date = random_date(
            warranty_start_date + timedelta(days=5),
            warranty_expiry_date - timedelta(days=15)
        )
        fault_occurrence_date = claim_submission_date - timedelta(days=random.randint(1, 5))
        repair_authorized = True

    elif class_label == "Invalid":
        invalid_reason = random.choice(["expired", "excluded_fault", "serial_mismatch", "prior_replacement"])

        if invalid_reason == "expired":
            fault_type = random.choice(cat_info["covered_faults"])
            fault_description = f"{fault_type} reported by customer."
            claim_submission_date = random_date(
                warranty_expiry_date + timedelta(days=1),
                warranty_expiry_date + timedelta(days=200)
            )
            fault_occurrence_date = claim_submission_date - timedelta(days=random.randint(1, 5))

        elif invalid_reason == "excluded_fault":
            fault_type = random.choice(cat_info["excluded_faults"])
            fault_description = f"{fault_type} - not covered under warranty terms."
            claim_submission_date = random_date(
                warranty_start_date + timedelta(days=5),
                warranty_expiry_date - timedelta(days=15)
            )
            fault_occurrence_date = claim_submission_date - timedelta(days=random.randint(1, 5))

        elif invalid_reason == "serial_mismatch":
            fault_type = random.choice(cat_info["covered_faults"])
            fault_description = f"{fault_type} reported by customer."
            claim_submission_date = random_date(
                warranty_start_date + timedelta(days=5),
                warranty_expiry_date - timedelta(days=15)
            )
            fault_occurrence_date = claim_submission_date - timedelta(days=random.randint(1, 5))
            serial_number_match = False

        else:  # prior_replacement
            fault_type = random.choice(cat_info["covered_faults"])
            fault_description = f"{fault_type} reported by customer."
            claim_submission_date = random_date(
                warranty_start_date + timedelta(days=5),
                warranty_expiry_date - timedelta(days=15)
            )
            fault_occurrence_date = claim_submission_date - timedelta(days=random.randint(1, 5))
            previous_replacement = True

    else:  # ManualReview
        borderline_reason = random.choice(
            ["missing_doc", "unauthorized_repair", "near_expiry", "ambiguous_fault", "duplicate"]
        )
        fault_type = random.choice(cat_info["covered_faults"])
        claim_submission_date = random_date(
            warranty_start_date + timedelta(days=5),
            warranty_expiry_date - timedelta(days=1)
        )
        fault_occurrence_date = claim_submission_date - timedelta(days=random.randint(1, 5))
        fault_description = f"{fault_type} reported by customer."

        if borderline_reason == "missing_doc":
            missing = random.choice(["receipt", "warranty_card", "product_image"])
            has_receipt = missing != "receipt"
            has_warranty_card = missing != "warranty_card"
            has_product_image = missing != "product_image"

        elif borderline_reason == "unauthorized_repair":
            repair_count = random.randint(1, 3)
            repair_authorized = False

        elif borderline_reason == "near_expiry":
            claim_submission_date = random_date(
                warranty_expiry_date - timedelta(days=7),
                warranty_expiry_date + timedelta(days=3)
            )
            fault_occurrence_date = claim_submission_date - timedelta(days=random.randint(1, 3))

        elif borderline_reason == "ambiguous_fault":
            fault_description = random.choice(AMBIGUOUS_FAULT_PHRASES)

        else:  # duplicate
            is_duplicate_claim = True

    claim_id = f"CLM-{index:05d}"
    product_id = f"PRD-{index:05d}"

    return {
        "claim_id": claim_id,
        "product_id": product_id,
        "product_category": category,
        "product_name": product_name,
        "serial_number": serial_number,
        "purchase_date": purchase_date.date().isoformat(),
        "purchase_price": purchase_price,
        "warranty_start_date": warranty_start_date.date().isoformat(),
        "warranty_duration_days": warranty_duration_days,
        "warranty_expiry_date": warranty_expiry_date.date().isoformat(),
        "fault_occurrence_date": fault_occurrence_date.date().isoformat(),
        "fault_type": fault_type,
        "fault_description": fault_description,
        "damage_type": damage_type,
        "claim_submission_date": claim_submission_date.date().isoformat(),
        "product_age_days": (claim_submission_date - purchase_date).days,
        "has_receipt": has_receipt,
        "has_warranty_card": has_warranty_card,
        "has_product_image": has_product_image,
        "serial_number_match": serial_number_match,
        "repair_count": repair_count,
        "repair_authorized": repair_authorized,
        "previous_replacement": previous_replacement,
        "is_duplicate_claim": is_duplicate_claim,
        "class_label": class_label,
    }


def generate_dataset(n_per_class: int = 500) -> pd.DataFrame:
    records = []
    index = 1
    for label in ["Valid", "Invalid", "ManualReview"]:
        for _ in range(n_per_class):
            records.append(generate_claim(label, index))
            index += 1

    df = pd.DataFrame(records)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle
    return df


def stratified_split(df: pd.DataFrame, train_frac=0.70, val_frac=0.15):
    train_parts, val_parts, test_parts = [], [], []

    for label in df["class_label"].unique():
        subset = df[df["class_label"] == label].sample(frac=1, random_state=42).reset_index(drop=True)
        n = len(subset)
        train_end = int(n * train_frac)
        val_end = train_end + int(n * val_frac)

        train_parts.append(subset.iloc[:train_end])
        val_parts.append(subset.iloc[train_end:val_end])
        test_parts.append(subset.iloc[val_end:])

    train_df = pd.concat(train_parts).sample(frac=1, random_state=42).reset_index(drop=True)
    val_df = pd.concat(val_parts).sample(frac=1, random_state=42).reset_index(drop=True)
    test_df = pd.concat(test_parts).sample(frac=1, random_state=42).reset_index(drop=True)

    return train_df, val_df, test_df


def main():
    print("Generating 1,500 synthetic warranty claims...")
    df = generate_dataset(n_per_class=500)

    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    raw_path = "data/raw/generated_claims.csv"
    df.to_csv(raw_path, index=False)
    print(f"Saved {len(df)} records to {raw_path}")

    train_df, val_df, test_df = stratified_split(df)

    train_df.to_csv("data/processed/train.csv", index=False)
    val_df.to_csv("data/processed/val.csv", index=False)
    test_df.to_csv("data/processed/test.csv", index=False)

    print(f"Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")
    print("\nClass distribution check:")
    print("Train:\n", train_df["class_label"].value_counts())
    print("Val:\n", val_df["class_label"].value_counts())
    print("Test:\n", test_df["class_label"].value_counts())


if __name__ == "__main__":
    main()