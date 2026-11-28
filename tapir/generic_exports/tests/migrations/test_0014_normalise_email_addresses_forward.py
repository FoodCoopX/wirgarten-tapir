import datetime

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestNormaliseEmailAddressesForward(MigratorTestCase):
    migrate_from = [("generic_exports", "0013_alter_automated_export_cycle_choices")]
    migrate_to = [("generic_exports", "0014_normalise_email_addresses")]

    def prepare(self):
        self.old_state.apps.get_model("generic_exports", "CsvExport").objects.create(
            export_segment_id="segment",
            name="export",
            separator=",",
            file_name="export",
            email_recipients=["First@Example.com", " second@example.com"],
            automated_export_cycle="weekly",
            automated_export_day=1,
            automated_export_hour=datetime.time(hour=1),
        )

    def test_forward(self):
        self.assertEqual(
            ["first@example.com", "second@example.com"],
            self.new_state.apps.get_model("generic_exports", "CsvExport")
            .objects.get()
            .email_recipients,
        )
