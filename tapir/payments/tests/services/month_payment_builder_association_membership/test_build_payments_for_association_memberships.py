from unittest.mock import patch, Mock, call

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildPaymentsForAssociationMemberships(TapirUnitTest):
    @patch.object(
        MonthPaymentBuilderUtils, "build_payment_for_contract_and_member", autospec=True
    )
    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "get_active_memberships",
        autospec=True,
    )
    def test_buildPaymentsForAssociationMemberships_default_buildsPaymentsCorrectly(
        self,
        mock_get_active_memberships: Mock,
        mock_get_member_payment_rhythm: Mock,
        mock_build_payment_for_contract_and_member: Mock,
    ):
        member_1 = MemberFactory.build(pk="m1")
        member_2 = MemberFactory.build(pk="m2")
        member_3 = MemberFactory.build(pk="m3")
        members = [member_1, member_2, member_3]
        memberships = [
            AssociationMembershipFactory.build(member=member_1),
            AssociationMembershipFactory.build(member=member_1),
            AssociationMembershipFactory.build(member=member_2),
            AssociationMembershipFactory.build(member=member_3),
        ]
        memberships_by_member = {
            member_1: {memberships[0], memberships[1]},
            member_2: {memberships[2]},
            member_3: {memberships[3]},
        }

        mock_get_active_memberships.return_value = memberships
        payment_rhythms = {
            member_1: MemberPaymentRhythm.Rhythm.QUARTERLY,
            member_2: MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            member_3: MemberPaymentRhythm.Rhythm.MONTHLY,
        }
        mock_get_member_payment_rhythm.side_effect = (
            lambda member, **kwargs: payment_rhythms[member]
        )
        payments = {
            member_1: PaymentFactory.build(),
            member_2: None,
            member_3: PaymentFactory.build(),
        }
        mock_build_payment_for_contract_and_member.side_effect = (
            lambda member, **kwargs: payments[member]
        )
        cache = Mock()
        current_month = Mock()
        generated_payments = Mock()

        result = MonthPaymentBuilderAssociationMembership.build_payments_for_association_memberships(
            current_month=current_month,
            cache=cache,
            generated_payments=generated_payments,
        )

        self.assertEqual({payments[member_1], payments[member_3]}, set(result))

        mock_get_active_memberships.assert_called_once_with(
            cache=cache, first_of_month=current_month
        )
        self.assertEqual(3, mock_get_member_payment_rhythm.call_count)

        mock_get_member_payment_rhythm.assert_has_calls(
            [
                call(
                    member=member,
                    reference_date=current_month,
                    cache=cache,
                )
                for member in members
            ],
            any_order=True,
        )

        self.assertEqual(3, mock_build_payment_for_contract_and_member.call_count)
        mock_build_payment_for_contract_and_member.assert_has_calls(
            [
                call(
                    member=member,
                    first_of_month=current_month,
                    contracts=memberships_by_member[member],
                    rhythm=payment_rhythms[member],
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=False,
                    payment_type="payment_type_association_membership",
                    total_to_pay_function=MonthPaymentBuilderAssociationMembership.get_total_to_pay,
                    allow_negative_amounts=False,
                )
                for member in members
            ],
            any_order=True,
        )
