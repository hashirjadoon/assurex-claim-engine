"""
AssureX Claim Engine - Claim Summary Card Generator
=====================================================
Renders each claim record as a visual "Claim Summary Card" image using Pillow.

IMPORTANT (per SRS): This card must NOT contain the Python model's prediction,
confidence score, or final claim decision. It only shows claim information.

Training claims get >=2 visual variations (different background/font/spacing/date format).
Validation and testing claims get exactly 1 image each (no variations, no training use).

Output structure:
    data/claim_summary_cards/train/{Valid,Invalid,ManualReview}/
    data/claim_summary_cards/val/{Valid,Invalid,ManualReview}/
    data/claim_summary_cards/test/{Valid,Invalid,ManualReview}/

Run from project root:
    python3 src/cards/generate_card.py
"""

import os
import random
from datetime import datetime

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

random.seed(42)

CARD_WIDTH = 600
CARD_HEIGHT = 500

BACKGROUND_COLORS = ["#FFFFFF", "#F5F5F0", "#EAF2F8"]
FONT_SIZES = [16, 18]
DATE_FORMATS = ["%Y-%m-%d", "%d %b %Y"]

# Class label used in CSV vs folder name (SRS uses "Manual Review" in text,
# but our CSV/folder use "ManualReview" as a single token — kept consistent
# across dataset_generator, cards, and model training)
LABEL_TO_FOLDER = {
    "Valid": "Valid",
    "Invalid": "Invalid",
    "ManualReview": "ManualReview",
}


def get_font(size: int):
    """Falls back to Pillow's default font if no truetype font is found on the system."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def format_date(date_str: str, fmt: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime(fmt)


def build_card_lines(row: pd.Series, date_fmt: str) -> list:
    warranty_expiry = datetime.strptime(row["warranty_expiry_date"], "%Y-%m-%d")
    claim_date = datetime.strptime(row["claim_submission_date"], "%Y-%m-%d")
    days_diff = (warranty_expiry - claim_date).days
    warranty_status = "Active" if days_diff >= 0 else "Expired"
    warranty_detail = (
        f"{days_diff} days remaining" if days_diff >= 0
        else f"{abs(days_diff)} days overdue"
    )

    doc_status = []
    doc_status.append(f"Receipt: {'Present' if row['has_receipt'] else 'Missing'}")
    doc_status.append(f"Warranty Card: {'Present' if row['has_warranty_card'] else 'Missing'}")
    doc_status.append(f"Product Image: {'Present' if row['has_product_image'] else 'Missing'}")

    lines = [
        ("Claim Summary Card", True),
        (f"Claim ID: {row['claim_id']}", False),
        (f"Product: {row['product_name']} ({row['product_category']})", False),
        (f"Product Age: {row['product_age_days']} days", False),
        (f"Purchase Date: {format_date(row['purchase_date'], date_fmt)}", False),
        (f"Warranty Status: {warranty_status} ({warranty_detail})", False),
        (f"Fault Type: {row['fault_type']}", False),
        (f"Damage Type: {row['damage_type']}", False),
        (f"Repair Count: {row['repair_count']}", False),
        (f"Repair Authorized: {'Yes' if row['repair_authorized'] else 'No'}", False),
        (f"Serial Number Status: {'Match' if row['serial_number_match'] else 'Mismatch'}", False),
        (f"Previous Replacement: {'Yes' if row['previous_replacement'] else 'No'}", False),
    ]
    for d in doc_status:
        lines.append((d, False))

    return lines


def render_card(row: pd.Series, bg_color: str, font_size: int, date_fmt: str,
                 padding: int) -> Image.Image:
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), color=bg_color)
    draw = ImageDraw.Draw(img)

    title_font = get_font(font_size + 6)
    body_font = get_font(font_size)

    lines = build_card_lines(row, date_fmt)

    y = padding
    line_height = font_size + 10

    for text, is_title in lines:
        font = title_font if is_title else body_font
        color = "#1A1A1A" if is_title else "#333333"
        draw.text((padding, y), text, fill=color, font=font)
        y += line_height + (10 if is_title else 0)

    # Simple border for visual consistency
    draw.rectangle([(2, 2), (CARD_WIDTH - 3, CARD_HEIGHT - 3)], outline="#CCCCCC", width=2)

    return img


def generate_cards_for_split(csv_path: str, split_name: str, variations: int):
    df = pd.read_csv(csv_path)
    base_dir = f"data/claim_summary_cards/{split_name}"

    total_images = 0
    for _, row in df.iterrows():
        folder = LABEL_TO_FOLDER[row["class_label"]]
        out_dir = os.path.join(base_dir, folder)
        os.makedirs(out_dir, exist_ok=True)

        for v in range(variations):
            bg_color = random.choice(BACKGROUND_COLORS)
            font_size = random.choice(FONT_SIZES)
            date_fmt = random.choice(DATE_FORMATS)
            padding = random.choice([20, 30])

            img = render_card(row, bg_color, font_size, date_fmt, padding)
            filename = f"{row['claim_id']}_v{v+1}.png"
            img.save(os.path.join(out_dir, filename))
            total_images += 1

    print(f"{split_name}: generated {total_images} images from {len(df)} claims "
          f"({variations} variation(s) each)")


def main():
    print("Generating Claim Summary Card images...")

    # Training: >=2 variations per claim (SRS requirement)
    generate_cards_for_split("data/processed/train.csv", "train", variations=2)

    # Validation and Testing: exactly 1 image each, no variations, no training use
    generate_cards_for_split("data/processed/val.csv", "val", variations=1)
    generate_cards_for_split("data/processed/test.csv", "test", variations=1)

    print("\nDone. Card images saved under data/claim_summary_cards/")


if __name__ == "__main__":
    main()