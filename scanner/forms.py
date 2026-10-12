import io
import os
from PIL import Image, ImageDraw

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Prescription


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="Full name", max_length=60)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ("first_name", "username", "email", "password1", "password2")


def _generate_prescription_graphic(text):
    """Generate a realistic digital prescription graphic when text is entered without an image."""
    width, height = 900, 650
    img = Image.new("RGB", (width, height), color=(253, 255, 254))
    draw = ImageDraw.Draw(img)

    # Outer border & header banner
    draw.rectangle([(25, 25), (width - 25, height - 25)], outline=(34, 168, 125), width=3)
    draw.rectangle([(32, 32), (width - 32, 115)], fill=(240, 250, 246))

    # Header text
    draw.text((50, 48), "Rx CLINICAL PRESCRIPTION RECORD", fill=(10, 61, 44))
    draw.text((50, 78), "Clinical Informatics & Medicine Verification System", fill=(82, 102, 92))

    # Divider
    draw.line([(32, 115), (width - 32, 115)], fill=(177, 240, 216), width=2)

    # Rx symbol
    draw.text((50, 135), "Rx:", fill=(20, 108, 79))

    # Lines
    y = 175
    for line in text.splitlines():
        line = line.strip()
        if line:
            draw.text((65, y), line, fill=(15, 31, 24))
            y += 38

    # Footer
    draw.line([(32, height - 70), (width - 32, height - 70)], fill=(225, 235, 229), width=1)
    draw.text((50, height - 52), "Digitally Generated Prescription Sheet - MediScan AI Engine", fill=(121, 144, 132))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile("prescription_document.png", buf.getvalue(), content_type="image/png")


class UploadForm(forms.ModelForm):
    manual_text = forms.CharField(
        label="Type or paste prescription text (optional)",
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Tab. Paracetamol 650 mg 1-0-1 5 days\nTab. Pantoprazole 40 mg OD 5 days",
            "id": "id_manual_text"
        }),
        help_text="One medicine per line. Example: Tab. Paracetamol 500 mg 1-0-1 5 days"
    )

    class Meta:
        model = Prescription
        fields = ("image", "age_group", "conditions", "allergies")
        labels = {"image": "Prescription file", "age_group": "Patient age group"}
        widgets = {
            "conditions": forms.TextInput(attrs={"placeholder": "e.g. asthma, kidney disease"}),
            "allergies": forms.TextInput(attrs={"placeholder": "e.g. penicillin, aspirin"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].required = False

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get("image")
        manual_text = cleaned_data.get("manual_text", "").strip()

        if not image and not manual_text:
            raise forms.ValidationError("Please upload a prescription image or enter the prescription text below.")

        if image:
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".pdf"):
                self.add_error("image", "Upload a JPG, PNG or PDF file.")
            elif image.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
                self.add_error("image", f"File is larger than {settings.MAX_UPLOAD_MB} MB.")
        elif manual_text:
            cleaned_data["image"] = _generate_prescription_graphic(manual_text)

        return cleaned_data
