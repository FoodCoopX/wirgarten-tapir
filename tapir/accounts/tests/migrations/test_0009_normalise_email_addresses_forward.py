from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestNormaliseEmailAddressesForward(MigratorTestCase):
    migrate_from = [
        ("accounts", "0008_alter_tapiruser_birthdate_alter_tapiruser_city_and_more")
    ]
    migrate_to = [("accounts", "0009_normalise_email_addresses")]

    def prepare(self):
        user = self.old_state.apps.get_model("accounts", "TapirUser").objects.create(
            username="test_user", email=" Test@Example.com "
        )
        self.user_id = user.id
        self.old_state.apps.get_model("accounts", "EmailChangeRequest").objects.create(
            user=user, new_email="New@Example.com"
        )

    def test_forward(self):
        self.assertEqual(
            "test@example.com",
            self.new_state.apps.get_model("accounts", "TapirUser")
            .objects.get(id=self.user_id)
            .email,
        )
        self.assertEqual(
            ["new@example.com"],
            list(
                self.new_state.apps.get_model(
                    "accounts", "EmailChangeRequest"
                ).objects.values_list("new_email", flat=True)
            ),
        )
