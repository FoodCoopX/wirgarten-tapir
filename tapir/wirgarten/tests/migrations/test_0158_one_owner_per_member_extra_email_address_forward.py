import datetime

from django.db.models import Model
from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestOneOwnerPerMemberExtraEmailAddressForward(MigratorTestCase):
    migrate_from = [
        ("wirgarten", "0157_normalise_email_addresses"),
        ("accounts", "0009_normalise_email_addresses"),
        ("tapir_mail", "0054_normalise_email_addresses"),
    ]
    migrate_to = [("wirgarten", "0158_one_owner_per_member_extra_email_address")]

    def prepare(self):
        member_model = self.old_state.apps.get_model("wirgarten", "Member")
        member_a = member_model.objects.create(
            username="member_a", email="main_a@example.com"
        )
        member_b = member_model.objects.create(
            username="member_b", email="main_b@example.com"
        )
        member_c = member_model.objects.create(
            username="member_c", email="main_c@example.com"
        )

        self.oldest_shared = self._create_extra(
            member=member_b, email="shared@example.com", confirmed_day=1
        )
        self.newer_shared = self._create_extra(
            member=member_a, email="shared@example.com", confirmed_day=2
        )
        self.main_address_of_other = self._create_extra(
            member=member_a, email="main_b@example.com", confirmed_day=1
        )
        self.unique = self._create_extra(
            member=member_c, email="unique@example.com", confirmed_day=1
        )
        self.unconfirmed_shared = self._create_extra(
            member=member_c, email="shared@example.com", confirmed_day=None
        )

        static_segment = self.old_state.apps.get_model(
            "tapir_mail", "StaticSegment"
        ).objects.create(name="Mail-Kategorie:category")
        mail_category = self.old_state.apps.get_model(
            "tapir_mail", "MailCategory"
        ).objects.create(
            name="category",
            mode="optional_default_on",
            available_for_external_recipients=False,
            static_segment=static_segment,
            dynamic_segment_name="segment",
        )
        registration_model = self.old_state.apps.get_model(
            "tapir_mail", "InternalRecipientCategoryRegistration"
        )
        for extra in [
            self.oldest_shared,
            self.newer_shared,
            self.main_address_of_other,
        ]:
            registration_model.objects.create(
                member_extra_email=extra,
                mail_category=mail_category,
                is_registered=True,
            )

    def test_forward(self):
        extra_model = self.new_state.apps.get_model("wirgarten", "MemberExtraEmail")
        confirmed_ids = set(
            extra_model.objects.filter(confirmed_on__isnull=False).values_list(
                "id", flat=True
            )
        )
        self.assertEqual({self.oldest_shared.id, self.unique.id}, confirmed_ids)

        registration_model = self.new_state.apps.get_model(
            "tapir_mail", "InternalRecipientCategoryRegistration"
        )
        self.assertEqual(
            [self.oldest_shared.id],
            list(
                registration_model.objects.values_list(
                    "member_extra_email_id", flat=True
                )
            ),
        )

    def _create_extra(self, member: Model, email: str, confirmed_day: int | None):
        return self.old_state.apps.get_model(
            "wirgarten", "MemberExtraEmail"
        ).objects.create(
            member=member,
            email=email,
            confirmed_on=(
                datetime.datetime(
                    year=2025, month=1, day=confirmed_day, tzinfo=datetime.UTC
                )
                if confirmed_day is not None
                else None
            ),
        )
