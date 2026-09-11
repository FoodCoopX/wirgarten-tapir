from __future__ import annotations

import re
from typing import Iterable, Set

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tapir.wirgarten.models import Member, Subscription


def parse_member_numbers(specs: Iterable[str]) -> Set[int]:
    """
    Parse a list of member number specifications into a concrete set of ints.

    Accepted formats (can be mixed, separated by commas or whitespace):
    - Single numbers: "123"
    - Ranges: "100-120" (inclusive)

    Examples:
      ["100-103, 200, 250-252", "300", "400-401"] -> {100,101,102,103,200,250,251,252,300,400,401}
    """
    result: set[int] = set()

    def add_token(token: str):
        token = token.strip()
        if not token:
            return
        m = re.fullmatch(r"(\d+)-(\d+)", token)
        if m:
            start = int(m.group(1))
            end = int(m.group(2))
            if end < start:
                raise CommandError(f"Ungültiger Bereich: {token} (Ende < Start)")
            result.update(range(start, end + 1))
            return
        if re.fullmatch(r"\d+", token):
            result.add(int(token))
            return
        raise CommandError(f"Ungültiges Mitgliedsnummer-Token: '{token}'")

    for spec in specs:
        if spec is None:
            continue
        # split by commas or whitespace
        for token in re.split(r"[\s,]+", str(spec)):
            add_token(token)

    return result


class Command(BaseCommand):
    help = (
        "Löscht Subscriptions (inkl. abhängiger Datenstrukturen) für angegebene Mitgliedsnummern.\n"
        "Mit --members können Listen und Bereiche angegeben werden, z. B.:\n"
        "  --members '100-120, 135, 200-205' --members 300 301-303\n"
        "Standardmäßig wird ein Dry-Run durchgeführt; mit --yes wird die Löschung bestätigt."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--members",
            dest="members",
            action="append",
            default=[],
            help=(
                "Mitgliedsnummern als Liste/Ranges, z. B. '100-120,135,200' oder mehrfaches --members."
            ),
        )
        parser.add_argument(
            "--exclude",
            dest="exclude",
            action="append",
            default=[],
            help=(
                "Optionale Ausschlussliste (gleiches Format wie --members), um bestimmte Nummern auszunehmen."
            ),
        )
        parser.add_argument(
            "--yes",
            dest="confirm",
            action="store_true",
            help="Ohne Rückfrage wirklich löschen (kein Dry-Run).",
        )

    def handle(self, *args, **options):
        members_specs = options.get("members") or []
        exclude_specs = options.get("exclude") or []
        confirm: bool = bool(options.get("confirm"))

        if not members_specs:
            raise CommandError("Bitte mindestens einen --members Parameter angeben.")

        member_nos = parse_member_numbers(members_specs)
        if exclude_specs:
            member_nos -= parse_member_numbers(exclude_specs)

        if not member_nos:
            self.stdout.write(
                self.style.WARNING("Keine Mitgliedsnummern nach Parsing übrig.")
            )
            return

        members_qs = Member.objects.filter(member_no__in=member_nos)
        found_nos = set(members_qs.values_list("member_no", flat=True))
        missing_nos = sorted(member_nos - found_nos)

        if missing_nos:
            self.stdout.write(
                self.style.WARNING(
                    f"Warnung: {len(missing_nos)} Mitgliedsnummer(n) nicht gefunden: {', '.join(map(str, missing_nos))}"
                )
            )

        subs_qs = Subscription.objects.filter(member__in=members_qs)
        total_subs = subs_qs.count()

        self.stdout.write(
            self.style.NOTICE(
                f"Gefundene Mitglieder: {len(found_nos)} | Zu löschende Subscriptions: {total_subs}"
            )
        )

        # Detailübersicht (optional): Anzahl Subscriptions pro Mitglied
        per_member = (
            subs_qs.values_list("member__member_no")
            .order_by("member__member_no")
            .distinct()
        )
        details = []
        for (member_no,) in per_member:
            cnt = subs_qs.filter(member__member_no=member_no).count()
            details.append((member_no, cnt))
        if details:
            lines = [f"  Mitglied {mn}: {cnt} Subscriptions" for mn, cnt in details]
            self.stdout.write("Details:\n" + "\n".join(lines))

        if not confirm:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-Run: Es wurden keine Daten gelöscht. Führen Sie den Befehl mit --yes aus, um zu löschen."
                )
            )
            return

        with transaction.atomic():
            deleted_map = {}
            # Sammle die zu löschenden IDs vorab für eine sprechende Ausgabe
            for mn, cnt in details:
                deleted_map[mn] = cnt
            deleted_count, _ = subs_qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Löschung abgeschlossen. Gelöschte Objekte (gesamt): {deleted_count}"
            )
        )
        if deleted_map:
            lines = [
                f"  Mitglied {mn}: {cnt} Subscriptions gelöscht"
                for mn, cnt in deleted_map.items()
            ]
            self.stdout.write("Details:\n" + "\n".join(lines))
