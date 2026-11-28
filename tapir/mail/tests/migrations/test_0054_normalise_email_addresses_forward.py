from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestNormaliseEmailAddressesForward(MigratorTestCase):
    migrate_from = [("tapir_mail", "0053_registration_recipient_foreign_keys")]
    migrate_to = [("tapir_mail", "0054_normalise_email_addresses")]

    def prepare(self):
        self.old_state.apps.get_model("tapir_mail", "ExternalRecipient").objects.create(
            email=" External@Example.com", first_name="Test"
        )
        segment = self.old_state.apps.get_model(
            "tapir_mail", "StaticSegment"
        ).objects.create(name="segment")
        self.old_state.apps.get_model(
            "tapir_mail", "StaticSegmentRecipient"
        ).objects.create(segment=segment, email="Static@Example.com")

    def test_forward(self):
        for model_name, expected in [
            ("ExternalRecipient", ["external@example.com"]),
            ("StaticSegmentRecipient", ["static@example.com"]),
        ]:
            self.assertEqual(
                expected,
                list(
                    self.new_state.apps.get_model(
                        "tapir_mail", model_name
                    ).objects.values_list("email", flat=True)
                ),
            )
