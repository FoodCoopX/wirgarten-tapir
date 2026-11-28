import datetime

from django.db.models import Model
from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestBackfillMemberExtraEmailCategoryRegistrationsForward(MigratorTestCase):
    migrate_from = [
        ("wirgarten", "0154_member_extra_email_receives_direct_mails"),
        ("tapir_mail", "0053_registration_recipient_foreign_keys"),
    ]
    migrate_to = [
        ("wirgarten", "0155_backfill_member_extra_email_category_registrations")
    ]

    def prepare(self):
        member = self.old_state.apps.get_model("wirgarten", "Member").objects.create(
            username="test_member", email="member@example.com"
        )
        self.confirmed_extra = self._create_extra(
            member=member, email="confirmed@example.com", is_confirmed=True
        )
        self._create_extra(
            member=member, email="unconfirmed@example.com", is_confirmed=False
        )

        self.always_on = self._create_category(name="always_on", mode="always_on")
        self.default_on = self._create_category(
            name="default_on", mode="optional_default_on"
        )
        self.default_off = self._create_category(
            name="default_off", mode="optional_default_off"
        )
        self.default_on_member_unregistered = self._create_category(
            name="default_on_member_unregistered", mode="optional_default_on"
        )
        self.default_off_member_registered = self._create_category(
            name="default_off_member_registered", mode="optional_default_off"
        )
        self._create_category(
            name="no_dynamic_segment", mode="always_on", dynamic_segment_name=""
        )

        registration_model = self.old_state.apps.get_model(
            "tapir_mail", "InternalRecipientCategoryRegistration"
        )
        registration_model.objects.create(
            member=member,
            mail_category=self.default_on_member_unregistered,
            is_registered=False,
        )
        registration_model.objects.create(
            member=member,
            mail_category=self.default_off_member_registered,
            is_registered=True,
        )

    def test_forward(self):
        registrations = self.new_state.apps.get_model(
            "tapir_mail", "InternalRecipientCategoryRegistration"
        ).objects.all()
        extra_registrations = {
            (registration.mail_category_id, registration.is_registered)
            for registration in registrations.filter(
                member_extra_email_id=self.confirmed_extra.id
            )
        }

        self.assertEqual(
            {
                (self.always_on.id, True),
                (self.default_on.id, True),
                (self.default_off.id, False),
                (self.default_on_member_unregistered.id, False),
                (self.default_off_member_registered.id, True),
            },
            extra_registrations,
        )
        self.assertEqual(7, registrations.count())

    def _create_extra(self, member: Model, email: str, is_confirmed: bool):
        return self.old_state.apps.get_model(
            "wirgarten", "MemberExtraEmail"
        ).objects.create(
            member=member,
            email=email,
            confirmed_on=(
                datetime.datetime(year=2025, month=1, day=1, tzinfo=datetime.UTC)
                if is_confirmed
                else None
            ),
        )

    def _create_category(
        self, name: str, mode: str, dynamic_segment_name: str = "segment"
    ):
        static_segment = self.old_state.apps.get_model(
            "tapir_mail", "StaticSegment"
        ).objects.create(name=f"Mail-Kategorie:{name}")
        return self.old_state.apps.get_model(
            "tapir_mail", "MailCategory"
        ).objects.create(
            name=name,
            mode=mode,
            available_for_external_recipients=False,
            static_segment=static_segment,
            dynamic_segment_name=dynamic_segment_name,
        )
