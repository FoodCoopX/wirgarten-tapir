import csv
import mimetypes

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.db.models import Count, Max, Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET
from django.views.generic import View

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import CoopShareTransaction, Member
from tapir.wirgarten.service.file_export import begin_csv_string
from tapir.wirgarten.utils import format_currency, format_date, get_now, get_today
from tapir.wirgarten.views.member.list.member_list import MemberFilter, MemberListView


@require_GET
@csrf_protect
@permission_required(Permission.Coop.VIEW)
def export_coop_member_list(request, **kwargs):
    KEY_MEMBER_NO = "Nr"
    KEY_FIRST_NAME = "Vorname"
    KEY_LAST_NAME = "Nachname"
    KEY_ADDRESS = "Straße + Hausnr."
    KEY_ADDRESS2 = "Adresse 2"
    KEY_POSTCODE = "PLZ"
    KEY_CITY = "Ort"
    KEY_BIRTHDATE = "Geburtstag/Gründungsdatum"
    KEY_TELEPHONE = "Telefon"
    KEY_EMAIL = "Mailadresse"
    KEY_COOP_SHARES_TOTAL = "GAnteile gesamt"
    KEY_COOP_SHARES_TOTAL_EURO = "GAnteile in € gesamt"
    KEY_COOP_SHARES_CANCELLATION_DATE = (
        "Kündigungsdatum der Mitgliedschaft/ (einzelner) Geschäftsanteile"
    )
    KEY_COOP_SHARES_CANCELLATION_AMOUNT = "Wert der gekündigten Geschäftsanteile"
    KEY_COOP_SHARES_CANCELLATION_CONTRACT_END_DATE = (
        "Inkrafttreten der Kündigung der Mitgliedschaft/(einzelner) Geschäftsanteile"
    )
    KEY_COOP_SHARES_TRANSFER_EURO = "Übertragung Genossenschaftsanteile"
    KEY_COOP_SHARES_TRANSFER_FROM_TO = "Übertragung an/von"
    KEY_COOP_SHARES_TRANSFER_DATE = "Datum der Übertragung"
    KEY_COOP_SHARES_PAYBACK_EURO = "Ausgezahltes Geschäftsguthaben"
    KEY_COMMENT = "Kommentar"

    # Determine maximum number of shares a member has
    max_shares = Member.objects.annotate(
        purchase_transactions_count=Count(
            "coopsharetransaction",
            filter=Q(
                coopsharetransaction__transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE
            ),
        )
    ).aggregate(max_purchase_transactions=Max("purchase_transactions_count"))[
        "max_purchase_transactions"
    ]

    # Generate column headers for each share ownership entry
    share_cols = {}
    for i in range(1, max_shares + 1):
        share_cols[f"KEY_COOP_SHARES_{i}_EURO"] = f"GAnteile in € {i}. Zeichnung"
        share_cols[f"KEY_COOP_SHARES_{i}_ENTRY_DATE"] = f"Eintrittsdatum {i}. Zeichnung"

    output, writer = begin_csv_string(
        [
            KEY_MEMBER_NO,
            KEY_FIRST_NAME,
            KEY_LAST_NAME,
            KEY_ADDRESS,
            KEY_ADDRESS2,
            KEY_POSTCODE,
            KEY_CITY,
            KEY_BIRTHDATE,
            KEY_TELEPHONE,
            KEY_EMAIL,
            KEY_COOP_SHARES_TOTAL,
            KEY_COOP_SHARES_TOTAL_EURO,
            *share_cols.values(),
            KEY_COOP_SHARES_CANCELLATION_DATE,
            KEY_COOP_SHARES_CANCELLATION_AMOUNT,
            KEY_COOP_SHARES_CANCELLATION_CONTRACT_END_DATE,
            KEY_COOP_SHARES_TRANSFER_EURO,
            KEY_COOP_SHARES_TRANSFER_FROM_TO,
            KEY_COOP_SHARES_TRANSFER_DATE,
            KEY_COOP_SHARES_PAYBACK_EURO,
            KEY_COMMENT,
        ]
    )
    for entry in Member.objects.order_by("member_no"):
        coop_shares = entry.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE
        ).order_by("timestamp")
        last_cancelled_coop_shares = entry.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION
        ).order_by("-timestamp")
        if len(last_cancelled_coop_shares) > 0:
            last_cancelled_coop_shares = last_cancelled_coop_shares[0]
        else:
            last_cancelled_coop_shares = None

        today = get_today()
        # skip future members. TODO: check cancellation, when must old members be removed from the list?
        if entry.coop_entry_date is None or entry.coop_entry_date > today:
            continue

        transfered_to = entry.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.TRANSFER_OUT
        )
        transfered_from = entry.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN
        )

        data = {
            KEY_MEMBER_NO: entry.member_no,
            KEY_FIRST_NAME: entry.first_name,
            KEY_LAST_NAME: entry.last_name,
            KEY_ADDRESS: entry.street,
            KEY_ADDRESS2: entry.street_2,
            KEY_POSTCODE: entry.postcode,
            KEY_CITY: entry.city,
            KEY_BIRTHDATE: format_date(entry.birthdate),
            KEY_TELEPHONE: entry.phone_number,
            KEY_EMAIL: entry.email,
            KEY_COOP_SHARES_TOTAL: entry.coop_shares_quantity,
            KEY_COOP_SHARES_TOTAL_EURO: format_currency(
                entry.coop_shares_total_value()
            ),
            KEY_COOP_SHARES_CANCELLATION_DATE: format_date(
                last_cancelled_coop_shares.timestamp
            )
            if last_cancelled_coop_shares and last_cancelled_coop_shares.valid_at
            else "",
            KEY_COOP_SHARES_CANCELLATION_AMOUNT: format_currency(
                last_cancelled_coop_shares.total_price
            )
            if last_cancelled_coop_shares and last_cancelled_coop_shares.valid_at
            else "",
            KEY_COOP_SHARES_CANCELLATION_CONTRACT_END_DATE: format_date(
                last_cancelled_coop_shares.valid_at
            )
            if last_cancelled_coop_shares and last_cancelled_coop_shares.valid_at
            else "",
            KEY_COOP_SHARES_PAYBACK_EURO: "",  # TODO: how??? Cancelled coop shares?
            KEY_COMMENT: "",  # TODO: join comment log entries?
        }

        for i, share in enumerate(coop_shares, start=1):
            data[share_cols[f"KEY_COOP_SHARES_{i}_EURO"]] = format_currency(
                share.total_price
            )
            data[share_cols[f"KEY_COOP_SHARES_{i}_ENTRY_DATE"]] = format_date(
                share.valid_at
            )

        transfer_euro_amount = (
            sum(map(lambda x: x.quantity, transfered_to))
            + sum(map(lambda x: x.quantity, transfered_from))
        ) * settings.COOP_SHARE_PRICE
        transfer_euro_string = (
            "" if transfer_euro_amount == 0 else format_currency(transfer_euro_amount)
        )

        transfer_to_string = ", ".join(
            map(
                lambda x: f"an {x.transfer_member.first_name} {x.transfer_member.last_name}: {format_currency(abs(x.quantity) * settings.COOP_SHARE_PRICE)}  €",
                transfered_to,
            )
        )
        transfer_from_string = ", ".join(
            map(
                lambda x: f"von {x.transfer_member.first_name} {x.transfer_member.last_name}: {format_currency(x.quantity * settings.COOP_SHARE_PRICE)} €",
                transfered_from,
            )
        )
        transfer_to_date = ", ".join(
            map(
                lambda x: f"an {x.transfer_member.first_name} {x.transfer_member.last_name}: {format_date(x.valid_at)}",
                transfered_to,
            )
        )
        transfer_from_date = ", ".join(
            map(
                lambda x: f"von {x.transfer_member.first_name} {x.transfer_member.last_name}: {format_date(x.valid_at)}",
                transfered_from,
            )
        )
        data[KEY_COOP_SHARES_TRANSFER_EURO] = transfer_euro_string
        if not transfer_to_string or not transfer_from_string:
            data[KEY_COOP_SHARES_TRANSFER_FROM_TO] = (
                transfer_to_string or transfer_from_string
            )
            data[KEY_COOP_SHARES_TRANSFER_DATE] = transfer_to_date or transfer_from_date
        else:
            data[KEY_COOP_SHARES_TRANSFER_FROM_TO] = (
                transfer_to_string + " | " + transfer_from_string
            )
            data[KEY_COOP_SHARES_TRANSFER_DATE] = (
                transfer_to_date + " | " + transfer_from_date
            )

        writer.writerow(data)

    filename = f"Mitgliederliste_{get_now().strftime('%Y%m%d_%H%M%S')}.csv"
    mime_type, _ = mimetypes.guess_type(filename)
    response = HttpResponse("".join(output.csv_string), content_type=mime_type)
    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response


