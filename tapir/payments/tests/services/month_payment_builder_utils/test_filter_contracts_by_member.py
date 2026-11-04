from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestFilterContractsByMember(TapirUnitTest):
    def test_filterContractsByMember_memberIdIsNone_returnsAllContracts(self):
        contracts = [
            SubscriptionFactory.build(member__pk="member_1"),
            SubscriptionFactory.build(member__pk="member_2"),
        ]

        result = MonthPaymentBuilderUtils.filter_contracts_by_member(
            contracts=contracts, member_id=None
        )

        self.assertEqual(contracts, result)

    def test_filterContractsByMember_memberIdGiven_returnsOnlyContractsOfThatMember(
        self,
    ):
        contract_1 = SubscriptionFactory.build(member__pk="member_1")
        contract_2 = SubscriptionFactory.build(member__pk="member_2")
        contract_3 = SubscriptionFactory.build(member__pk="member_1")

        result = MonthPaymentBuilderUtils.filter_contracts_by_member(
            contracts=[contract_1, contract_2, contract_3], member_id="member_1"
        )

        self.assertEqual([contract_1, contract_3], result)
