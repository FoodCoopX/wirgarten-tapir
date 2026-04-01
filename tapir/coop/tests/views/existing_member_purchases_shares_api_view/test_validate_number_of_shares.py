from rest_framework.exceptions import ValidationError

from tapir.configuration.models import TapirParameter
from tapir.coop.views import ExistingMemberPurchasesSharesApiView
from tapir.wirgarten.models import CoopShareTransaction, Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, CoopShareTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestValidateNumberOfShares(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_MIN_SHARES).update(value=5)

        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member,
            quantity=3,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        )
        CoopShareTransactionFactory.create(
            member=member,
            quantity=-1,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
        )

    def test_validateNumberOfShares_orderCoversRequiredNumber_doesNothing(self):
        ExistingMemberPurchasesSharesApiView.validate_number_of_shares(
            number_of_shares_to_add=3, member=Member.objects.get(), cache={}
        )

    def test_validateNumberOfShares_orderDoesntCoverRequiredNumber_raiseValidationError(
        self,
    ):
        with self.assertRaises(ValidationError):
            ExistingMemberPurchasesSharesApiView.validate_number_of_shares(
                number_of_shares_to_add=2, member=Member.objects.get(), cache={}
            )