class ExportMembersView(View):
    def get(self, request, *args, **kwargs):
        # Get queryset based on filters and ordering
        filter_class = MemberFilter
        queryset = filter_class(request.GET, queryset=self.get_queryset()).qs

        # Create response object with CSV content
        response = HttpResponse(content_type="text/csv")
        response[
            "Content-Disposition"
        ] = f'attachment; filename="Mitglieder_gefiltert_{get_now().strftime("%Y%m%d_%H%M%S")}.csv"'
        writer = csv.writer(response, delimiter=";")

        # Write header row
        writer.writerow(
            [
                "#",
                "Vorname",
                "Nachname",
                "Email",
                "Telefon",
                "Adresse",
                "PLZ",
                "Ort",
                "Land",
                "Registriert am",
                "Geno-Beitritt am",
                "Geschäftsanteile (€)",
                "Umsatz/Monat (€)",
                "Abholort",
            ]
        )

        # Write data rows
        for member in queryset:
            writer.writerow(
                [
                    member.member_no,
                    member.first_name,
                    member.last_name,
                    member.email,
                    member.phone_number,
                    member.street + (", " + member.street_2) if member.street_2 else "",
                    member.postcode,
                    member.city,
                    member.country,
                    format_date(member.created_at.date()),
                    format_date(member.coop_entry_date),
                    format_currency(member.coop_shares_total_value),
                    format_currency(member.monthly_payment),
                    member.pickup_location.name if member.pickup_location else "",
                ]
            )

        return response

    def get_queryset(self):
        return MemberListView.get_queryset(self)

    def get_filterset_class(self):
        return MemberFilter

    def get_success_url(self):
        return reverse_lazy("member_list")


@require_GET
@permission_required(Permission.Accounts.MANAGE)
@csrf_protect
def resend_verify_email(request, **kwargs):
    member_id = kwargs["pk"]
    member = Member.objects.get(id=member_id)
    try:
        member.send_verify_email()
        result = "success"
    except Exception as e:
        result = str(e)

    next_url = request.environ["QUERY_STRING"].replace("next=", "")

    return HttpResponseRedirect(next_url + "&resend_verify_email=" + result)
