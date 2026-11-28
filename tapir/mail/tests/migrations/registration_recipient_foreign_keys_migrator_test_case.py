import datetime

from django.db.models import Model
from django_test_migrations.contrib.unittest_case import MigratorTestCase

MIGRATIONS_BEFORE = [
    ("tapir_mail", "0052_stable_trigger_ids"),
    ("wirgarten", "0154_member_extra_email_receives_direct_mails"),
]
MIGRATIONS_TESTED = [("tapir_mail", "0053_registration_recipient_foreign_keys")]


class RegistrationRecipientForeignKeysMigratorTestCase(MigratorTestCase):
    migrate_from = MIGRATIONS_BEFORE
    migrate_to = MIGRATIONS_TESTED

    def _create_member(self, username: str) -> Model:
        return self.old_state.apps.get_model("wirgarten", "Member").objects.create(
            username=username, email=f"{username}@example.com"
        )

    def _create_category(self, name: str) -> Model:
        static_segment = self.old_state.apps.get_model(
            "tapir_mail", "StaticSegment"
        ).objects.create(name=f"Mail-Kategorie:{name}")
        return self.old_state.apps.get_model(
            "tapir_mail", "MailCategory"
        ).objects.create(
            name=name,
            mode="optional_default_off",
            available_for_external_recipients=False,
            static_segment=static_segment,
            dynamic_segment_name="segment",
        )

    def _get_registration_model(self) -> type[Model]:
        return self.new_state.apps.get_model(
            "tapir_mail", "InternalRecipientCategoryRegistration"
        )

    @staticmethod
    def _build_datetime(day: int) -> datetime.datetime:
        return datetime.datetime(year=2025, month=1, day=day, tzinfo=datetime.UTC)
