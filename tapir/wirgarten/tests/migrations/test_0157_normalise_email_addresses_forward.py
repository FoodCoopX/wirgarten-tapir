from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestNormaliseEmailAddressesForward(MigratorTestCase):
    migrate_from = [
        ("wirgarten", "0156_update_extra_mail_addresses_explanation_text"),
    ]
    migrate_to = [("wirgarten", "0157_normalise_email_addresses")]

    def prepare(self):
        member = self.old_state.apps.get_model("wirgarten", "Member").objects.create(
            username="test_member", email="member@example.com"
        )
        self.old_state.apps.get_model("wirgarten", "MemberExtraEmail").objects.create(
            member=member, email=" Extra@Example.com"
        )
        log_class_type, _ = self.old_state.apps.get_model(
            "contenttypes", "ContentType"
        ).objects.get_or_create(
            app_label="wirgarten", model="memberextraemaildeletedlogentry"
        )
        self.old_state.apps.get_model(
            "wirgarten", "MemberExtraEmailDeletedLogEntry"
        ).objects.create(
            user=member, email="Deleted@Example.com", log_class_type=log_class_type
        )

    def test_forward(self):
        for model_name, expected in [
            ("MemberExtraEmail", ["extra@example.com"]),
            ("MemberExtraEmailDeletedLogEntry", ["deleted@example.com"]),
        ]:
            self.assertEqual(
                expected,
                list(
                    self.new_state.apps.get_model(
                        "wirgarten", model_name
                    ).objects.values_list("email", flat=True)
                ),
            )
