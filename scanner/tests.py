from django.contrib.auth.models import User
from django.test import TestCase

from scanner.models import Interaction, Medicine, Prescription, PrescriptionItem, Profile, is_pharmacist
from scanner.services import matcher, pipeline, safety


class MedicineMatcherTest(TestCase):
    def setUp(self):
        self.para = Medicine.objects.create(
            generic_name="Paracetamol",
            brand_names="Crocin, Dolo, Calpol, Metacin, PCM",
            strengths="500 mg, 650 mg",
            therapeutic_class="Analgesic",
            uses="Fever\nPain",
            side_effects="Nausea",
            contraindications="Severe liver impairment",
        )
        self.panto = Medicine.objects.create(
            generic_name="Pantoprazole",
            brand_names="Pan, Pantop, Protonix",
            strengths="20 mg, 40 mg",
            therapeutic_class="Proton pump inhibitor",
            uses="Acidity\nGERD",
            side_effects="Headache",
            contraindications="Allergy to PPI",
        )
        pipeline.clear_index_cache()
        self.index, _ = pipeline._build_index()

    def test_short_token_matching(self):
        """Verify short brand tokens like 'Pan' and 'PCM' are extracted and matched."""
        lines = [{"text": "Tab. Pan 40 mg 1-0-0 5 days", "conf": 95.0}]
        parsed = matcher.parse_lines(lines, self.index)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["best"], self.panto.id)
        self.assertEqual(parsed[0]["strength"], "40 mg")
        self.assertEqual(parsed[0]["frequency"], "1-0-0")
        self.assertEqual(parsed[0]["duration"], "5 days")

    def test_frequency_variations(self):
        """Verify OD, BD, and word frequencies like 'once daily'."""
        lines = [{"text": "Tab. Dolo 650 mg ONCE DAILY for 3 days", "conf": 92.0}]
        parsed = matcher.parse_lines(lines, self.index)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["best"], self.para.id)
        self.assertEqual(parsed[0]["strength"], "650 mg")
        self.assertEqual(parsed[0]["frequency"], "ONCE DAILY")
        self.assertEqual(parsed[0]["duration"], "3 days")


class SafetyEngineTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="patient1", password="password123")
        self.warfarin = Medicine.objects.create(
            generic_name="Warfarin",
            brand_names="Coumadin",
            strengths="5 mg",
            therapeutic_class="Anticoagulant",
            uses="Blood clot prevention",
            side_effects="Bleeding",
            contraindications="Active bleeding\nPregnancy",
            precautions="Avoid alcohol",
            allergy_keywords="warfarin",
        )
        self.aspirin = Medicine.objects.create(
            generic_name="Aspirin",
            brand_names="Disprin, Ecosprin",
            strengths="75 mg",
            therapeutic_class="NSAID / Antiplatelet",
            uses="Pain\nHeart prevention",
            side_effects="Stomach irritation",
            contraindications="Stomach ulcer\nAsthma",
            precautions="Take with food",
            allergy_keywords="aspirin, salicylate, nsaid",
        )
        Interaction.objects.create(
            medicine_a=self.warfarin,
            medicine_b=self.aspirin,
            severity="major",
            description="High risk of bleeding.",
        )

    def test_interaction_detection(self):
        """Prescription with Warfarin and Aspirin surfaces major interaction."""
        rx = Prescription.objects.create(user=self.user)
        PrescriptionItem.objects.create(prescription=rx, detected_text="Warfarin", medicine=self.warfarin)
        PrescriptionItem.objects.create(prescription=rx, detected_text="Aspirin", medicine=self.aspirin)

        report = safety.analyze(rx)
        self.assertEqual(len(report["interactions"]), 1)
        self.assertEqual(report["interactions"][0].severity, "major")

    def test_negation_in_conditions(self):
        """'No asthma' condition should NOT trigger an asthma contraindication warning."""
        rx = Prescription.objects.create(user=self.user, conditions="No asthma, healthy")
        PrescriptionItem.objects.create(prescription=rx, detected_text="Aspirin", medicine=self.aspirin)

        report = safety.analyze(rx)
        # Should not flag asthma because it's negated
        asthma_warnings = [text for name, text in report["patient_warnings"] if "asthma" in text.lower()]
        self.assertEqual(len(asthma_warnings), 0)

    def test_active_condition_triggers_warning(self):
        """Active condition 'Severe stomach ulcer' MUST trigger contraindication warning."""
        rx = Prescription.objects.create(user=self.user, conditions="stomach ulcer")
        PrescriptionItem.objects.create(prescription=rx, detected_text="Aspirin", medicine=self.aspirin)

        report = safety.analyze(rx)
        ulcer_warnings = [text for name, text in report["patient_warnings"] if "ulcer" in text.lower()]
        self.assertGreaterEqual(len(ulcer_warnings), 1)
