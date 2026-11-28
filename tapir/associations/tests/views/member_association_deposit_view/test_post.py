from decimal import Decimal

from tapir.associations.models import (
    AssociationDepositTransaction,
    AssociationDepositAgreedLogEntry,
)
from tapir.associations.tests.views.member_association_deposit_view.base import (
    MemberAssociationDepositViewTestCase,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import MemberFactory


class TestMemberAssociationDepositViewPost(MemberAssociationDepositViewTestCase):
    def post_increase(self, **values):
        return self.client.post(
            self.url,
            {"total_amount": "250", "confirmation": True, **values},
            content_type="application/json",
        )

    def test_post_default_createsOnlyDifference(self):
        self.assertStatusCode(self.post_increase(), 200)
        self.assertCountEqual(
            [Decimal("200"), Decimal("50")],
            AssociationDepositTransaction.objects.filter(
                member=self.member
            ).values_list("amount", flat=True),
        )

    def test_post_repeatedTotal_rejectsWithoutNewPayment(self):
        self.assertStatusCode(self.post_increase(), 200)
        self.assertStatusCode(self.post_increase(), 400)
        self.assertEqual(2, AssociationDepositTransaction.objects.count())

    def test_post_missingConfirmation_createsNoTransaction(self):
        self.assertStatusCode(self.post_increase(confirmation=False), 400)
        self.assertEqual(1, AssociationDepositTransaction.objects.count())

    def test_post_disabledFeature_returns403(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        self.assertStatusCode(self.post_increase(), 403)
        self.assertEqual(1, AssociationDepositTransaction.objects.count())

    def test_post_memberIncreaseDisabled_returns403(self):
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, False
        )
        self.assertStatusCode(self.post_increase(), 403)

    def test_post_otherMember_returns403(self):
        self.client.force_login(MemberFactory.create())
        self.assertStatusCode(self.post_increase(), 403)

    def test_post_adminAndMemberIncreaseDisabled_createsAttributedIncrease(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, False
        )
        self.assertStatusCode(self.post_increase(), 200)
        entry = AssociationDepositAgreedLogEntry.objects.get(amount=50)
        self.assertEqual(admin.pk, entry.actor_id)
        self.assertEqual(self.member.pk, entry.user_id)
