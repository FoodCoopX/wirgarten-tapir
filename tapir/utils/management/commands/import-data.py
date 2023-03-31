from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
import django.db
from tapir.wirgarten.models import Member, Subscription, CoopShareTransaction, TapirUser, GrowingPeriod, \
    MandateReference, Product, PickupLocation
from tapir.wirgarten.service.member import get_or_create_mandate_ref
import csv

class Command(BaseCommand):
    help = 'Imports data from CSV files into the database'

    def add_arguments(self, parser):
        parser.add_argument('--type', nargs=1, choices=['members', 'shares', 'subscriptions'], required=True)
        parser.add_argument('--file', nargs=1, required=True)
        parser.add_argument('--delete-all', action='store_true')

    def handle(self, *args, **options):
        #print(args)
        print(options)
        filepath = options["file"][0]
        type = options["type"][0]
        delete_all = options["delete_all"]

        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            if type == "members":
                if delete_all:
                    Member.objects.all().delete()
                for row in reader:
                    # identify pickup location ID
                    try:
                        if row["Abholort"] != '':
                            picloc = PickupLocation.objects.get(name=row["Abholort"]).id
                        else:
                            picloc = None
                    except ObjectDoesNotExist as e:
                        print(row)
                        print("Pickup Location not found - record is skipped!")
                        continue
                    m = Member(
                        first_name=row["Vorname"],
                        last_name=row["Nachname"],
                        birthdate=row["Geburtstag/Gründungsdatum"],
                        street=row["Straße"] + " " + row["Hausnr."],
                        postcode=row["PLZ"],
                        city=row["Ort"],
                        email=row["Mailadresse"],
                        phone_number=row["Telefon"],
                        id=row["Nr"],
                        iban=row["IBAN"],
                        account_owner=row["Kontoinhaber"],
                        sepa_consent=row["consent_sepa"] + "T12:00:00+0200",
                        privacy_consent=row["privacy_consent"] + "T12:00:00+0200",
                        pickup_location_id=picloc
                    )
                    try:
                        m.save(bypass_keycloak=True)
                    except Exception as e:
                        print(e)
                        continue
            if type == "shares":
                if delete_all:
                    CoopShareTransaction.objects.all().delete()
                for row in reader:
                    print(row)
                    #{'Mitgliedsnummer': '1', 'Bewegungsart (Z,Ü,K)': 'Z', 'Datum': '2017-03-10', 'Anzahl Anteile': '2', 'Wert Anteile': '100', 'Übertragungspartner': '', 'Wirkung Kündigung': ''}
                    qu = int(row["Anzahl Anteile"])
                    transfer_member = None
                    valid_date = row["Datum"]
                    if row["Übertragungspartner"] != '':
                        try:
                            transfer_member=Member.objects.get(id=row["Übertragungspartner"])
                            print(transfer_member)
                        except ObjectDoesNotExist as e:
                            print("Transfer Member not found!")
                            continue
                    match row["Bewegungsart (Z,Ü,K)"]:
                        case "Z":
                            trans_type = CoopShareTransaction.CoopShareTransactionType.PURCHASE
                        case "Ü":
                            if qu > 0:
                                trans_type = CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN
                            else:
                                trans_type = CoopShareTransaction.CoopShareTransactionType.TRANSFER_OUT

                        case "K":
                            trans_type = CoopShareTransaction.CoopShareTransactionType.CANCELLATION
                            valid_date = row["Wirkung Kündigung"]
                        case _:
                            raise "Unknown transaction type!"
                    try:
                        s = CoopShareTransaction.objects.create(
                            member_id=row["Mitgliedsnummer"],
                            transaction_type=trans_type,
                            timestamp=row["Datum"],
                            valid_at=valid_date,
                            quantity=qu,
                            share_price=50,
                            transfer_member=transfer_member
                        )
                    except django.db.Error as e:
                        print("Database Error occured",e.__cause__)
                    except ValidationError as e:
                        print("Validation Error occured",e.messages)
            if type == "subscriptions":
                if delete_all:
                    Subscription.objects.all().delete()
                    # identify current growing_period
                period = GrowingPeriod.objects.get(start_date="2023-01-01")
                for row in reader:
                    # VertragNr,Zeitstempel,E-Mail-Adresse,Tapir-ID,Mitgliedernummer,Probevertrag,Vertragsbeginn,[S-Ernteanteil],[M-Ernteanteil],[L-Ernteanteil],[XL-Ernteanteil],product,Quantity,Richtpreis,Solidarpreis in Prozent,"Gesamtzahlung",Vertragsgrundsätze,Abholort,Email-Adressen,Ernteanteilsreduzierung/erhöhung,consent_widerruf,consent_vertragsgrundsätze,cancellation.ts
                    # print(row)
                    # identify TapirUserID, either via MemberNo or Email
                    try:
                        if row["Mitgliedernummer"] != "":
                            m = TapirUser.objects.get(id=row["Mitgliedernummer"])
                        else:
                            if row["E-Mail-Adresse"] != "":
                                m = TapirUser.objects.get(email=row["E-Mail-Adresse"])
                            else:
                                print("No data to identify TapirUser in Vertrag ",row["VertragNr"])
                    except django.core.exceptions.ObjectDoesNotExist as e:
                        print(row)
                        print("Database Error: TapirUser not found",e.__cause__)
                        continue
                    except django.db.Error as e:
                        print(row)
                        print("Database Error occured with MemberNo",e.__cause__)
                        continue
                    except ValidationError as e:
                        print(row)
                        print("Validation Error occured",e.messages)
                        continue
                    # identify MandateRef
                    mref = get_or_create_mandate_ref(m)
                    # identify product
                    try:
                        if row["product"]:
                            prod = Product.objects.get(name=row["product"])
                        else:
                            print("No product defined in Vertrag ", row["VertragNr"])
                            continue
                    except django.core.exceptions.ObjectDoesNotExist as e:
                        print(row)
                        print("Product not found",e.__cause__)
                        continue
                    # prepare cancellation value
                    if row["cancellation.ts"] != "":
                        ts_cancel = row["cancellation.ts"]
                    else:
                        ts_cancel = None
                    try:
                        s = Subscription.objects.create(
                            member_id=m.id,
                            quantity=float(row["Quantity"]),
                            start_date=row["Vertragsbeginn"],
                            end_date="2023-06-30",
                            cancellation_ts=ts_cancel ,
                            solidarity_price=row["Solidarpreis in Prozent"],
                            mandate_ref_id=mref.ref,
                            period_id=period.id,
                            product_id=prod.id,
                            consent_ts="2023-01-01 12:00:00",
                        )
                        print("Subscription object successfully created.")
                    except django.db.Error as e:
                        print(row)
                        print("Database Error occured with create subscription: ",e.__cause__)
                        continue
                    except ValidationError as e:
                        print(row)
                        print("Validation Error occured with create subscription: ",e.messages)
                        continue
                    except ValueError as e:
                        print(row)
                        print("Value Error occured with create subscription: ",e)
                        continue





