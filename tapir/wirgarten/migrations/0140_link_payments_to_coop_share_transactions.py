from django.db import migrations


def link_payments_to_coop_share_transactions(apps, schema):
    # Payments that were merged for several purchases get split into one payment per purchase.
    # The first purchase keeps the original payment and any difference to its expected amount.
    coop_share_transaction_class = apps.get_model("wirgarten", "CoopShareTransaction")
    payment_class = apps.get_model("wirgarten", "Payment")

    transactions_by_payment_id = {}
    for coop_share_transaction in coop_share_transaction_class.objects.filter(
        payment__isnull=False
    ).order_by("timestamp", "id"):
        transactions_by_payment_id.setdefault(
            coop_share_transaction.payment_id, []
        ).append(coop_share_transaction)

    for payment in payment_class.objects.filter(
        id__in=transactions_by_payment_id.keys()
    ):
        first_transaction, *other_transactions = transactions_by_payment_id[payment.id]
        for other_transaction in other_transactions:
            amount = other_transaction.share_price * other_transaction.quantity
            payment_class.objects.create(
                due_date=payment.due_date,
                mandate_ref_id=payment.mandate_ref_id,
                amount=amount,
                status=payment.status,
                edited=payment.edited,
                transaction_id=payment.transaction_id,
                type=payment.type,
                coop_share_transaction=other_transaction,
            )
            payment.amount -= amount

        payment.coop_share_transaction = first_transaction
        payment.save()


def merge_payments_of_coop_share_transactions(apps, schema):
    payment_class = apps.get_model("wirgarten", "Payment")

    payments_by_key = {}
    for payment in payment_class.objects.filter(
        coop_share_transaction__isnull=False
    ).order_by("created_at", "id"):
        key = (
            payment.due_date,
            payment.mandate_ref_id,
            payment.transaction_id,
            payment.status,
        )
        payments_by_key.setdefault(key, []).append(payment)

    for first_payment, *other_payments in payments_by_key.values():
        for other_payment in other_payments:
            first_payment.amount += other_payment.amount
            other_payment.coop_share_transaction.payment = first_payment
            other_payment.coop_share_transaction.save()
            other_payment.delete()

        first_payment.coop_share_transaction.payment = first_payment
        first_payment.coop_share_transaction.save()
        first_payment.save()


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0139_payment_coop_share_transaction"),
    ]

    operations = [
        migrations.RunPython(
            link_payments_to_coop_share_transactions,
            merge_payments_of_coop_share_transactions,
        ),
    ]
