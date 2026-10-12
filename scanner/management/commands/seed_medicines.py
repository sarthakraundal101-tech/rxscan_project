from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from scanner.models import Interaction, Medicine, Profile
from scanner.seed_data import INTERACTIONS, MEDICINES


class Command(BaseCommand):
    help = "Load the starter medicine database, interactions and demo accounts."

    def handle(self, *args, **options):
        for data in MEDICINES:
            Medicine.objects.update_or_create(generic_name=data["generic_name"], defaults=data)
        by_name = {m.generic_name: m for m in Medicine.objects.all()}
        Interaction.objects.all().delete()
        for a, b, sev, desc in INTERACTIONS:
            Interaction.objects.create(medicine_a=by_name[a], medicine_b=by_name[b], severity=sev, description=desc)

        for username, role, name in [("demo", "patient", "Demo User"), ("patient", "patient", "Demo Patient"), ("pharmacist", "pharmacist", "Demo Pharmacist")]:
            user, created = User.objects.get_or_create(username=username, defaults={"first_name": name})
            user.set_password("demo12345")
            user.save()
            Profile.objects.update_or_create(user=user, defaults={"role": role})
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(MEDICINES)} medicines, {len(INTERACTIONS)} interactions. "
            "Demo login: demo / demo12345"))
