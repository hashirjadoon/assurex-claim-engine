"""
Claim Summary Card generator (v2, color-coded status blocks).
Cards show claim information only. No prediction, confidence or decision.
Train: 2 variations per claim. Val/test: 1 image per claim.
"""
import os
import random
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.rules_engine.warranty_rules import load_policy

random.seed(42)

W, H = 600, 700
GREEN, AMBER, RED = "#2E9E4F", "#F2A900", "#D93025"
BACKGROUNDS = ["#FFFFFF", "#F1F1EC", "#E8F1F8"]
FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"]


def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def d(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d")


def build_rows(r):
    p = load_policy(r["product_category"])
    rows = []

    left = (d(r["warranty_expiry_date"]) - d(r["claim_submission_date"])).days
    if left > p["near_expiry_window_days"]:
        rows.append(("WARRANTY: ACTIVE", GREEN))
    elif left >= 0:
        rows.append(("WARRANTY: EXPIRING SOON", AMBER))
    elif abs(left) <= p["grace_period_days"]:
        rows.append(("WARRANTY: GRACE PERIOD", AMBER))
    else:
        rows.append(("WARRANTY: EXPIRED", RED))

    if r["fault_type"] in p["exclusions"]:
        rows.append(("FAULT: EXCLUDED", RED))
    elif r["fault_type"] in p["covered_faults"]:
        rows.append(("FAULT: COVERED", GREEN))
    else:
        rows.append(("FAULT: NOT LISTED", AMBER))

    vague = any(k in str(r["fault_description"]).lower() for k in p["ambiguous_keywords"])
    rows.append(("DESCRIPTION: VAGUE", AMBER) if vague else ("DESCRIPTION: CLEAR", GREEN))

    rows.append(("SERIAL: MATCH", GREEN) if r["serial_number_match"] else ("SERIAL: MISMATCH", RED))
    rows.append(("RECEIPT: PRESENT", GREEN) if r["has_receipt"] else ("RECEIPT: MISSING", AMBER))
    rows.append(("WARRANTY CARD: PRESENT", GREEN) if r["has_warranty_card"] else ("WARRANTY CARD: MISSING", AMBER))
    rows.append(("PRODUCT IMAGE: PRESENT", GREEN) if r["has_product_image"] else ("PRODUCT IMAGE: MISSING", AMBER))

    if r["repair_count"] == 0:
        rows.append(("REPAIR: NONE", GREEN))
    elif r["repair_authorized"]:
        rows.append(("REPAIR: AUTHORIZED", GREEN))
    else:
        rows.append(("REPAIR: UNAUTHORIZED", AMBER))

    rows.append(("REPLACEMENT: USED", RED) if r["previous_replacement"] else ("REPLACEMENT: NONE", GREEN))
    rows.append(("DUPLICATE: YES", AMBER) if r["is_duplicate_claim"] else ("DUPLICATE: NO", GREEN))
    return rows


def render(r, bg, margin, corner):
    img = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(img)
    dr.text((margin, 14), "CLAIM SUMMARY CARD", fill="#1A1A1A", font=font(30))
    dr.text((margin, 52), f"{r['claim_id']} | {r['product_name']} | {r['product_age_days']} days old",
            fill="#444444", font=font(17))
    y = 90
    for text, color in build_rows(r):
        dr.rounded_rectangle([(margin, y), (W - margin, y + 54)], radius=corner, fill=color)
        dr.text((margin + 16, y + 11), text, fill="#FFFFFF" if color != AMBER else "#1A1A1A", font=font(28))
        y += 62
    return img


def run_split(csv_path, split, variations):
    df = pd.read_csv(csv_path)
    n = 0
    for _, r in df.iterrows():
        out = Path(f"data/claim_summary_cards/{split}/{r['class_label']}")
        out.mkdir(parents=True, exist_ok=True)
        for v in range(variations):
            img = render(r, random.choice(BACKGROUNDS), random.choice([16, 24]), random.choice([6, 14]))
            img.save(out / f"{r['claim_id']}_v{v + 1}.png")
            n += 1
    print(f"{split}: {n} images from {len(df)} claims")


if __name__ == "__main__":
    run_split("data/processed/train.csv", "train", 2)
    run_split("data/processed/val.csv", "val", 1)
    run_split("data/processed/test.csv", "test", 1)