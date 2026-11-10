from tapir.payments.tests.factories import MemberCreditFactory
from tapir.pickup_locations.services.pickup_location_deletion_validator import (
    PickupLocationDeletionValidator,
)
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.models import WaitingListPickupLocationWish
from tapir.wirgarten.tests.factories import (
    MemberPickupLocationFactory,
    PaymentFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationDeletionValidator(TapirIntegrationTest):
    def setUp(self):
        super().setUp()
        self.pickup_location = PickupLocationFactory.create()

    def test_validate_unusedLocation_returnsNone(self):
        PickupLocationFactory.create()

        self.assertIsNone(
            PickupLocationDeletionValidator.validate(
                pickup_location=self.pickup_location
            )
        )

    def test_validate_locationLinkedToMember_returnsMessage(self):
        MemberPickupLocationFactory.create(pickup_location=self.pickup_location)

        self.assertEqual(
            "Der Abholort kann nicht gelöscht werden, er wird noch verwendet von: Mitgliedern.",
            PickupLocationDeletionValidator.validate(
                pickup_location=self.pickup_location
            ),
        )

    def test_validate_locationUsedInWaitingListWish_returnsMessage(self):
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=WaitingListEntryFactory.create(),
            pickup_location=self.pickup_location,
            priority=1,
        )

        self.assertEqual(
            "Der Abholort kann nicht gelöscht werden, er wird noch verwendet von: Wartelisten-Wünschen.",
            PickupLocationDeletionValidator.validate(
                pickup_location=self.pickup_location
            ),
        )

    def test_validate_severalUsages_listsAllOfThem(self):
        MemberCreditFactory.create(pickup_location=self.pickup_location)
        PaymentFactory.create(pickup_location=self.pickup_location)

        self.assertEqual(
            "Der Abholort kann nicht gelöscht werden, er wird noch verwendet von: Gutschriften, Zahlungen.",
            PickupLocationDeletionValidator.validate(
                pickup_location=self.pickup_location
            ),
        )
