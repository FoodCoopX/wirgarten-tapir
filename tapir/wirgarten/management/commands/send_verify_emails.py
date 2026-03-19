from django.core.management import BaseCommand
from django.db.models import QuerySet, Count, Q

from tapir.wirgarten.models import Member
from tapir.wirgarten.service.member import (
    annotate_member_queryset_with_coop_shares_total_value,
)
from tapir.wirgarten.utils import get_today


class Command(BaseCommand):
    help = (
        "Sends the keycloak verification mails to all members that don't have a keycloak account yet. "
        "Members that have neither coop shares nor subscriptions are ignored."
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
        members = (
            self.get_members_with_at_least_one_share_or_one_relevant_subscription()
        )

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
        self.stdout.write(
            f"Sending emails to {len(members)} members WITHOUT subscription:"
        )

        self.send_emails(members, options["dry_run"])

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
        queryset: QuerySet[Member],
    ):
        return queryset.annotate(
            num_subscriptions=Count(
                "subscription", filter=Q(subscription__end_date__gte=get_today())
            )
        )

    @classmethod
    def get_members_with_at_least_one_share_or_one_relevant_subscription(cls):
        members = Member.objects.filter(keycloak_id=None)
        members = annotate_member_queryset_with_coop_shares_total_value(
            queryset=members
        ).filter()
        members = cls.annotate_member_queryset_with_number_of_current_and_future_subscriptions(
            members
        )
        return members.filter(
            Q(coop_shares_total_value__gt=0) | Q(num_subscriptions__gt=0)
        )

    def send_emails(self, members, dry_run: bool):
        if not self.confirm_member_group(members):
            return

        if dry_run:
            self.stdout.write("Dry run enabled, aborting")
            return

        for member in members:
            try:
                member.save(bypass_keycloak=False)
                # The member must be saved twice in order to persist the keycloak ID
                member.save(bypass_keycloak=False)
            except Exception as e:
                self.stderr.write(f"Error when saving member {member}: {e}")
                continue
