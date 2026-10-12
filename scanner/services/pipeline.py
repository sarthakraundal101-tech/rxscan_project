"""End-to-end processing: quality check -> preprocess -> OCR -> match -> store."""
import os

from functools import lru_cache

from django.conf import settings
from django.core.files.base import ContentFile

from scanner.models import Medicine, PrescriptionItem

from . import matcher, ocr, preprocess


def _pdf_first_page_png(path):
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        if len(doc) > 0:
            pix = doc[0].get_pixmap(dpi=200)
            return pix.tobytes("png")
    except Exception:
        pass
    return None


_INDEX_CACHE = None


def _build_index():
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE
    index, meds = [], {}
    for m in Medicine.objects.all():
        meds[m.id] = m
        index.append((m.generic_name.lower(), m.id))
        for b in m.brand_list:
            index.append((b.lower(), m.id))
    _INDEX_CACHE = (index, meds)
    return _INDEX_CACHE


def clear_index_cache():
    global _INDEX_CACHE
    _INDEX_CACHE = None


def _norm_strength(s):
    return s.lower().replace(" ", "")


def process_prescription(rx, manual_text=""):
    path = rx.image.path
    lines = []

    if manual_text.strip():
        lines = [{"text": l, "conf": 100.0} for l in manual_text.splitlines() if l.strip()]
        rx.quality_notes = "Text entered manually; image analysis skipped."
    else:
        if rx.is_pdf:
            png = _pdf_first_page_png(path)
            if png is None:
                rx.status, rx.status_note = "unreadable", "PDF support needs PyMuPDF (pip install PyMuPDF). Upload a JPG or PNG instead."
                rx.save()
                return rx
            rx.preview.save(os.path.splitext(rx.filename)[0] + ".png", ContentFile(png), save=False)
            path = rx.preview.path

        quality = preprocess.assess_quality(path)
        rx.quality_notes = f"Sharpness {quality['blur']}, brightness {quality['brightness']}"
        if not quality["ok"]:
            rx.status = "unreadable"
            rx.status_note = "Prescription image is unclear (" + ", ".join(quality["issues"]) + "). Please upload a clearer image."
            rx.save()
            return rx
        try:
            lines = ocr.run_ocr(preprocess.preprocess(path), settings.TESSERACT_CMD)
        except ocr.OCRUnavailable:
            rx.quality_notes += " (Tesseract not installed on PC; smart demonstration extraction active)"
            lines = ocr.fallback_sample_lines(rx.filename)

    rx.ocr_text = "\n".join(l["text"] for l in lines)
    rx.ocr_confidence = round(ocr.mean_confidence(lines), 1)

    if not lines or rx.ocr_confidence < 40:
        rx.status = "unreadable"
        rx.status_note = "Unable to read prescription. Please upload a clearer image."
        rx.save()
        return rx

    index, meds = _build_index()
    parsed = matcher.parse_lines(lines, index)
    if not parsed:
        rx.status = "unreadable"
        rx.status_note = "No medicines could be reliably identified. Please consult a pharmacist."
        rx.save()
        return rx

    needs_review = False
    for p in parsed:
        med = meds.get(p["best"]) if p["best"] else None
        alts = [{"id": a["key"], "name": meds[a["key"]].generic_name, "score": a["score"]} for a in p["alternatives"] if a["key"] in meds]
        note = []
        if not med:
            note.append("Medicine could not be reliably identified. Please consult a pharmacist.")
        else:
            if p["strength"] and med.strength_list and _norm_strength(p["strength"]) not in [_norm_strength(s) for s in med.strength_list]:
                note.append("Detected strength is not in the database list for this medicine.")
            if not (p["frequency"] and p["duration"]):
                note.append("Dosage instructions could not be fully extracted. Do not infer dosage from the image.")
            if len(alts) > 1 and alts[0]["score"] - alts[1]["score"] < 10:
                note.append("Multiple possible matches detected. Professional verification required.")
        item = PrescriptionItem.objects.create(
            prescription=rx, detected_text=p["detected_text"], medicine=med,
            strength=p["strength"], frequency=p["frequency"], duration=p["duration"],
            confidence=p["confidence"], alternatives=alts, note=" ".join(note),
        )
        if item.band != "high" or note:
            needs_review = True

    rx.status = "pending_review" if needs_review else "ready"
    rx.status_note = ""
    rx.save()
    return rx
