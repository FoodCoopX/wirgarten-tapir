import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils.translation import gettext

from tapir.bidding_round.config import CLOSED, SOLIDARITY
from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.services.bidding_round_view_service import (
    BiddingRoundViewService,
)
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
)
from tapir.bidding_round.tests.helpers import create_round_product_with_product
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import GrowingPeriod
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, TapirUnitTest
from tapir.wirgarten.utils import get_now


class TestBiddingRoundViewService(TapirUnitTest):
    def test_getDisplayName_returnsTranslatedTerm(self):
        self.assertEqual(
            gettext("Bidding round"),
            BiddingRoundViewService.get_display_name(cache={}),
        )

    def test_getRoundsDisplayName_returnsTranslatedTerm(self):
        self.assertEqual(
            gettext("Bidding rounds"),
            BiddingRoundViewService.get_rounds_display_name(cache={}),
        )

    def test_filterAndSortMembers_autoRenewedFilter_keepsOnlyAutoRenewed(self):
        members = [
            {"member_name": "Bid", "has_bid": True, "is_auto_renewed": False},
            {"member_name": "Auto", "has_bid": False, "is_auto_renewed": True},
            {"member_name": "None", "has_bid": False, "is_auto_renewed": False},
        ]

        result = BiddingRoundViewService.filter_and_sort_members(
            members, filter_="auto_renewed", sort="name"
        )

        self.assertEqual(["Auto"], [member["member_name"] for member in result])


class TestSerializeContracts(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)

    def _prepare_round(self, reference_value=Decimal("80.00")):
        round_ = BiddingRoundFactory.create(status=CLOSED)
        round_.average_bid_locked_at = get_now()
        round_.locked_traffic_light_position = Decimal("50")
        round_.locked_surcharge_percent = Decimal("0")
        round_.save()
        GrowingPeriodFactory.create(
            start_date=round_.growing_period.start_date - relativedelta(years=1),
            end_date=round_.growing_period.start_date - datetime.timedelta(days=1),
        )
        round_product, product = create_round_product_with_product(
            round_, reference_value=reference_value, capacity=10
        )
        ProductPriceFactory.create(
            product=product,
            price=Decimal("77.00"),
            size=1,
            valid_from=round_.growing_period.start_date - relativedelta(years=1),
        )
        return round_, round_product, product

    def test_serializeContracts_bidder_returnsItemsAndAmounts(self):
        round_, round_product, product = self._prepare_round()
        member = MemberFactory.create()
        bid = BidFactory.create(round=round_, member=member, admin_confirmed=get_now())
        BidItemFactory.create(
            bid=bid,
            round_product=round_product,
            product=product,
            quantity=1,
            amount_1=Decimal("85.90"),
            amount_2=None,
            amount_3=None,
        )
        subscription = SubscriptionFactory.create(
            member=member,
            period=round_.growing_period,
            product=product,
            quantity=1,
        )
        BiddingRoundCreatedSubscription.objects.create(
            round=round_, subscription=subscription, is_bidder_contract=True
        )

        result = BiddingRoundViewService.serialize_contracts(round_, cache={})

        self.assertEqual(1, len(result))
        row = result[0]
        self.assertEqual("bid", row["type"])
        self.assertEqual(member.id, row["member_id"])
        self.assertEqual(1, len(row["items"]))
        self.assertEqual(product.name, row["items"][0]["product_name"])
        self.assertEqual(1, row["items"][0]["quantity"])
        self.assertEqual(Decimal("77.00"), row["standard_amount_per_month"])
        self.assertEqual(Decimal("85.90"), row["amount_per_month"])
        self.assertEqual(Decimal("8.90"), row["contribution_amount_per_month"])
        self.assertEqual(Decimal("1030.80"), row["amount_per_year"])

    def test_serializeContracts_materialisedAutoRenewed_returnsRow(self):
        round_, _, product = self._prepare_round()
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=round_.growing_period,
            product=product,
            quantity=1,
        )

        result = BiddingRoundViewService.serialize_contracts(round_, cache={})

        self.assertEqual(1, len(result))
        row = result[0]
        self.assertEqual("auto_renewed", row["type"])
        self.assertEqual(member.id, row["member_id"])
        self.assertEqual(1, len(row["items"]))
        self.assertEqual(Decimal("77.00"), row["standard_amount_per_month"])
        self.assertEqual(Decimal("80.00"), row["amount_per_month"])
        self.assertEqual(Decimal("3.00"), row["contribution_amount_per_month"])
        self.assertFalse(row["is_created"])

    def test_serializeContracts_autoRenewedWithoutMaterialisedSubscription_returnsNoRow(
        self,
    ):
        round_, _, product = self._prepare_round()
        previous_period = GrowingPeriod.objects.get(
            end_date=round_.growing_period.start_date - datetime.timedelta(days=1)
        )
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=previous_period,
            product=product,
            quantity=1,
            start_date=previous_period.start_date,
            end_date=previous_period.end_date,
        )

        result = BiddingRoundViewService.serialize_contracts(round_, cache={})

        self.assertEqual(0, len(result))
