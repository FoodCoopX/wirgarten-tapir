import datetime
from unittest.mock import patch, Mock

from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import mock_timezone, TapirIntegrationTest


class TestGetDeliveriesServiceGetDeliveries(TapirIntegrationTest):
    def setUp(self):
        ParameterDefinitions().import_definitions()
        mock_timezone(self, factories.NOW)

    @patch.object(GetDeliveriesService, "build_delivery_object")
    def test_getDeliveries_default_buildsDeliveryForAllDatesBetweenFromAndTo(
        self, mock_build_delivery_object: Mock
    ):
        member = MemberFactory.create()
        mock_build_delivery_object.return_value = Mock()
        cache = {}
        deliveries = GetDeliveriesService.get_deliveries(
            member=member,
            date_from=datetime.date(year=2024, month=4, day=1),
            date_to=datetime.date(year=2024, month=4, day=30),
            cache=cache,
        )

        self.assertEqual(4, len(deliveries))
        self.assertEqual(4, mock_build_delivery_object.call_count)
        delivery_dates_in_april_2024 = [
            datetime.date(year=2024, month=4, day=day) for day in [3, 10, 17, 24]
        ]
        for index, date in enumerate(delivery_dates_in_april_2024):
            actual_call = mock_build_delivery_object.mock_calls[index]
            _, args, kwargs = actual_call
            self.assertEqual((), args)
            self.assertEqual(
                {"member": member, "delivery_date": date, "cache": cache}, kwargs
            )

    @patch.object(GetDeliveriesService, "build_delivery_object")
    def test_getDeliveries_noDeliveryOnSomeDays_returnedListContainsOnlyDeliveredDays(
        self, mock_build_delivery_object: Mock
    ):
        member = MemberFactory.create()
        mock_build_delivery_object.side_effect = lambda member, delivery_date, cache: (
            Mock() if delivery_date.day in [3, 17] else None
        )

        deliveries = GetDeliveriesService.get_deliveries(
            member=member,
            date_from=datetime.date(year=2024, month=4, day=1),
            date_to=datetime.date(year=2024, month=4, day=30),
            cache={},
        )

        self.assertEqual(2, len(deliveries))
