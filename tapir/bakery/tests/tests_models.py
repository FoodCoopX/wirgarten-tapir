import datetime
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from tapir.bakery.models import (
    BreadContent,
    BreadDelivery,
    StoveSession,
)
from tapir.bakery.tests.factories import (
    BreadCapacityPickupLocationFactory,
    BreadFactory,
    IngredientFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak

YEAR = 2026
WEEK = 11


class TestBreadContentConstraints(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_unique_together_bread_ingredient(self):
        bread = BreadFactory.create()
        ingredient = IngredientFactory.create()
        BreadContent.objects.create(bread=bread, ingredient=ingredient, amount=100)

        with self.assertRaises(IntegrityError):
            BreadContent.objects.create(bread=bread, ingredient=ingredient, amount=200)


class TestStoveSessionConstraints(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_unique_together_session_layer(self):
        bread = BreadFactory.create()
        StoveSession.objects.create(
            year=YEAR,
            delivery_week=WEEK,
            delivery_day=3,
            session_number=1,
            layer_number=1,
            bread=bread,
            quantity=10,
        )

        with self.assertRaises(IntegrityError):
            StoveSession.objects.create(
                year=YEAR,
                delivery_week=WEEK,
                delivery_day=3,
                session_number=1,
                layer_number=1,
                bread=bread,
                quantity=5,
            )


class TestSignals(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch("tapir.bakery.services.breaddelivery_service.ensure_bread_deliveries_for_member")
    def test_subscription_save_triggers_bread_delivery_creation(self, mock_ensure):
        member = MemberFactory.create()
        sub = SubscriptionFactory.create(member=member)
        sub.save()

        if sub.product.type.delivery_cycle == "weekly":
            mock_ensure.assert_called_with(member)

    @patch("tapir.bakery.services.breaddelivery_service.ensure_bread_deliveries_for_member")
    def test_pickup_location_change_triggers_bread_delivery_update(self, mock_ensure):
        from tapir.wirgarten.models import MemberPickupLocation

        member = MemberFactory.create()
        pl = PickupLocationFactory.create()
        MemberPickupLocation.objects.create(
            member=member,
            pickup_location=pl,
            valid_from=datetime.date.today(),
        )

        mock_ensure.assert_called_with(member)


class TestBreadDeliveryValidation(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        set_bypass_keycloak()
        self.pl = PickupLocationFactory.create()
        self.bread = BreadFactory.create(name="Roggenbrot")
        self.member = MemberFactory.create()
        self.subscription = SubscriptionFactory.create(member=self.member)

    def test_save_breadAvailableAtLocation_succeeds(self):
        BreadCapacityPickupLocationFactory.create(
            year=2026,
            delivery_week=11,
            pickup_location=self.pl,
            bread=self.bread,
            capacity=5,
        )

        delivery = BreadDelivery(
            year=2026,
            delivery_week=11,
            subscription=self.subscription,
            pickup_location=self.pl,
            bread=self.bread,
        )
        delivery.save()  # Should not raise

    def test_save_breadNotAvailableAtLocation_raisesValidationError(self):
        # No BreadsPerPickupLocationPerWeek entry exists
        delivery = BreadDelivery(
            year=2026,
            delivery_week=11,
            subscription=self.subscription,
            pickup_location=self.pl,
            bread=self.bread,
        )

        with self.assertRaises(ValidationError) as ctx:
            delivery.save()

        self.assertIn("bread", ctx.exception.message_dict)

    def test_save_noBreadAssigned_succeeds(self):
        delivery = BreadDelivery(
            year=2026,
            delivery_week=11,
            subscription=self.subscription,
            pickup_location=self.pl,
            bread=None,
        )
        delivery.save()  # Should not raise — no bread to validate
