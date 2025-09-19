from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExistingMemberPurchasesSharesAPIView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_normalMemberPurchaseSharesForAnotherMember_returns403AndDontPurchaseAnything(
        self,
    ):
        purchasing_member = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create()
        self.client.force_login(purchasing_member)

        url = reverse("coop:existing_member_purchases_shares")
        url = f"{url}?member_id={other_member.id}&number_of_shares_to_add=2"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(CoopShareTransaction.objects.exists())

    def test_post_normalMemberPurchaseSharesForThemselves_executePurchase(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        url = reverse("coop:existing_member_purchases_shares")
        url = f"{url}?member_id={member.id}&number_of_shares_to_add=2"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, CoopShareTransaction.objects.count())
        self.assertEqual(2, CoopShareTransaction.objects.get().quantity)

    def test_post_adminPurchaseSharesForAnotherMember_executePurchase(self):
        admin = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(admin)

        url = reverse("coop:existing_member_purchases_shares")
        url = f"{url}?member_id={other_member.id}&number_of_shares_to_add=3"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, CoopShareTransaction.objects.count())
        self.assertEqual(3, CoopShareTransaction.objects.get().quantity)

    def test_post_memberIsStudent_dontValidateMinimumNumberOfShares(self):
        member = MemberFactory.create(is_student=True)
        self.client.force_login(member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_MIN_SHARES).update(value=5)

        url = reverse("coop:existing_member_purchases_shares")
        url = f"{url}?member_id={member.id}&number_of_shares_to_add=1"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, CoopShareTransaction.objects.count())
        self.assertEqual(1, CoopShareTransaction.objects.get().quantity)

    def test_post_memberIsNotStudent_validateMinimumNumberOfShares(self):
        member = MemberFactory.create(is_student=False)
        self.client.force_login(member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_MIN_SHARES).update(value=5)

        url = reverse("coop:existing_member_purchases_shares")
        url = f"{url}?member_id={member.id}&number_of_shares_to_add=1"

        with self.assertRaises(ValidationError):
            self.client.post(url)

        self.assertFalse(CoopShareTransaction.objects.exists())
