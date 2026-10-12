from django.contrib import admin

from .models import Interaction, Medicine, Prescription, PrescriptionItem, Profile, Verification

admin.site.register(Profile)
admin.site.register(Medicine)
admin.site.register(Interaction)
admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
admin.site.register(Verification)
