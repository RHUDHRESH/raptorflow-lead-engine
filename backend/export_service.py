from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from database import Lead


@dataclass(frozen=True)
class LeadPdfResult:
    lead_id: int
    file_path: Path


def _safe_filename(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "unknown"
    allowed = []
    for ch in value:
        if ch.isalnum() or ch in ("-", "_", "."):
            allowed.append(ch)
        elif ch.isspace():
            allowed.append("-")
    cleaned = "".join(allowed)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-_").lower() or "unknown"


def ensure_exports_dir(base_dir: Path) -> Path:
    exports_dir = base_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir


def _register_fonts() -> None:
    try:
        pdfmetrics.getFont("Inter")
        return
    except Exception:
        pass

    possible = []
    win_dir = Path("C:/Windows/Fonts")
    if win_dir.exists():
        possible.extend(
            [
                win_dir / "segoeui.ttf",
                win_dir / "arial.ttf",
            ]
        )

    for path in possible:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("Inter", str(path)))
                return
            except Exception:
                continue


def generate_lead_pdf(*, lead: Lead, assets_dir: Path) -> LeadPdfResult:
    exports_dir = ensure_exports_dir(assets_dir)
    company_name = lead.company.name if lead.company else "Unknown"
    contact_name: Optional[str] = lead.contact.name if lead.contact else None

    safe_company = _safe_filename(company_name)
    filename = f"lead_{lead.id}_{safe_company}.pdf"
    output_path = exports_dir / filename

    for existing in exports_dir.glob(f"lead_{lead.id}_*.pdf"):
        if existing == output_path:
            continue
        try:
            existing.unlink()
        except Exception:
            pass

    _register_fonts()

    c = canvas.Canvas(str(output_path), pagesize=LETTER)
    width, height = LETTER

    left = 0.75 * inch
    top = height - 0.75 * inch

    title_font = "Inter" if "Inter" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
    body_font = "Inter" if "Inter" in pdfmetrics.getRegisteredFontNames() else "Helvetica"

    c.setTitle(f"Lead {lead.id} - {company_name}")

    c.setFont(title_font, 18)
    c.drawString(left, top, company_name)

    c.setFont(body_font, 10)
    c.setFillGray(0.35)
    c.drawString(left, top - 18, f"Lead ID: {lead.id}  •  Generated: {datetime.utcnow().isoformat(timespec='seconds')}Z")
    c.setFillGray(0)

    y = top - 42

    def field(label: str, value: str) -> None:
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, label)
        c.setFont(body_font, 10)
        c.drawString(left + 150, y, (value or "").strip())
        y -= 14

    field("Website", (lead.company.website if lead.company else "") or "")
    field("Score", f"{lead.total_score or 0:.0f} ({lead.score_bucket or 'parked'})")
    field("Role Type", lead.role_type or "")

    y -= 6
    c.setStrokeGray(0.85)
    c.line(left, y, width - left, y)
    c.setStrokeGray(0)
    y -= 16

    c.setFont(title_font, 12)
    c.drawString(left, y, "Contact")
    y -= 18

    field("Name", contact_name or "")
    field("Email", (lead.contact.email if lead.contact else "") or "")
    phones = ""
    if lead.contact and lead.contact.phone_numbers:
        if isinstance(lead.contact.phone_numbers, list):
            phones = ", ".join([str(p) for p in lead.contact.phone_numbers if p])
        else:
            phones = str(lead.contact.phone_numbers)
    field("Phone(s)", phones)

    y -= 6
    c.setStrokeGray(0.85)
    c.line(left, y, width - left, y)
    c.setStrokeGray(0)
    y -= 16

    c.setFont(title_font, 12)
    c.drawString(left, y, "Why they likely need marketing")
    y -= 18

    text = c.beginText(left, y)
    text.setFont(body_font, 10)

    def write_paragraph(value: Optional[str]) -> None:
        nonlocal text
        raw = (value or "").strip()
        if not raw:
            raw = ""
        for line in raw.splitlines() if raw else [""]:
            for chunk in _wrap_line(line, 95):
                text.textLine(chunk)
        text.textLine("")

    write_paragraph(lead.key_pain)
    write_paragraph(lead.problem)
    write_paragraph(lead.implication)
    write_paragraph(lead.need_payoff)

    c.drawText(text)

    c.showPage()
    c.save()

    return LeadPdfResult(lead_id=lead.id, file_path=output_path)


def _wrap_line(line: str, max_chars: int) -> list[str]:
    if not line:
        return [""]
    words = line.split()
    out: list[str] = []
    current: list[str] = []
    for w in words:
        candidate = " ".join(current + [w])
        if len(candidate) <= max_chars:
            current.append(w)
            continue
        if current:
            out.append(" ".join(current))
            current = [w]
        else:
            out.append(w[:max_chars])
            current = []
    if current:
        out.append(" ".join(current))
    return out
