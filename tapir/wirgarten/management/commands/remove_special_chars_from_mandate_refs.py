from tapir.wirgarten.models import (
    MandateReference,
    Payment,
    CoopShareTransaction,
    Subscription,
)
from unidecode import unidecode
from django.db import transaction, IntegrityError
from django.core.management import BaseCommand


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        for orig_mandate_ref in MandateReference.objects.all():
            new_str = unidecode(orig_mandate_ref.ref)
            if new_str != orig_mandate_ref.ref:
                print(
                    f"{orig_mandate_ref.member} >> Changed mandate ref from '{orig_mandate_ref.ref}' to '{new_str}'"
                )
                mandate_ref = MandateReference.objects.create(
                    member=orig_mandate_ref.member,
                    ref=new_str,
                    start_ts=orig_mandate_ref.start_ts,
                    end_ts=orig_mandate_ref.end_ts,
                )

                payments = Payment.objects.filter(mandate_ref=orig_mandate_ref.ref)
                if payments.exists():
                    print("\tUpdating payments: ", payments.count())
                    payments.update(mandate_ref=mandate_ref)

                coop_share_transactions = CoopShareTransaction.objects.filter(
                    mandate_ref=orig_mandate_ref.ref
                )
                if coop_share_transactions.exists():
                    print(
                        "\tUpdating coop share transactions: ",
                        coop_share_transactions.count(),
                    )
                    coop_share_transactions.update(mandate_ref=mandate_ref)

                subs = Subscription.objects.filter(mandate_ref=orig_mandate_ref.ref)
                if subs.exists():
                    print("\tUpdating subs: ", subs.count())
                    subs.update(mandate_ref=mandate_ref)

                orig_mandate_ref.delete()
