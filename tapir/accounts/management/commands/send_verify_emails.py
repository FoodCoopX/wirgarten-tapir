from django.core.management import BaseCommand
from django.db.models import QuerySet, Count, Q

from tapir.accounts.exceptions import VerificationEmailsAlreadySendingException
from tapir.accounts.services.unverified_members_service import (
    UnverifiedMembersService,
)
from tapir.generic_exports.services.member_segment_provider import (
    MemberSegmentProvider,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today


class Command(BaseCommand):
    help = (
        "Sends the keycloak verification mails to all members that don't have a keycloak account yet. "
        "Only active members (as in the 'active users' mail segment) are considered."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-members-with-subscription",
            help="Filter out members that don't have any subscription (past subscriptions are ignored)",
            action="store_true",
        )
        parser.add_argument(
            "--only-members-without-subscription",
            help="Filter out members that have at least one subscription (past subscriptions are ignored)",
            action="store_true",
        )
        parser.add_argument(
            "--dry-run",
            help="Don't apply any permanent change (mails won't be sent)",
            action="store_true",
        )

    def handle(self, *args, **options):
        cache = {}
        members = self.get_active_members_without_keycloak_account(cache=cache)

        if not members.exists():
            self.stdout.write(
                self.style.WARNING("-> No Members in selected user group!")
            )
            return

        self.stdout.write(
            f"{members.count()} members in total don't have a keycloak account yet"
        )

        if options["only_members_without_subscription"]:
            count_before = members.count()
            members = members.filter(num_subscriptions=0)
            count_after = members.count()
            self.stdout.write(
                f"{count_before - count_after} members will be ignored because they have a current or future subscription"
            )

        if options["only_members_with_subscription"]:
            count_before = members.count()
            members = members.filter(num_subscriptions__gt=0)
            count_after = members.count()
            self.stdout.write(
                f"{count_before - count_after} members will be ignored because they don't have a current or future subscription"
            )

        members = list(members.distinct().order_by("member_no", "last_name"))
        self.stdout.write(f"Sending emails to {len(members)} members:")

        self.send_emails(members=members, dry_run=options["dry_run"])

    def confirm_member_group(self, members):
        if len(members) == 0:
            self.stdout.write(
                self.style.WARNING("-> No Members in selected user group!")
            )
            return False

        for member in members:
            self.stdout.write(f" - {member}")
            subscriptions = list(member.subscription_set.all())
            if len(subscriptions) > 0:
                self.stdout.write(
                    "\n".join(f"\t - {subscription}" for subscription in subscriptions),
                )

        answer = input("Are you sure you want to continue? [y/N] ")
        if answer.lower() not in ["y", "yes"]:
            self.stdout.write(self.style.WARNING("Command was canceled."))
            return False
        else:
            return True

    @staticmethod
    def annotate_member_queryset_with_number_of_current_and_future_subscriptions(
        queryset: QuerySet[Member], cache: dict
    ):
        return queryset.annotate(
            num_subscriptions=Count(
                "subscription",
                filter=Q(subscription__end_date__gte=get_today(cache=cache)),
            )
        )

    @classmethod
    def get_active_members_without_keycloak_account(cls, cache: dict):
        members = MemberSegmentProvider.get_queryset_active_members(cache=cache).filter(
            keycloak_id=None
        )
        return cls.annotate_member_queryset_with_number_of_current_and_future_subscriptions(
            queryset=members, cache=cache
        )

    def send_emails(self, members, dry_run: bool):
        if not self.confirm_member_group(members):
            return

        if dry_run:
            self.stdout.write("Dry run enabled, aborting")
            return

        try:
            UnverifiedMembersService.send_verification_emails(
                members=members, actor=None
            )
        except VerificationEmailsAlreadySendingException:
            self.stderr.write(
                "Verification emails are already being sent, try again later"
            )
