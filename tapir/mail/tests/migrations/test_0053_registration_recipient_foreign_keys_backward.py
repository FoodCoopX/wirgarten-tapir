from tapir.mail.tests.migrations.registration_recipient_foreign_keys_migrator_test_case import (
    MIGRATIONS_BEFORE,
    MIGRATIONS_TESTED,
    RegistrationRecipientForeignKeysMigratorTestCase,
)


class TestRegistrationRecipientForeignKeysBackward(
    RegistrationRecipientForeignKeysMigratorTestCase
):
    migrate_from = MIGRATIONS_TESTED
    migrate_to = MIGRATIONS_BEFORE

    def prepare(self):
        self.member = self._create_member(username="member")
        self.extra_email = self.old_state.apps.get_model(
            "wirgarten", "MemberExtraEmail"
        ).objects.create(member=self.member, email="extra@example.com")
        mail_category = self._create_category(name="category")
        registration_model = self.old_state.apps.get_model(
            "tapir_mail", "InternalRecipientCategoryRegistration"
        )
        self.member_registration = registration_model.objects.create(
            member=self.member, mail_category=mail_category, is_registered=True
        )
        self.extra_registration = registration_model.objects.create(
            member_extra_email=self.extra_email,
            mail_category=mail_category,
            is_registered=False,
        )

    def test_backward(self):
        registrations = self._get_registration_model().objects
        self.assertEqual(
            self.member.id,
            registrations.get(id=self.member_registration.id).internal_recipient_id,
        )
        self.assertEqual(
            self.extra_email.id,
            registrations.get(id=self.extra_registration.id).internal_recipient_id,
        )
