import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from tapir.bestell_wizard.services.bestell_wizard_order_fulfiller import (
    BestellWizardOrderFulfiller,
)
from tapir.bidding_round.config import BIDDING_ROUND_STATUS_CLOSED
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
    BiddingRoundProductTypeFactory,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBestellWizardOrderFulfillerLatecomerFloor(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_fulfiller.send_product_order_confirmation"
    )
    @patch.object(BestellWizardOrderFulfiller, "create_questionnaire_responses")
    @patch.object(
        BestellWizardOrderFulfiller,
        "create_solidarity_contribution",
        return_value=None,
    )
    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_fulfiller.legal_status_is_association",
        return_value=False,
    )
    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_fulfiller.legal_status_is_cooperative",
        return_value=False,
    )
    @patch.object(BestellWizardOrderFulfiller, "create_subscriptions")
    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_fulfiller.MemberPaymentRhythmService.assign_payment_rhythm_to_member"
    )
    @patch.object(BestellWizardOrderFulfiller, "create_member")
    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_fulfiller.OrderValidator.does_order_need_a_pickup_location",
        return_value=False,
    )
    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_fulfiller.TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer"
    )
    def test_createMemberAndFulfillOrder_latecomer_usesFloorInContributionAndMail(
        self,
        mock_build_order,
        mock_does_order_need_pickup_location,
        mock_create_member,
        mock_assign_payment_rhythm,
        mock_create_subscriptions,
        mock_legal_status_is_cooperative,
        mock_legal_status_is_association,
        mock_create_solidarity_contribution,
        mock_create_questionnaire_responses,
        mock_send_product_order_confirmation,
    ):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() + datetime.timedelta(days=30)
        )
        contract_start_date = period.start_date + datetime.timedelta(days=14)
        bidding_round = BiddingRoundFactory.create(
            growing_period=period,
            status=BIDDING_ROUND_STATUS_CLOSED,
            contracts_created_at=get_now(cache={}),
        )
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        product = ProductFactory.create(type=round_product_type.product_type)
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type, product=product
        )
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            product=product,
            quantity=1,
            amount_1=Decimal("80.00"),
        )
        member = MemberFactory.create()
        subscription = SubscriptionFactory.create(
            member=member,
            product=product,
            period=period,
            quantity=1,
            start_date=contract_start_date,
            end_date=period.end_date,
        )

        mock_create_member.return_value = member
        mock_create_subscriptions.return_value = [subscription]

        BestellWizardOrderFulfiller.create_member_and_fulfill_order(
            validated_serializer_data={
                "shopping_cart_order": {},
                "pickup_location_ids": [],
                "student_status_enabled": False,
                "personal_data": {},
                "payment_rhythm": "monthly",
                "number_of_coop_shares": 0,
                "pay_coop_shares_in_instalments": False,
                "association_membership_type_id": None,
                "solidarity_contribution": Decimal("0"),
                "distribution_channels": [],
            },
            delivery_address_input=None,
            contract_start_date=contract_start_date,
            request=SimpleNamespace(user=SimpleNamespace(is_authenticated=False)),
            cache={},
        )

        contribution = SolidarityContribution.objects.get(
            member=member, start_date=contract_start_date
        )
        self.assertEqual(Decimal("30.00"), contribution.amount)
        self.assertEqual(
            contribution,
            mock_send_product_order_confirmation.call_args.kwargs[
                "solidarity_contribution"
            ],
        )
