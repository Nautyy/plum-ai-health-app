"""Generate sample medical document images for OCR testing."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError as exc:
    raise SystemExit(
        "Pillow required. Run: uv run --with pillow python scripts/generate_sample_documents.py"
    ) from exc

ROOT = Path(__file__).resolve().parent.parent.parent / "sample-documents"


def _font(size: int = 22):
    for name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_document(title: str, lines: list[str], filename: Path, width: int = 900) -> None:
    font = _font(20)
    title_font = _font(26)
    padding = 40
    line_height = 32
    height = padding * 2 + 40 + len(lines) * line_height + 20

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, width - 10, height - 10], outline="#333333", width=2)
    draw.text((padding, padding), title, fill="#1a1a1a", font=title_font)
    y = padding + 44
    for line in lines:
        draw.text((padding, y), line, fill="#222222", font=font)
        y += line_height

    filename.parent.mkdir(parents=True, exist_ok=True)
    img.save(filename, quality=92)
    print(f"Wrote {filename.relative_to(ROOT.parent)}")


def render_blurry(filename: Path) -> None:
    """Simulate an unreadable pharmacy bill photo."""
    lines = [
        "PHARMACY BILL",
        "Patient: Sneha Reddy",
        "Paracetamol 650mg    Rs 120",
        "Total Amount: Rs 800",
    ]
    render_document("BLURRY PHARMACY RECEIPT", lines, filename.with_suffix(".tmp.jpg"))
    img = Image.open(filename.with_suffix(".tmp.jpg"))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=14))
    # Heavy downscale/upscale to destroy text legibility for OCR
    small = blurred.resize((img.width // 6, img.height // 6), Image.Resampling.BILINEAR)
    wrecked = small.resize(img.size, Image.Resampling.NEAREST)
    wrecked.save(filename, quality=40)
    filename.with_suffix(".tmp.jpg").unlink(missing_ok=True)
    print(f"Wrote {filename.relative_to(ROOT.parent)}")


def main() -> None:
    render_document(
        "MEDICAL PRESCRIPTION",
        [
            "Doctor: Dr. Arun Sharma",
            "Registration: KA/45678/2015",
            "Patient Name: Rajesh Kumar",
            "Date: 2024-11-01",
            "Diagnosis: Viral Fever",
            "Medicines: Paracetamol 650mg, Vitamin C 500mg",
        ],
        ROOT / "consultation" / "prescription_rajesh.jpg",
    )

    render_document(
        "HOSPITAL BILL / RECEIPT",
        [
            "Hospital: City Clinic, Bengaluru",
            "Patient Name: Rajesh Kumar",
            "Date: 2024-11-01",
            "Consultation Fee          Rs 1000",
            "CBC Test                  Rs 300",
            "Dengue NS1 Test           Rs 200",
            "Total Amount: Rs 1500",
        ],
        ROOT / "consultation" / "hospital_bill_rajesh.jpg",
    )

    render_document(
        "MEDICAL PRESCRIPTION",
        [
            "Doctor: Dr. Meera Iyer",
            "Patient Name: Rajesh Kumar",
            "Date: 2024-11-01",
            "Diagnosis: Upper Respiratory Infection",
            "Rx: Azithromycin 500mg",
        ],
        ROOT / "edge-cases" / "another_prescription.jpg",
    )

    render_document(
        "MEDICAL PRESCRIPTION",
        [
            "Doctor: Dr. Arun Sharma",
            "Patient Name: Rajesh Kumar",
            "Date: 2024-11-01",
            "Diagnosis: Viral Fever",
        ],
        ROOT / "edge-cases" / "prescription_rajesh.jpg",
    )

    render_document(
        "HOSPITAL BILL",
        [
            "Hospital: Metro Care Hospital",
            "Patient Name: Arjun Mehta",
            "Date: 2024-11-01",
            "Consultation Fee          Rs 1500",
            "Total Amount: Rs 1500",
        ],
        ROOT / "edge-cases" / "bill_arjun.jpg",
    )

    render_document(
        "MEDICAL PRESCRIPTION",
        [
            "Doctor: Dr. Sunil Patel",
            "Patient Name: Sneha Reddy",
            "Date: 2024-10-25",
            "Diagnosis: Common Cold",
            "Medicines: Paracetamol 650mg",
        ],
        ROOT / "pharmacy" / "prescription_sneha.jpg",
    )

    render_document(
        "PHARMACY BILL",
        [
            "Store: Apollo Pharmacy, Hyderabad",
            "Drug Lic No: TS/PH/12345",
            "Patient Name: Sneha Reddy",
            "Date: 2024-10-25",
            "Paracetamol 650mg         Rs 120",
            "Cough Syrup               Rs 180",
            "Total Amount: Rs 800",
        ],
        ROOT / "pharmacy" / "pharmacy_bill_sneha.jpg",
    )

    render_blurry(ROOT / "edge-cases" / "blurry_pharmacy_bill.jpg")

    render_document(
        "DENTAL TREATMENT BILL",
        [
            "Clinic: Smile Dental Clinic",
            "Patient Name: Priya Singh",
            "Date: 2024-10-15",
            "Root Canal Treatment      Rs 8000",
            "Teeth Whitening           Rs 4000",
            "Total Amount: Rs 12000",
        ],
        ROOT / "dental" / "dental_bill_priya.jpg",
    )

    print(f"\nDone — sample images in {ROOT}")


if __name__ == "__main__":
    main()
