"""Generate sample medical document images aligned with assignment/sample_documents_guide.md."""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent.parent / "sample-documents"


def _font(size: int = 20, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ("arialbd.ttf", "Arial Bold.ttf") if bold else ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf")
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_document(
    lines: list[str],
    filename: Path,
    *,
    width: int = 920,
    title: str | None = None,
    stamp_at: tuple[int, int] | None = None,
    phone_photo: bool = False,
    quiet: bool = False,
) -> None:
    """Render a guide-style document image."""
    body_font = _font(19)
    title_font = _font(24, bold=True)
    small_font = _font(16)
    padding = 36
    line_height = 30

    height = padding * 2 + (44 if title else 0) + len(lines) * line_height + 40
    img = Image.new("RGB", (width, height), "#fafafa")
    draw = ImageDraw.Draw(img)
    draw.rectangle([8, 8, width - 8, height - 8], outline="#333333", width=2)

    y = padding
    if title:
        draw.text((padding, y), title, fill="#111111", font=title_font)
        y += 44

    for line in lines:
        font = small_font if line.startswith("  ") else body_font
        draw.text((padding, y), line, fill="#1a1a1a", font=font)
        y += line_height

    if stamp_at:
        sx, sy = stamp_at
        draw.ellipse([sx, sy, sx + 140, sy + 50], outline="#cc0000", width=3)
        draw.text((sx + 18, sy + 12), "REG. STAMP", fill="#cc0000", font=small_font)

    if phone_photo:
        img = img.rotate(random.uniform(-2.5, 2.5), expand=True, fillcolor="#e8e8e8")
        img = ImageOps.autocontrast(img)
        img = ImageEnhance.Brightness(img).enhance(0.95)

    filename.parent.mkdir(parents=True, exist_ok=True)
    img.save(filename, format="JPEG", quality=88 if phone_photo else 93)
    if not quiet:
        print(f"Wrote {filename.relative_to(ROOT.parent)}")


def render_blurry(source_lines: list[str], filename: Path, title: str) -> None:
    """Unreadable pharmacy bill — matches guide layout then destroys legibility."""
    tmp = filename.with_suffix(".tmp.jpg")
    render_document(source_lines, tmp, title=title, quiet=True)
    img = Image.open(tmp)
    blurred = img.filter(ImageFilter.GaussianBlur(radius=16))
    small = blurred.resize((img.width // 5, img.height // 5), Image.Resampling.BILINEAR)
    wrecked = small.resize(img.size, Image.Resampling.NEAREST)
    wrecked.save(filename, quality=35)
    tmp.unlink(missing_ok=True)
    print(f"Wrote {filename.relative_to(ROOT.parent)}")


def prescription_rajesh_lines() -> list[str]:
    return [
        "Dr. Arun Sharma, MBBS, MD (Internal Medicine)",
        "Reg. No: KA/45678/2015",
        "City Medical Centre, 12 MG Road, Bengaluru",
        "Ph: +91-80-25551234",
        "────────────────────────────────────────",
        "Patient: Rajesh Kumar          Date: 01-Nov-2024",
        "Age: 39 years   Gender: M",
        "Chief Complaint: Fever since 3 days, body ache",
        "────────────────────────────────────────",
        "Diagnosis: Viral Fever",
        "",
        "Rx:",
        "  1. Tab Paracetamol 650mg — 1-1-1 x 5 days",
        "  2. Tab Vitamin C 500mg — 0-0-1 x 7 days",
        "",
        "Investigations: CBC, Dengue NS1",
        "Follow-up: After 5 days if no improvement",
        "",
        "                          [Doctor's Signature]",
    ]


def hospital_bill_rajesh_lines() -> list[str]:
    return [
        "CITY MEDICAL CENTRE",
        "12 MG Road, Bengaluru – 560001",
        "GSTIN: 29AABCC1234D1Z5",
        "Ph: 080-25551234",
        "────────────────────────────────────────",
        "BILL / RECEIPT",
        "Bill No: CMC/2024/08321    Date: 01-Nov-2024",
        "────────────────────────────────────────",
        "Patient Name: Rajesh Kumar",
        "Age/Gender: 39 / Male",
        "Referring Doctor: Dr. Arun Sharma",
        "────────────────────────────────────────",
        "DESCRIPTION                  QTY   RATE     AMOUNT",
        "Consultation Fee (OPD)         1   1000.00  1000.00",
        "CBC (Complete Blood Count)     1    200.00   200.00",
        "Dengue NS1 Antigen Test        1    300.00   300.00",
        "",
        "Subtotal:                                1500.00",
        "GST (0% on medical):                         0.00",
        "Total Amount:                            1500.00",
        "────────────────────────────────────────",
        "Payment Mode: UPI",
    ]


def pharmacy_bill_sneha_lines() -> list[str]:
    return [
        "HEALTH FIRST PHARMACY",
        "Drug Lic. No: TS/PH/12345",
        "22 Brigade Road, Hyderabad",
        "────────────────────────────────────────",
        "Bill No: HFP-24-09821    Date: 25-Oct-2024",
        "Patient: Sneha Reddy    Dr: Dr. Sunil Patel",
        "────────────────────────────────────────",
        "MEDICINE         BATCH   EXP    QTY   MRP    AMT",
        "Paracetamol 650  A2341   03/26   15   40.00  600.00",
        "Cough Syrup      B7821   06/26    5   40.00  200.00",
        "",
        "Subtotal:                                 800.00",
        "Discount (0%):                              0.00",
        "Net Amount:                               800.00",
        "────────────────────────────────────────",
        "Pharmacist: R. Sharma   [Stamp]",
    ]


def main() -> None:
    # ── Consultation (TC004 / OCR-001) ─────────────────────────────────────
    render_document(
        prescription_rajesh_lines(),
        ROOT / "consultation" / "prescription_rajesh.jpg",
        title="MEDICAL PRESCRIPTION",
        phone_photo=True,
    )

    render_document(
        hospital_bill_rajesh_lines(),
        ROOT / "consultation" / "hospital_bill_rajesh.jpg",
        title="HOSPITAL BILL / CLINIC INVOICE",
        phone_photo=True,
    )

    # ── Edge cases ───────────────────────────────────────────────────────────
    render_document(
        [
            "Dr. Meera Iyer, MBBS (General Medicine)",
            "Reg. No: MH/23456/2018",
            "Sunrise Clinic, Pune",
            "────────────────────────────────────────",
            "Patient: Rajesh Kumar          Date: 01-Nov-2024",
            "Diagnosis: Upper Respiratory Infection (URI)",
            "",
            "Rx:",
            "  1. Tab Azithromycin 500mg — 0-0-1 x 3 days",
        ],
        ROOT / "edge-cases" / "another_prescription.jpg",
        title="MEDICAL PRESCRIPTION",
    )

    render_document(
        prescription_rajesh_lines(),
        ROOT / "edge-cases" / "prescription_rajesh.jpg",
        title="MEDICAL PRESCRIPTION",
        stamp_at=(520, 118),
    )

    render_document(
        [
            "METRO CARE HOSPITAL",
            "45 Whitefield Road, Bengaluru – 560066",
            "Ph: 080-40112233",
            "────────────────────────────────────────",
            "BILL / RECEIPT",
            "Bill No: MCH/2024/11202    Date: 01-Nov-2024",
            "────────────────────────────────────────",
            "Patient Name: Arjun Mehta",
            "Age/Gender: 42 / Male",
            "Referring Doctor: Dr. Vikram Rao",
            "────────────────────────────────────────",
            "DESCRIPTION                  QTY   RATE     AMOUNT",
            "Consultation Fee (OPD)         1   1500.00  1500.00",
            "",
            "Total Amount:                            1500.00",
        ],
        ROOT / "edge-cases" / "bill_arjun.jpg",
        title="HOSPITAL BILL",
    )

    render_blurry(
        pharmacy_bill_sneha_lines(),
        ROOT / "edge-cases" / "blurry_pharmacy_bill.jpg",
        title="PHARMACY BILL / RECEIPT",
    )

    # ── Pharmacy (OCR-004 / OCR-005) ───────────────────────────────────────
    render_document(
        [
            "Dr. Sunil Patel, MBBS",
            "Reg. No: TS/56789/2017",
            "Care Plus Clinic, Hyderabad",
            "────────────────────────────────────────",
            "Patient: Sneha Reddy           Date: 25-Oct-2024",
            "Age: 32 years   Gender: F",
            "Diagnosis: Common Cold",
            "",
            "Rx:",
            "  1. Tab Paracetamol 650mg — SOS",
            "  2. Cough Syrup — 5ml TDS x 5 days",
        ],
        ROOT / "pharmacy" / "prescription_sneha.jpg",
        title="MEDICAL PRESCRIPTION",
    )

    render_document(
        pharmacy_bill_sneha_lines(),
        ROOT / "pharmacy" / "pharmacy_bill_sneha.jpg",
        title="PHARMACY BILL / RECEIPT",
    )

    # ── Dental (OCR-006) ───────────────────────────────────────────────────
    render_document(
        [
            "SMILE DENTAL CLINIC",
            "8 Indiranagar, Bengaluru – 560038",
            "GSTIN: 29SMILE1234F1Z2",
            "────────────────────────────────────────",
            "INVOICE",
            "Bill No: SDC/2024/00456    Date: 15-Oct-2024",
            "────────────────────────────────────────",
            "Patient Name: Priya Singh",
            "Age/Gender: 28 / Female",
            "────────────────────────────────────────",
            "DESCRIPTION                        AMOUNT",
            "Root Canal Treatment (molar)       8000.00",
            "Teeth Whitening (cosmetic)         4000.00",
            "",
            "Total Amount:                     12000.00",
            "────────────────────────────────────────",
            "Payment Mode: Card",
        ],
        ROOT / "dental" / "dental_bill_priya.jpg",
        title="DENTAL TREATMENT BILL",
    )

    # ── Bonus: lab report (guide type 3) ───────────────────────────────────
    render_document(
        [
            "PRECISION DIAGNOSTICS PVT LTD",
            "NABL Accredited Lab   |   Lab ID: KA-NABL-1234",
            "45 Jayanagar, Bengaluru   |  Ph: 080-26661234",
            "────────────────────────────────────────",
            "Patient: Rajesh Kumar",
            "Age/Sex: 39 / Male",
            "Ref Doctor: Dr. Arun Sharma",
            "Sample Date: 01-Nov-2024   Report Date: 01-Nov-2024",
            "Sample ID: PD-2024-18723",
            "────────────────────────────────────────",
            "TEST NAME          RESULT    UNIT    NORMAL RANGE",
            "Hemoglobin         13.2      g/dL    13.0 – 17.0",
            "WBC Count          9,800     /μL     4,500 – 11,000",
            "Dengue NS1 Antigen NEGATIVE           —",
            "────────────────────────────────────────",
            "Remarks: WBC count towards upper normal limit.",
            "Dr. Meena Pillai, MD (Pathology)",
            "Reg. No: KA/89012/2018",
        ],
        ROOT / "diagnostics" / "lab_report_rajesh.jpg",
        title="DIAGNOSTIC / LAB REPORT",
    )

    print(f"\nDone — {ROOT}")


if __name__ == "__main__":
    main()
