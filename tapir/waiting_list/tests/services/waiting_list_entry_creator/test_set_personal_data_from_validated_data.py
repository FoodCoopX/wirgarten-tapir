from tapir.waiting_list.services.waiting_list_entry_creator import (
    WaitingListEntryCreator,
)
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestSetPersonalDataFromValidatedData(TapirUnitTest):
    def test_setPersonalDataFromValidatedData_mixedCaseAddress_setsTheNormalisedAddress(
        self,
    ):
        entry = WaitingListEntryFactory.build()

        WaitingListEntryCreator.set_personal_data_from_validated_data(
            waiting_list_entry=entry,
            validated_data={
                "first_name": "John",
                "last_name": "Doe",
                "email": " John@Example.com",
                "phone_number": "",
                "street": "",
                "street_2": "",
                "postcode": "",
                "city": "",
            },
        )

        self.assertEqual("john@example.com", entry.email)
        self.assertEqual("John", entry.first_name)
