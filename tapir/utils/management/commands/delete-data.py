from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand

from tapir.wirgarten.models import Member, Subscription, CoopShareTransaction, \
    MandateReference, Payment


class Command(BaseCommand):
    help = 'Delete member/shares/subscription data from database'

    def add_arguments(self, parser):
        parser.add_argument('--member-no', type=int)
        parser.add_argument('--member-email', type=str)
        parser.add_argument('--delete-shares', action='store_true')
        parser.add_argument('--delete-subscriptions', action='store_true')
        parser.add_argument('--delete-complete', action='store_true')
        parser.add_argument('--dry-run', choices='yes,no', default='yes')

    def handle(self, *args, **options):
        print(options)

        # check params
        if not options["member_no"] and not options["member_email"]:
            print("Either --member-no or --member-email must be given - otherwise no member identification possible!")
            return

        if not options["delete_shares"] and not options["delete_subscriptions"] and not options["delete_complete"]:
            print("No delete flag set - don't know what to delete!")
            return

        mno = options["member_no"]
        mmail = options["member_email"]
        del_complete = options["delete_complete"]
        del_shares = options["delete_shares"]
        del_subs = options["delete_subscriptions"]
        dry = options["dry_run"] == 'yes'

        if mno:
            try:
                m = Member.objects.get(member_no=mno)
                m_id = m.tapiruser_ptr_id
            except ObjectDoesNotExist as e:
                print(f"Member not found with member_no {mno} - nothing changed.")
                return
        elif mmail:
            try:
                m = Member.objects.get(email=mmail)
                m_id = m.id
            except ObjectDoesNotExist as e:
                print(f"Member not found with member_mail {mmail} - nothing changed.")
                return
        print(m)

        if del_shares or del_complete:
            try:
                shares_list = CoopShareTransaction.objects.filter(member_id=m_id)
                if dry:
                    print("DRY-RUN: Would delete shares: ", shares_list)
                else:
                    res = shares_list.delete()
                    print("Deleted:", res)
            except Exception as e:
                print(e)

        if del_subs or del_complete:
            try:
                subs_list = Subscription.objects.filter(member_id=m_id)
                if dry:
                    print("DRY-RUN: Would delete subscriptions: ", subs_list)
                else:
                    res = subs_list.delete()
                    print("Deleted:", res)
            except Exception as e:
                print(e)

        if del_complete:
            # first delete mandate references and payments
            try:
                ref_list = MandateReference.objects.filter(member_id=m_id)
                pay_list = []
                print("DRY-RUN: Would delete mandate references: ", ref_list)
                # check payments
                for mr in ref_list:
                    pres = Payment.objects.filter(mandate_ref_id=mr.ref)
                    if pres:
                        for p in pres:
                            pay_list.append(p)
                print("DRY-RUN: Would delete payments: ", pay_list)
                if not dry:
                    for p in pay_list:
                        p.delete()
                        print("Deleted payment.", p)
                    res = ref_list.delete()
                    print("Deleted:", res)
            except Exception as e:
                print(e)
                return
            if dry:
                print("DRY-RUN: Would delete member: ", m)
            else:
                try:
                    res = m.delete()
                    print(f"Deleted member {m} with all dependent records.")
                except Exception as e:
                    print(e)
            return
