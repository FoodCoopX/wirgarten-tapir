import datetime

from django.urls import reverse

from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    MemberFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_normalMemberTriesToChangeDates_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        subscription = SubscriptionFactory.create(
            end_date=datetime.date(year=2025, month=1, day=2)
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date": subscription.start_date,
                "end_date": datetime.date(year=2025, month=10, day=12),
            },
        )

        self.assertStatusCode(response, 403)

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=1, day=2), subscription.end_date
        )

    def test_post_validationFails_dontChangeDatesAndReturnErrorMessage(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        subscription = SubscriptionFactory.create(
            end_date=datetime.date(year=2025, month=1, day=2)
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date": subscription.start_date,
                "end_date": datetime.date(year=2025, month=1, day=1),
            },
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            {
                "error": "Das End-Datum muss am gleichem Wochentag sein wie die Kommissioniervariable (Sonntag), du hast Mittwoch angegeben",
                "order_confirmed": False,
            },
            response.json(),
        )

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=1, day=2), subscription.end_date
        )

    def test_post_endDateNotChanged_dontDeleteFutureSubscription(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        subscription = SubscriptionFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
        )
        SubscriptionFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
            product=subscription.product,
            member=subscription.member,
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=datetime.date(year=2025, month=1, day=1),
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date": datetime.date(year=2025, month=2, day=1),
                "end_date": subscription.end_date,
            },
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            {
                "error": None,
                "order_confirmed": True,
            },
            response.json(),
        )

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=2, day=1), subscription.start_date
        )
        self.assertEqual(2, Subscription.objects.count())

    def test_post_endDateChanged_deleteFutureSubscription(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        subscription = SubscriptionFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
        )
        SubscriptionFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
            product=subscription.product,
            member=subscription.member,
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=datetime.date(year=2025, month=1, day=1),
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date": subscription.start_date,
                "end_date": datetime.date(year=2025, month=11, day=30),
            },
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            {
                "error": None,
                "order_confirmed": True,
            },
            response.json(),
        )

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=11, day=30), subscription.end_date
        )
        self.assertEqual(1, Subscription.objects.count())
