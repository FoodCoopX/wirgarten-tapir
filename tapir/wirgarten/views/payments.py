from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import generic

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import PaymentTransaction, Payment


class PaymentTransactionListView(PermissionRequiredMixin, generic.list.ListView):
    permission_required = Permission.Payments.VIEW
    template_name = "wirgarten/payment/payment_list.html"

    def __init__(self):
        super(PaymentTransactionListView, self).__init__()
        self.object_list = self.get_queryset()

    def get_queryset(self):
        def get_transaction_dict(t: PaymentTransaction):
            payments = list(Payment.objects.filter(transaction=t))
            return {
                "id": t.id,
                "created_at": t.created_at,
                "number_of_payments": len(payments),
                "total_amount": sum(map(lambda p: p.amount, payments)),
                "file": t.file,
                "payments": payments,
            }

        return list(
            map(
                get_transaction_dict,
                PaymentTransaction.objects.all().order_by("-created_at"),
            )
        )
