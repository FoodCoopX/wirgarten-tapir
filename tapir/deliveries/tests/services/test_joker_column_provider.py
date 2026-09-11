import datetime

from tapir.deliveries.services.joker_column_provider import JokerColumnProvider
from tapir.deliveries.services.joker_segment_provider import JokerSegmentProvider
from tapir.deliveries.tests.factories import JokerFactory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberPickupLocationFactory,
    GrowingPeriodFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestJokerColumnProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getValueMemberNumber_default_returnsMemberNumber(self):
        joker = JokerFactory.create(member__member_no="12")
        self._set_parameter(
            key=ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, value=False
        )

        result = JokerColumnProvider.get_value_member_number(
            joker=joker, reference_datetime=get_now(), cache={}
        )

        self.assertEqual("12", result)

    def test_getValueMemberLastName_default_returnsMemberLastName(self):
        joker = JokerFactory.create(member__last_name="Foo")

        result = JokerColumnProvider.get_value_member_last_name(joker, None, None)

        self.assertEqual("Foo", result)

    def test_getValueMemberFirstName_default_returnsMemberFirstName(self):
        joker = JokerFactory.create(member__first_name="Bar")

        result = JokerColumnProvider.get_value_member_first_name(joker, None, None)

        self.assertEqual("Bar", result)

    def test_getValuePickupLocationName_default_returnsCorrectName(self):
        joker = JokerFactory.create(date=datetime.date(year=2020, month=6, day=1))
        GrowingPeriodFactory.create(start_date=datetime.date(year=2020, month=1, day=1))
        MemberPickupLocationFactory.create(
            member=joker.member,
            pickup_location__name="pl_1",
            valid_from=datetime.date(year=2020, month=1, day=1),
        )
        MemberPickupLocationFactory.create(
            member=joker.member,
            pickup_location__name="pl_2",
            valid_from=datetime.date(year=2020, month=5, day=20),
        )
        MemberPickupLocationFactory.create(
            member=joker.member,
            pickup_location__name="pl_3",
            valid_from=datetime.date(year=2020, month=7, day=1),
        )

        joker = JokerSegmentProvider.get_queryset_all_joker_this_growing_period(
            reference_datetime=datetime.datetime(
                year=2020, month=8, day=1, tzinfo=datetime.timezone.utc
            )
        ).get()

        result = JokerColumnProvider.get_value_pickup_location_name(joker, None, None)

        self.assertEqual("pl_2", result)

    def test_getValueCalendarWeek_default_returnsCorrectWeek(self):
        JokerFactory.create(date=datetime.date(year=2020, month=6, day=1))
        GrowingPeriodFactory.create(start_date=datetime.date(year=2020, month=1, day=1))

        joker = JokerSegmentProvider.get_queryset_all_joker_this_growing_period(
            reference_datetime=datetime.datetime(
                year=2020, month=8, day=1, tzinfo=datetime.timezone.utc
            )
        ).get()

        result = JokerColumnProvider.get_value_calendar_week(joker, None, None)

        self.assertEqual("23", result)

    def test_getValueProductTypes_default_returnsCorrectNames(self):
        joker = JokerFactory.create(date=datetime.date(year=2020, month=6, day=1))
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )
        SubscriptionFactory.create(
            member=joker.member,
            period=growing_period,
            end_date=datetime.date(year=2020, month=3, day=15),
            product__type__name="pt_1",
        )
        SubscriptionFactory.create(
            member=joker.member,
            period=growing_period,
            end_date=datetime.date(year=2020, month=8, day=21),
            product__type__name="pt_2",
        )
        SubscriptionFactory.create(
            member=joker.member, period=growing_period, product__type__name="pt_3"
        )

        result = JokerColumnProvider.get_value_product_types(
            joker,
            datetime.datetime(year=2020, month=9, day=1, tzinfo=datetime.timezone.utc),
            {},
        )

        self.assertEqual("pt_2,pt_3", result)

    def test_getValueProducts_default_returnsCorrectNames(self):
        joker = JokerFactory.create(date=datetime.date(year=2020, month=6, day=1))
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )
        SubscriptionFactory.create(
            member=joker.member,
            period=growing_period,
            end_date=datetime.date(year=2020, month=3, day=15),
            product__name="p_1",
        )
        SubscriptionFactory.create(
            member=joker.member,
            period=growing_period,
            end_date=datetime.date(year=2020, month=8, day=21),
            product__name="p_2",
        )
        SubscriptionFactory.create(
            member=joker.member, period=growing_period, product__name="p_3"
        )

        result = JokerColumnProvider.get_value_products(
            joker,
            datetime.datetime(year=2020, month=9, day=1, tzinfo=datetime.timezone.utc),
            {},
        )

        self.assertEqual("p_2,p_3", result)
