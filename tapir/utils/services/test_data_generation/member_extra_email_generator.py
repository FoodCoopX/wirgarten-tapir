import factory.random
from faker import Faker

from tapir.core.services.member_extra_email_registration_snapshotter import (
    MemberExtraEmailRegistrationSnapshotter,
)
from tapir.wirgarten.models import Member, MemberExtraEmail
from tapir.wirgarten.utils import get_now


class MemberExtraEmailGenerator:
    EXTRA_EMAIL_PROBABILITY = 0.15
    UNCONFIRMED_PROBABILITY = 0.2
    WITHOUT_DIRECT_MAILS_PROBABILITY = 0.3

    @classmethod
    def generate_member_extra_emails(cls):
        cache = {}
        fake = Faker("de_DE")
        fake.seed_instance("tapir")

        for member in Member.objects.order_by("email"):
            if factory.random.randgen.random() >= cls.EXTRA_EMAIL_PROBABILITY:
                continue

            extra_email = MemberExtraEmail.objects.create(
                member=member,
                email=f"{member.email.split('@')[0]}.extra@example.com",
                first_name=fake.first_name(),
                last_name=member.last_name,
                confirmed_on=(
                    None
                    if factory.random.randgen.random() < cls.UNCONFIRMED_PROBABILITY
                    else get_now(cache=cache)
                ),
                receives_direct_mails=factory.random.randgen.random()
                >= cls.WITHOUT_DIRECT_MAILS_PROBABILITY,
            )
            if extra_email.is_confirmed and extra_email.receives_direct_mails:
                MemberExtraEmailRegistrationSnapshotter.snapshot(
                    extra_email=extra_email, cache=cache
                )
