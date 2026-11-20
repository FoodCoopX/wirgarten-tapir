import datetime
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.tests.factories import (
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
    BiddingRoundProductTypeFactory,
)
from tapir.wirgarten.models import ProductPrice
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestStandardPriceView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)

    def _login_as_admin(self):
        admin = MemberFactory.create(is_superuser=True, is_staff=True)
        self.client.force_login(admin)

    def _create_round(self, locked=True, ended=False):
        if ended:
            start_date = get_now(cache={}).date() - datetime.timedelta(days=400)
            end_date = get_now(cache={}).date() - datetime.timedelta(days=10)
        else:
            start_date = get_now(cache={}).date() + datetime.timedelta(days=30)
            end_date = start_date + datetime.timedelta(days=364)
        period = GrowingPeriodFactory.create(start_date=start_date, end_date=end_date)
        bidding_round = BiddingRoundFactory.create(
            growing_period=period,
            average_bid_locked_at=get_now(cache={}) if locked else None,
            locked_bidder_average_per_share_per_month=(
                Decimal("85.00") if locked else None
            ),
        )
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=product,
            size=Decimal("1.7"),
        )
        ProductPriceFactory.create(
            product=product,
            price=Decimal("70.00"),
            size=Decimal("1.0000"),
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        return bidding_round, product, period

    def test_post_loggedInAsAdmin_setsStandardPricesToLockedAverageTimesProductSize(
        self,
    ):
        self._login_as_admin()
        bidding_round, product, period = self._create_round()

        response = self.client.post(
            reverse("bidding_rounds:align_standard_prices", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(1, len(response.data["results"]))
        self.assertEqual("144.50", response.data["results"][0]["price"])
        price = ProductPrice.objects.get(product=product, valid_from=period.start_date)
        self.assertEqual(Decimal("144.50"), price.price)

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())
        bidding_round, _product, _period = self._create_round()

        response = self.client.post(
            reverse("bidding_rounds:align_standard_prices", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_averageBidNotLocked_returns400(self):
        self._login_as_admin()
        bidding_round, _product, _period = self._create_round(locked=False)

        response = self.client.post(
            reverse("bidding_rounds:align_standard_prices", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_post_endedContractPeriod_returns400(self):
        self._login_as_admin()
        bidding_round, _product, _period = self._create_round(ended=True)

        response = self.client.post(
            reverse("bidding_rounds:align_standard_prices", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
