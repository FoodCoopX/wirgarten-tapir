import sys

from django.core.management import BaseCommand

from tapir.wirgarten.models import Member


class Command(BaseCommand):
    help = "Sends the keycloak verify emails to the specified user group"

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-subscription",
            help="Send keycloak verify emails to the Members with any Subscription",
            action="store_true",
        )
        parser.add_argument(
            "--no-subscription",
            help="Send keycloak verify emails to the Members WITHOUT any Subscription (only investing)",
            action="store_true",
        )

    def handle(self, *args, **options):
        def confirm_member_group(members):
            if len(members) < 1:
                self.stdout.write(
                    self.style.WARNING("-> No Members in selected user group!")
                )
                sys.exit(1)
            for member in members:

                print("- ", member)
                if member.subscription_set.exists():
                    print(
                        "         -",
                        "\n         - ".join(
                            map(lambda x: x.__str__(), member.subscription_set.all())
                        ),
                    )
            answer = input("Are you sure you want to continue? [y/N] ")
            if answer.lower() not in ["y", "yes"]:
                self.stdout.write(self.style.WARNING("Command was canceled."))
                sys.exit(1)
            else:
                return True

        def send_emails(members):
            if confirm_member_group(members):
                for m in members:
                    try:
                        m.save(bypass_keycloak=False)
                    except Exception as e:
                        print(e)
                        continue

        qs = Member.objects.filter(keycloak_id=None)
        if options["with_subscription"]:
            members = list(
                qs.filter(subscription__isnull=False)
                .distinct()
                .order_by("member_no", "last_name")
            )
            print(f"Sending emails to {len(members)} members WITH subscription:")
            send_emails(members)

        elif options["no_subscription"]:
            members = list(
                qs.exclude(subscription__isnull=False)
                .distinct()
                .order_by("member_no", "last_name")
            )
            print(f"Sending emails to {len(members)} members WITHOUT subscription:")
            send_emails(members)

        else:
            self.print_help("manage.py", "send_verify_emails")
            sys.exit(1)
