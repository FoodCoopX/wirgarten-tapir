from tapir.mail.tests.migrations.registration_recipient_foreign_keys_migrator_test_case import (
    RegistrationRecipientForeignKeysMigratorTestCase,
)


class TestRegistrationRecipientForeignKeysForward(
    RegistrationRecipientForeignKeysMigratorTestCase
):
    def prepare(self):
        self.member = self._create_member(username="member")
        self.mail_category = self._create_category(name="category")
        registration_model = self.old_state.apps.get_model(
            "tapir_mail", "InternalRecipientCategoryRegistration"
        )
        self.older_duplicate = registration_model.objects.create(
            internal_recipient_id=self.member.id,
            mail_category=self.mail_category,
            is_registered=False,
        )
        self.newer_duplicate = registration_model.objects.create(
            internal_recipient_id=self.member.id,
            mail_category=self.mail_category,
            is_registered=True,
        )
        registration_model.objects.filter(id=self.older_duplicate.id).update(
            created_at=self._build_datetime(day=1)
        )
        registration_model.objects.filter(id=self.newer_duplicate.id).update(
            created_at=self._build_datetime(day=2)
        )
        registration_model.objects.create(
            internal_recipient_id="unknownid0",
            mail_category=self.mail_category,
            is_registered=True,
        )

    def test_forward(self):
        registration = self._get_registration_model().objects.get()
        self.assertEqual(self.newer_duplicate.id, registration.id)
        self.assertEqual(self.member.id, registration.member_id)
        self.assertIsNone(registration.member_extra_email_id)
        self.assertTrue(registration.is_registered)
