from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT


class PaymentTypeLabelGetter:
    @staticmethod
    def get_label(payment_type: str) -> str:
        return (
            "Vereinseinlage"
            if payment_type == PAYMENT_TYPE_ASSOCIATION_DEPOSIT
            else payment_type
        )
