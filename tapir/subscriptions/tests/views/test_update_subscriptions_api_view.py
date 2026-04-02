import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.subscription_update_view_change_applier import (
    SubscriptionUpdateViewChangeApplier,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import (
    Subscription,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    PickupLocationFactory,
    GrowingPeriodFactory,
    MemberFactory,
    ProductPriceFactory,
    ProductCapacityFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestUpdateSubscriptionsApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)

        cls.product_1 = ProductFactory.create(type__delivery_cycle=WEEKLY[0])
        ProductPriceFactory.create(product=cls.product_1)
        cls.product_2 = ProductFactory.create(type=cls.product_1.type)
        ProductPriceFactory.create(product=cls.product_2)

        cls.pickup_location = PickupLocationFactory.create()
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2030, month=1, day=1)
        )

        ProductCapacityFactory.create(
            period=cls.growing_period, product_type=cls.product_1.type, capacity=1000
        )
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=cls.product_1.type_id
        )

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2030, month=6, day=1)
        )

    def build_valid_post_data_for_member(self, member_id: str):
        return {
            "member_id": member_id,
            "product_type_id": self.product_1.type.id,
            "shopping_cart": {self.product_1.id: 3, self.product_2.id: 2},
            "sepa_allowed": True,
            "pickup_location_id": self.pickup_location.id,
            "growing_period_id": self.growing_period.id,
            "account_owner": "new account owner",
            "iban": "NL76RABO8675663943",
            "payment_rhythm": MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
        }

    def test_post_orderIsValid_allChangesApplied(self):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=self.growing_period,
            product=self.product_1,
            quantity=1,
        )
        self.client.force_login(member)
        data = self.build_valid_post_data_for_member(member.id)

        response_content = self.send_request_and_assert_response_200(data=data)

        self.assert_order_confirmed(response_content)

        subscriptions = list(Subscription.objects.order_by("quantity"))
        self.assertEqual(3, len(subscriptions))

        subscription_old, subscription_new_1, subscription_new_2 = subscriptions

        self.assertEqual(
            subscription_new_1.start_date - datetime.timedelta(days=1),
            subscription_old.end_date,
        )

        self.assertEqual(
            self.pickup_location.id,
            MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=subscription_new_1.start_date
            ),
        )

        for subscription in [subscription_new_1, subscription_new_2]:
            self.assertEqual(member, subscription.member)
            self.assertLess(self.now.date(), subscription.start_date)
            self.assertEqual(self.growing_period.end_date, subscription.end_date)

        self.assertEqual(2, subscription_new_1.quantity)
        self.assertEqual(self.product_2, subscription_new_1.product)
        self.assertEqual(3, subscription_new_2.quantity)
        self.assertEqual(self.product_1, subscription_new_2.product)

        self.assertEqual(2, SubscriptionChangeLogEntry.objects.count())
        log_entry_added = SubscriptionChangeLogEntry.objects.get(
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.ADDED
        )
        self.assertEqual(member.email, log_entry_added.actor.email)
        self.assertEqual(member.email, log_entry_added.user.email)
        self.assertEqual(
            SubscriptionChangeLogEntry.build_subscription_list_as_string(
                [subscription_new_1, subscription_new_2]
            ),
            log_entry_added.subscriptions,
        )

        log_entry_cancelled = SubscriptionChangeLogEntry.objects.get(
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED
        )
        self.assertEqual(member.email, log_entry_cancelled.actor.email)
        self.assertEqual(member.email, log_entry_cancelled.user.email)

        self.assertEqual(
            MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member, reference_date=subscription_new_1.start_date, cache={}
            ),
        )

        member.refresh_from_db()
        self.assertEqual(self.now, member.sepa_consent)
        self.assertEqual("new account owner", member.account_owner)
        self.assertEqual("NL76RABO8675663943", member.iban)

    @patch.object(SubscriptionUpdateViewChangeApplier, "apply_changes", autospec=True)
    def test_post_orderIsInvalid_noChangesApplied(self, mock_apply_changes: Mock):
        member = MemberFactory.create()
        self.client.force_login(member)
        data = self.build_valid_post_data_for_member(member.id)
        data["sepa_allowed"] = False

        response_content = self.send_request_and_assert_response_200(data=data)

        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Das SEPA-Mandat muss ermächtigt sein.", response_content["error"]
        )
        mock_apply_changes.assert_not_called()
        self.assertFalse(Subscription.objects.exists())

    def test_post_adminDoesChangesForAnotherMember_returns200(self):
        user = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create()
        self.client.force_login(user)
        data = self.build_valid_post_data_for_member(target.id)

        response_content = self.send_request_and_assert_response_200(data=data)

        self.assert_order_confirmed(response_content)

    def test_post_normalDoesChangesForThemselves_returns200(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        data = self.build_valid_post_data_for_member(member.id)

        response_content = self.send_request_and_assert_response_200(data=data)

        self.assert_order_confirmed(response_content)

    def test_post_normalMemberDoesChangesForAnotherMember_returns403(self):
        user = MemberFactory.create(is_superuser=False)
        target = MemberFactory.create()
        self.client.force_login(user)
        data = self.build_valid_post_data_for_member(target.id)

        self.send_request_and_assert_status_code(
            data=data, status_code=status.HTTP_403_FORBIDDEN
        )

        self.assertFalse(Subscription.objects.exists())

    def assert_order_confirmed(self, response_content: dict):
        self.assertTrue(
            response_content["order_confirmed"],
            f"Order should be confirmed, error: {response_content["error"]}",
        )
        self.assertIsNone(response_content["error"])

    def send_request_and_assert_response_200(self, data: dict):
        response = self.send_request_and_assert_status_code(
            data=data, status_code=status.HTTP_200_OK
        )
        return response.json()

    def send_request_and_assert_status_code(self, data: dict, status_code: int):
        response = self.client.post(
            reverse("subscriptions:update_subscription"),
            data=data,
            content_type="application/json",
        )

        self.assertStatusCode(response, status_code)

        return response
