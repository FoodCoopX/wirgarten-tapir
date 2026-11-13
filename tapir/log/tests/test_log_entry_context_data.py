"""Rendering a log entry must survive a non-mapping hstore value.

``old_values``/``new_values``/``values`` are ``HStoreField``s, so they usually hold a mapping. A row
written outside ``populate`` (an import or legacy data) can hold a bare scalar; before the guard
that made the member detail page fail with ``AttributeError: 'str' object has no attribute 'keys'``.
"""

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.payments.models import MemberCreditCreatedLogEntry
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestUpdateModelLogEntryContextData(TapirIntegrationTest):
    def test_getContextData_populatedValues_listsTheChangedKeys(self):
        entry = UpdateTapirUserLogEntry()
        entry.populate(
            old_frozen={"first_name": "Ada", "last_name": "Lovelace"},
            new_frozen={"first_name": "Grace", "last_name": "Lovelace"},
        )

        context = entry.get_context_data()

        self.assertEqual([("first_name", "Ada", "Grace")], context["changes"])

    def test_getContextData_oldValuesIsAString_showsNoChangesInsteadOfFailing(self):
        entry = UpdateTapirUserLogEntry(
            old_values="not a mapping", new_values="not a mapping"
        )

        context = entry.get_context_data()

        self.assertEqual([], context["changes"])

    def test_getContextData_newValuesIsAString_doesNotFail(self):
        entry = UpdateTapirUserLogEntry(
            old_values={"first_name": "Ada"}, new_values="not a mapping"
        )

        context = entry.get_context_data()

        self.assertEqual([("first_name", "Ada", None)], context["changes"])


class TestModelLogEntryContextData(TapirIntegrationTest):
    def test_getContextData_mappingValues_listsTheValues(self):
        entry = MemberCreditCreatedLogEntry(values={"amount": "10.00"})

        context = entry.get_context_data()

        self.assertEqual([("amount", "10.00")], list(context["values"]))

    def test_getContextData_valuesIsAString_showsNothingInsteadOfFailing(self):
        entry = MemberCreditCreatedLogEntry(values="not a mapping")

        context = entry.get_context_data()

        self.assertEqual([], list(context["values"]))
