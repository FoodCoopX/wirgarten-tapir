from importlib.resources import _

from django.forms import Form, BooleanField, DecimalField, CharField

from tapir.wirgarten.models import Payment


class PaymentAmountEditForm(Form):
    def __init__(self, *args, **kwargs):
        super(PaymentAmountEditForm, self).__init__(*args)

        self.mandate_ref_id = kwargs["mandate_ref_id"].replace("~", "/")
        self.payment_due_date = kwargs["payment_due_date"]

        payments = Payment.objects.filter(
            mandate_ref=self.mandate_ref_id, due_date=self.payment_due_date
        )
        if len(payments) < 1:
            initial = 0.00
        elif len(payments) > 1:
            raise AssertionError("TOO MANY PAYMENTS FOUND!!")  # FIXME
        else:
            self.payment = payments[0]
            initial = self.payment.amount

        self.fields["comment"] = CharField(label=_("Änderungsgrund"), required=True)
        self.fields["amount"] = DecimalField(
            label=_("Neuer Betrag [€]"), initial=round(initial, 2)
        )
        self.fields["security_check"] = BooleanField(
            label=_(
                "Ich weiß was ich tue und bin mir der möglichen Konsequenzen bewusst."
            ),
            required=True,
            initial=False,
        )

    def is_valid(self):
        return (
            self.data["comment"]
            and self.data["security_check"]
            and float(self.data["amount"]) > 0
        )
