from django.test import TestCase

# Create your tests here.
from tapir.wirgarten.service.payment import (
    generate_mandate_ref,
    MANDATE_REF_LENGTH,
    is_mandate_ref_for_coop_shares,
)


class MandateReferenceTestCase(TestCase):
    def test_mandate_ref_length(self):
        member_id = "XXXXXXXXXX"

        geno_ref = generate_mandate_ref(member_id, True)
        self.assertEqual(len(geno_ref), MANDATE_REF_LENGTH)

        subs_ref = generate_mandate_ref(member_id, False)
        self.assertEqual(len(subs_ref), MANDATE_REF_LENGTH)

    def test_mandate_ref_suffix(self):
        member_id = "XXXXXXXXXX"

        geno_ref = generate_mandate_ref(member_id, True)
        self.assertEqual(geno_ref.endswith("/GENO"), True)

        subs_ref = generate_mandate_ref(member_id, False)
        self.assertEqual(subs_ref.endswith("/PROD"), True)

    def test_mandate_ref_userid(self):
        member_id = "XXXXXXXXXX"

        geno_ref = generate_mandate_ref(member_id, True)
        self.assertEqual(geno_ref.startswith(member_id + "/"), True)

        subs_ref = generate_mandate_ref(member_id, False)
        self.assertEqual(subs_ref.startswith(member_id + "/"), True)

    def test_mandate_ref_old_userid(self):
        member_id = 1001

        geno_ref = generate_mandate_ref(member_id, True)
        self.assertEqual(geno_ref.startswith(f"""000000{str(member_id)}/"""), True)

        subs_ref = generate_mandate_ref(member_id, False)
        self.assertEqual(subs_ref.startswith(f"""000000{str(member_id)}/"""), True)

    def test_mandate_ref_distinction(self):
        member_id = "XXXXXXXXXX"

        geno_ref = generate_mandate_ref(member_id, True)
        self.assertEqual(is_mandate_ref_for_coop_shares(geno_ref), True)

        subs_ref = generate_mandate_ref(member_id, False)
        self.assertEqual(is_mandate_ref_for_coop_shares(subs_ref), False)
