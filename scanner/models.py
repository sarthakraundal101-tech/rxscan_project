import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLES = [("patient", "Patient / User"), ("pharmacist", "Pharmacist / Doctor")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLES, default="patient")

    def __str__(self):
        return f"{self.user.username} ({self.role})"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


def is_pharmacist(user):
    if user.is_superuser:
        return True
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile.role == "pharmacist"


def _lines(text):
    return [l.strip() for l in (text or "").splitlines() if l.strip()]


class Medicine(models.Model):
    generic_name = models.CharField(max_length=120, unique=True)
    brand_names = models.CharField(max_length=300, blank=True, help_text="Comma separated")
    strengths = models.CharField(max_length=200, blank=True, help_text="Comma separated, e.g. 500 mg, 650 mg")
    therapeutic_class = models.CharField(max_length=120)
    uses = models.TextField(help_text="One per line")
    side_effects = models.TextField(help_text="One per line")
    contraindications = models.TextField(help_text="One per line")
    precautions = models.TextField(blank=True, help_text="One per line")
    allergy_keywords = models.CharField(max_length=200, blank=True, help_text="Comma separated")
    age_infant = models.TextField(blank=True)
    age_child = models.TextField(blank=True)
    age_adolescent = models.TextField(blank=True)
    age_adult = models.TextField(blank=True)
    age_older = models.TextField(blank=True)
    source = models.CharField(max_length=200, default="General pharmacology reference (verify before use)")
    last_updated = models.DateField(auto_now=True)

    class Meta:
        ordering = ["generic_name"]

    def __str__(self):
        return self.generic_name

    @property
    def code(self):
        return f"MED{self.pk:03d}"

    @property
    def brand_list(self):
        return [b.strip() for b in self.brand_names.split(",") if b.strip()]

    @property
    def strength_list(self):
        return [s.strip() for s in self.strengths.split(",") if s.strip()]

    @property
    def uses_list(self):
        return _lines(self.uses)

    @property
    def side_effects_list(self):
        return _lines(self.side_effects)

    @property
    def contraindications_list(self):
        return _lines(self.contraindications)

    @property
    def precautions_list(self):
        return _lines(self.precautions)

    @property
    def age_groups(self):
        pairs = [("Infant", self.age_infant), ("Child", self.age_child),
                 ("Adolescent", self.age_adolescent), ("Adult", self.age_adult),
                 ("Older adult", self.age_older)]
        return [(label, text) for label, text in pairs if text]


class Interaction(models.Model):
    SEVERITY = [("minor", "Minor"), ("moderate", "Moderate"), ("major", "Major")]
    medicine_a = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="+")
    medicine_b = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="+")
    severity = models.CharField(max_length=10, choices=SEVERITY)
    description = models.TextField()

    def __str__(self):
        return f"{self.medicine_a} + {self.medicine_b} ({self.severity})"


class Prescription(models.Model):
    STATUS = [
        ("unreadable", "Unreadable"),
        ("ready", "AI matched - awaiting verification"),
        ("pending_review", "Pending pharmacist review"),
        ("verified", "Pharmacist verified"),
    ]
    AGE_GROUPS = [("", "Not specified"), ("infant", "Infant"), ("child", "Child"),
                  ("adolescent", "Adolescent"), ("adult", "Adult"), ("older", "Older adult")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prescriptions")
    image = models.FileField(upload_to="prescriptions/")
    preview = models.ImageField(upload_to="previews/", blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    age_group = models.CharField(max_length=12, choices=AGE_GROUPS, blank=True)
    conditions = models.CharField("Medical conditions", max_length=300, blank=True)
    allergies = models.CharField(max_length=300, blank=True)
    ocr_text = models.TextField(blank=True)
    ocr_confidence = models.FloatField(default=0)
    quality_notes = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="pending_review")
    status_note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    @property
    def is_pdf(self):
        return self.image.name.lower().endswith(".pdf")

    @property
    def display_url(self):
        if self.preview:
            return self.preview.url
        return None if self.is_pdf else self.image.url

    @property
    def code(self):
        return f"P{self.pk:04d}"

    @property
    def filename(self):
        return os.path.basename(self.image.name)


class PrescriptionItem(models.Model):
    VSTATUS = [("auto", "Automatically matched"), ("verified", "Verified"), ("rejected", "Rejected")]
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="items")
    detected_text = models.CharField(max_length=200)
    medicine = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True, blank=True)
    strength = models.CharField(max_length=40, blank=True)
    frequency = models.CharField(max_length=40, blank=True)
    duration = models.CharField(max_length=40, blank=True)
    confidence = models.FloatField(default=0)
    alternatives = models.JSONField(default=list, blank=True)  # [{"id":..,"name":..,"score":..}]
    note = models.CharField(max_length=300, blank=True)
    verification_status = models.CharField(max_length=10, choices=VSTATUS, default="auto")

    class Meta:
        ordering = ["id"]

    @property
    def band(self):
        if self.verification_status == "verified":
            return "verified"
        if self.verification_status == "rejected" or not self.medicine:
            return "low"
        if self.confidence >= settings.CONF_HIGH:
            return "high"
        if self.confidence >= settings.CONF_REVIEW:
            return "review"
        return "low"

    @property
    def band_label(self):
        return {"verified": "Pharmacist verified", "high": "Potential match",
                "review": "Review recommended", "low": "Verification required"}[self.band]


class Verification(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="verifications")
    pharmacist = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField(blank=True)
    corrections = models.TextField(blank=True)
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-verified_at"]
