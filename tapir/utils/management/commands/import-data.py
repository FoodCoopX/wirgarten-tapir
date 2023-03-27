from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
import django.db
from tapir.wirgarten.models import Member,Subscription,CoopShareTransaction,TapirUser
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
                    print(row)
                    m = Member.objects.create(
                        first_name=row["Vorname"],
                        last_name=row["Nachname"],
                        birthdate=row["Geburtstag/Gründungsdatum"],
                        street=row["Straße"],
                        postcode=row["PLZ"],
                        city=row["Ort"],
                        email=row["Mailadresse"],
                        phone_number=row["Mobil"],
                        id=row["Nr"]
                    )
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
                        except django.core.exceptions.ObjectDoesNotExist as e:
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
                for row in reader:
                    print(row)
                    # find out TapirUserID, either via MemberNo or Email
                    m = TapirUser.objects.get(=row[""])
                    s = Subscription.objects.get_or_create(
                        member_id=row["Mitgliedsnummer"],
                        entry_date=row["Datum"],
                        quantity=row["Anzahl Anteile"],
                        share_price=50,
                    )
                    s.save()




