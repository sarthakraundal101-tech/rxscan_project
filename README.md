# RxScan: AI-Based Prescription Scanner and Medicine Information System

A Django web application that scans a prescription image, extracts the medicines with OCR,
matches them to a medicine database, shows verified reference information, and sends uncertain
results to a pharmacist for human-in-the-loop verification.

> **The system never prescribes a medicine or tells a patient what dose to take.** It shows the
> dosage *detected on the prescription* and reference information, and always asks for
> professional verification.

## Quick start

1. Install **Python 3.10+** and the **Tesseract OCR engine**
   - Windows: https://github.com/UB-Mannheim/tesseract/wiki (then set `TESSERACT_CMD` in `rxscan/settings.py`)
   - Ubuntu/Debian: `sudo apt install tesseract-ocr`
   - macOS: `brew install tesseract`
2. Run `./setup.sh` (macOS/Linux) or `setup.bat` (Windows). This creates a virtual environment,
   installs requirements, creates the database, loads 22 medicines and 19 interactions, and starts the server.
3. Open http://127.0.0.1:8000

Demo accounts (created by the seed command): `patient / demo12345` and `pharmacist / demo12345`.
Admin site: run `python manage.py createsuperuser`, then open `/admin/`.

Manual steps if you prefer: `pip install -r requirements.txt`, `python manage.py makemigrations scanner`,
`python manage.py migrate`, `python manage.py seed_medicines`, `python manage.py runserver`.

If Tesseract is missing, the upload page still works: use "Type the prescription instead".

## How it works

```
Upload -> Quality check (blur, brightness, contrast, size) -> Preprocess (resize, denoise,
CLAHE contrast, deskew) -> Tesseract OCR -> Parse (medicine, strength, frequency, duration)
-> Fuzzy match to generic + brand names -> Confidence score -> Safety checks
-> High confidence: info shown   |   Low confidence: pharmacist review -> Verified result
```

| Module | File |
| --- | --- |
| Image quality + preprocessing (OpenCV) | `scanner/services/preprocess.py` |
| OCR (Tesseract) | `scanner/services/ocr.py` |
| Medicine extraction + fuzzy matching | `scanner/services/matcher.py` |
| Interactions, contraindications, duplicates | `scanner/services/safety.py` |
| Orchestration | `scanner/services/pipeline.py` |
| Models / database schema | `scanner/models.py` |
| Medicine data | `scanner/seed_data.py` |

**Confidence bands** (`CONF_HIGH = 90`, `CONF_REVIEW = 70` in `settings.py`): >=90 potential match,
70-90 review recommended, <70 mandatory human verification. These are project defaults. Validate them
with your own test dataset before claiming any accuracy figures.

## Roles
- **Patient / User:** register, upload, view results and history, browse the medicine database.
- **Pharmacist / Doctor:** review queue, correct or confirm each medicine, add remarks, approve.
  Make a user a pharmacist in `/admin/` (Profile -> role), or use the demo pharmacist account.

## Limitations (mention these in your report)
- Tesseract is strongest on printed text. Handwriting accuracy is limited, which is why low-confidence
  results require pharmacist review. For better handwriting recognition, plug in a handwriting OCR model in `ocr.py`.
- The starter medicine data is general and qualitative. Validate it against an official formulary before any real use.
- Only the first page of a PDF is read.
- Thresholds and fuzzy-match scores are not clinically validated.

## Suggested report mapping
Problem statement -> objectives -> modules (above) -> ER diagram (models.py) -> DFD (pipeline diagram) ->
architecture -> database schema -> UI screens -> testing (try blurry, rotated, handwritten and misspelled prescriptions).
