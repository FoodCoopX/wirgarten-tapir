import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.urls import reverse

from tapir.bakery.models import BreadDelivery
from tapir.bakery.tests.factories import (
    BreadProductTypeFactory,
    enable_bakery,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak


@patch("tapir.wirgarten.views.member.details.actions.send_product_order_confirmation")
class TestRenewContractSameConditionsCreatesBreadDeliveries(TapirIntegrationTest):
    """
    Renewing on the same terms bulk-creates the next period's subscriptions,
    and bulk_create does not fire post_save - so the bakery receiver never sees
    them. The view has to trigger the sync itself, or the member starts the new
    growing period with no bread deliveries at all.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        set_bypass_keycloak()
        enable_bakery()

        today = datetime.date.today()
        self.current_period = GrowingPeriodFactory.create(
            start_date=today - relativedelta(months=6),
            end_date=today + relativedelta(months=6),
        )
        self.next_period = GrowingPeriodFactory.create(
            start_date=self.current_period.end_date + datetime.timedelta(days=1),
            end_date=self.current_period.end_date + relativedelta(years=1),
        )

        product_type = BreadProductTypeFactory.create()
        for period in (self.current_period, self.next_period):
            ProductCapacityFactory.create(period=period, product_type=product_type)

        # The renewal asks whether the product type still has capacity, which
        # prices every existing subscription - so the product needs a price
        # valid from before the current period starts.
        self.product = ProductFactory.create(type=product_type)
        ProductPriceFactory.create(
            product=self.product,
            valid_from=self.current_period.start_date,
            size=1,
        )

        self.member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=PickupLocationFactory.create(),
            valid_from=self.current_period.start_date,
        )
        self.subscription = SubscriptionFactory.create(
            member=self.member,
            product=self.product,
            period=self.current_period,
            quantity=1,
            start_date=self.current_period.start_date,
            end_date=self.current_period.end_date,
        )

    def _renew(self):
        self.client.force_login(self.member)
        return self.client.get(
            reverse(
                "wirgarten:member_renew_same_conditions",
                kwargs={"pk": self.member.id},
            )
        )

    def test_renew_createsTheNextPeriodsSubscription(self, _mail):
        self._renew()

        self.assertTrue(
            Subscription.objects.filter(
                member=self.member, period=self.next_period
            ).exists()
        )

    def test_renew_createsBreadDeliveriesForTheNextPeriod(self, _mail):
        self._renew()

        weeks_in_next_period = BreadDelivery.objects.filter(
            subscription__member=self.member,
            subscription__period=self.next_period,
        )
        self.assertTrue(
            weeks_in_next_period.exists(),
            "Renewing bulk-creates the subscriptions, so the bakery receiver "
            "never fires; the view has to trigger the sync itself.",
        )
