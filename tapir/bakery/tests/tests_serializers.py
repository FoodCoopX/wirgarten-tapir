from django.db import connection
from django.test.utils import CaptureQueriesContext

from tapir.bakery.models import BreadDelivery
from tapir.bakery.serializers import BreadDeliverySerializer
from tapir.bakery.tests.factories import (
    BreadCapacityPickupLocationFactory,
    BreadDeliveryFactory,
    BreadFactory,
    BreadSubscriptionFactory,
)
from tapir.bakery.tests.tests_viewsets import (
    DAY,
    WEEK,
    YEAR,
    create_pickup_location_with_delivery_day,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBreadDeliverySerializerDeliveryDay(TapirIntegrationTest):
    """
    delivery_day is derived from the pickup location's opening times, so it is
    a method field backed by a cached accessor rather than a source= path into
    a model property that queried once per row.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _create_deliveries(self, count, day=DAY):
        pickup_location = create_pickup_location_with_delivery_day(day)
        subscription = BreadSubscriptionFactory.create()
        for slot_number in range(1, count + 1):
            BreadDeliveryFactory.create(
                subscription=subscription,
                year=YEAR,
                delivery_week=WEEK,
                slot_number=slot_number,
                pickup_location=pickup_location,
                bread=None,
            )
        return list(
            BreadDelivery.objects.select_related("bread", "subscription__member").all()
        )

    def test_deliveryDay_comesFromThePickupLocationOpeningTimes(self):
        deliveries = self._create_deliveries(1)

        data = BreadDeliverySerializer(deliveries, many=True).data

        self.assertEqual([row["delivery_day"] for row in data], [DAY])

    def test_deliveryDay_pickupLocationWithoutOpeningTimes_isNull(self):
        BreadDeliveryFactory.create(
            subscription=BreadSubscriptionFactory.create(),
            year=YEAR,
            delivery_week=WEEK,
            slot_number=1,
            bread=None,
        )
        deliveries = list(
            BreadDelivery.objects.select_related("bread", "subscription__member").all()
        )

        data = BreadDeliverySerializer(deliveries, many=True).data

        self.assertIsNone(data[0]["delivery_day"])

    def test_derivedFields_costDoesNotGrowWithTheNumberOfRows(self):
        # The point of the derivation service: the pickup-location history, the
        # jokers, the weekdays and the locations are each loaded once for the
        # whole render rather than once per row.
        five = self._create_deliveries(5)
        with CaptureQueriesContext(connection) as for_five:
            data = BreadDeliverySerializer(five, many=True).data

        BreadDelivery.objects.all().delete()
        one = self._create_deliveries(1)
        with CaptureQueriesContext(connection) as for_one:
            BreadDeliverySerializer(one, many=True).data

        self.assertEqual(len(for_five), len(for_one))
        self.assertEqual([row["delivery_day"] for row in data], [DAY] * 5)


class TestBreadDeliverySerializerBreadValidation(TapirIntegrationTest):
    """
    A bread is chosen against the capacity its station has for that week, so
    the serializer rejects one the member's station does not bake.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _delivery(self, pickup_location):
        return BreadDeliveryFactory.create(
            subscription=BreadSubscriptionFactory.create(),
            year=YEAR,
            delivery_week=WEEK,
            slot_number=1,
            pickup_location=pickup_location,
            bread=None,
        )

    def test_validate_breadAvailableAtTheStation_isAccepted(self):
        pickup_location = create_pickup_location_with_delivery_day(DAY)
        delivery = self._delivery(pickup_location)
        bread = BreadFactory.create(name="Roggenbrot")
        BreadCapacityPickupLocationFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pickup_location,
            bread=bread,
            capacity=5,
        )

        serializer = BreadDeliverySerializer(
            delivery, data={"bread": str(bread.id)}, partial=True
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_breadNotBakedAtTheStation_isRejected(self):
        delivery = self._delivery(create_pickup_location_with_delivery_day(DAY))
        bread = BreadFactory.create(name="Roggenbrot")

        serializer = BreadDeliverySerializer(
            delivery, data={"bread": str(bread.id)}, partial=True
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("bread", serializer.errors)

    def test_validate_clearingTheChoice_isAccepted(self):
        delivery = self._delivery(create_pickup_location_with_delivery_day(DAY))

        serializer = BreadDeliverySerializer(
            delivery, data={"bread": None}, partial=True
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_memberWithoutAStation_isAccepted(self):
        # Nothing to check the bread against, so the choice is not blocked by
        # missing setup.
        delivery = BreadDeliveryFactory.create(
            subscription=BreadSubscriptionFactory.create(),
            year=YEAR,
            delivery_week=WEEK,
            slot_number=1,
            bread=None,
        )
        bread = BreadFactory.create(name="Roggenbrot")

        serializer = BreadDeliverySerializer(
            delivery, data={"bread": str(bread.id)}, partial=True
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
