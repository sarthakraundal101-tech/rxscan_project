"""Rule-based safety checks. These only SURFACE documented information; they never decide."""
import re

from django.db.models import Q

from scanner.models import Interaction


def _words(text):
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower())}


NEGATION_REGEX = re.compile(r"\b(?:no|not|non|never|denies|without|free\s+of)\s+([a-z]+)", re.I)
NONE_SET = {"none", "nil", "na", "n/a", "no", "nothing", "healthy", "normal", "none reported"}


def _extract_active_conditions(text):
    text = (text or "").lower().strip()
    if not text or text in NONE_SET:
        return set()
    negated = set(NEGATION_REGEX.findall(text))
    all_words = {w for w in re.findall(r"[a-z]{3,}", text)}
    return all_words - negated - {"condition", "disease", "patient", "history", "known", "none"}


def _extract_active_allergies(text):
    text = (text or "").lower().strip()
    if not text or text in NONE_SET or "no allerg" in text:
        return "", set()
    negated = set(NEGATION_REGEX.findall(text))
    all_words = {w for w in re.findall(r"[a-z]{3,}", text)}
    active_words = all_words - negated - {"allergies", "allergy", "allergic", "none"}
    return text, active_words


def analyze(prescription):
    """Return dict with interactions, duplicates, patient_warnings for a Prescription."""
    items = [i for i in prescription.items.select_related("medicine") if i.medicine and i.verification_status != "rejected"]
    meds, seen = [], set()
    for it in items:
        if it.medicine_id not in seen:
            seen.add(it.medicine_id)
            meds.append(it.medicine)

    # drug-drug interactions
    ids = [m.id for m in meds]
    interactions = []
    if len(ids) > 1:
        qs = Interaction.objects.filter(medicine_a_id__in=ids, medicine_b_id__in=ids).select_related("medicine_a", "medicine_b")
        order = {"major": 0, "moderate": 1, "minor": 2}
        interactions = sorted(qs, key=lambda x: order[x.severity])

    # duplicates
    duplicates = []
    names = [it.medicine.generic_name for it in items]
    for n in sorted({n for n in names if names.count(n) > 1}):
        duplicates.append(f"{n} appears more than once in this prescription.")
    by_class = {}
    for m in meds:
        by_class.setdefault(m.therapeutic_class, []).append(m.generic_name)
    for cls, group in by_class.items():
        if len(group) > 1:
            duplicates.append(f"Same therapeutic class ({cls}): {', '.join(group)}.")

    # patient-entered conditions / allergies against stored contraindications
    patient_warnings = []
    cond_words = _extract_active_conditions(prescription.conditions)
    allergy_text, allergy_words = _extract_active_allergies(prescription.allergies)

    for m in meds:
        if cond_words:
            for line in m.contraindications_list + m.precautions_list:
                line_words = _words(line)
                hit = cond_words & line_words
                if hit:
                    patient_warnings.append((m.generic_name, f"Entered condition matches a documented warning: {line}"))
        if allergy_text:
            keys = [k.strip().lower() for k in m.allergy_keywords.split(",") if k.strip()] + [m.generic_name.lower()]
            if any(k in allergy_text for k in keys) or (allergy_words & {m.therapeutic_class.lower()}):
                patient_warnings.append((m.generic_name, "Entered allergy may relate to this medicine. Do not use until verified."))
    return {"interactions": interactions, "duplicates": duplicates, "patient_warnings": patient_warnings}
