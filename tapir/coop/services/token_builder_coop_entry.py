from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.utils import format_currency, format_date


class TokenBuilderCoopEntry:
    @classmethod
    def build_mail_tokens_for_coop_entry(
        cls, coop_share_transaction: CoopShareTransaction | None
    ):
        if coop_share_transaction is None:
            return {
                "number_of_coop_shares": "0",
                "price_of_a_coop_share": "0",
                "total_cost": "0",
                "membership_start_date": "Keine Datum",
            }

        return {
            "number_of_coop_shares": coop_share_transaction.quantity,
            "price_of_a_coop_share": format_currency(
                coop_share_transaction.share_price
            ),
            "total_cost": format_currency(coop_share_transaction.total_price),
            "membership_start_date": format_date(coop_share_transaction.valid_at),
        }
