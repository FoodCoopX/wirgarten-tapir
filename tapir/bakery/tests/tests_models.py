import datetime
from unittest.mock import patch

from django.db import IntegrityError

from tapir.bakery.models import (
    BreadContent,
    BreadDelivery,
    StoveSession,
)
from tapir.bakery.services.breaddelivery_service import BreadDeliveryService
from tapir.bakery.tests.factories import BreadFactory, IngredientFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

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

    @patch(
        "tapir.bakery.services.breaddelivery_service.BreadDeliveryService."
        "ensure_bread_deliveries_for_member"
    )
    def test_subscriptionSaved_breadProductType_triggersSync(self, mock_ensure):
        member = MemberFactory.create()
        product = ProductFactory.create(
            type=ProductTypeFactory.create(delivery_cycle="weekly", is_bread=True)
        )
        sub = SubscriptionFactory.create(member=member, product=product)
        # Creating the subscription already fired the receiver once
        mock_ensure.reset_mock()

        sub.save()

        mock_ensure.assert_called_once_with(member)

    @patch(
        "tapir.bakery.services.breaddelivery_service.BreadDeliveryService."
        "ensure_bread_deliveries_for_member"
    )
    def test_subscriptionSaved_weeklyButNotBread_doesNotTriggerSync(self, mock_ensure):
        # The base harvest share is weekly on every org, so the delivery cycle
        # alone must not be enough to accrue bread deliveries.
        member = MemberFactory.create()
        product = ProductFactory.create(
            type=ProductTypeFactory.create(delivery_cycle="weekly", is_bread=False)
        )
        sub = SubscriptionFactory.create(member=member, product=product)
        mock_ensure.reset_mock()

        sub.save()

        mock_ensure.assert_not_called()

    def test_ensureBreadDeliveries_bakeryDisabled_createsNothing(self):
        # BAKERY_A_ENABLED defaults to False, so an installation without the
        # bakery must never accrue bread deliveries.
        member = MemberFactory.create()
        product = ProductFactory.create(
            type=ProductTypeFactory.create(delivery_cycle="weekly", is_bread=True)
        )
        SubscriptionFactory.create(
            member=member,
            product=product,
            start_date=datetime.date(2026, 3, 2),
            end_date=datetime.date(2026, 3, 29),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertFalse(BreadDelivery.objects.exists())
