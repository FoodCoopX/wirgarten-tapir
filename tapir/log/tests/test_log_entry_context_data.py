from django.test import SimpleTestCase

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.payments.models import MemberCreditCreatedLogEntry


class TestLogEntryContextData(SimpleTestCase):
    def test_updateModelLogEntry_nonDictValues_rendersEmptyChanges(self):
        entry = UpdateTapirUserLogEntry(old_values="broken", new_values="broken")

        context_data = entry.get_context_data()

        self.assertEqual([], context_data["changes"])

    def test_modelLogEntry_nonDictValues_rendersEmptyValues(self):
        entry = MemberCreditCreatedLogEntry(values="broken")

        context_data = entry.get_context_data()

        self.assertEqual([], list(context_data["values"]))
