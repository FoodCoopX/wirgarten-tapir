import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError

from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
)
from tapir.payments.services.payment_due_date_calculator import PaymentDueDateCalculator
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAssociationDepositInstalmentCalculator(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.cache = {}

    def test_instalment_count_bounds_do_not_coerce_invalid_values(self):
        for count in [1, 4, 12]:
            with self.subTest(count=count):
                AssociationDepositInstalmentCalculator.validate_instalment_count(count)
        for count in [0, 13, -1, True, "4", 1.5]:
            with self.subTest(count=count), self.assertRaises(ValidationError):
                AssociationDepositInstalmentCalculator.validate_instalment_count(count)

    def test_payment_schedule_preserves_exact_cent_totals(self):
        mock_parameter_value(self.cache, ParameterKeys.PAYMENT_DUE_DAY, 5)
        cases = [
            ("0.03", 3, ["0.01", "0.01", "0.01"]),
            ("100.01", 4, ["25.01", "25.00", "25.00", "25.00"]),
            ("200", 12, ["16.67"] * 8 + ["16.66"] * 4),
            ("200", 1, ["200.00"]),
        ]
        for amount, count, expected in cases:
            with self.subTest(amount=amount, count=count):
                plan = AssociationDepositInstalmentCalculator.build_payment_schedule(
                    Decimal(amount), count, datetime.date(2026, 11, 6), self.cache
                )
                self.assertEqual(
                    [Decimal(value) for value in expected], [p["amount"] for p in plan]
                )
                self.assertEqual(Decimal(amount), sum(p["amount"] for p in plan))
                self.assertTrue(all(p["amount"] > 0 for p in plan))
                self.assertEqual(datetime.date(2026, 12, 5), plan[0]["due_date"])
                self.assertEqual(
                    [None] if count == 1 else list(range(1, count + 1)),
                    [p["instalment_number"] for p in plan],
                )

    def test_schedule_recalculates_calendar_day_after_month_end_clamping(self):
        cases = [
            (31, datetime.date(2027, 2, 1), ["2027-02-28", "2027-03-31", "2027-04-30"]),
            (31, datetime.date(2028, 2, 1), ["2028-02-29", "2028-03-31", "2028-04-30"]),
            (
                30,
                datetime.date(2027, 1, 31),
                ["2027-02-28", "2027-03-30", "2027-04-30"],
            ),
            (
                31,
                datetime.date(2027, 4, 30),
                ["2027-04-30", "2027-05-31", "2027-06-30"],
            ),
        ]
        for day, start, expected in cases:
            with self.subTest(day=day, start=start):
                cache = {}
                mock_parameter_value(cache, ParameterKeys.PAYMENT_DUE_DAY, day)
                plan = AssociationDepositInstalmentCalculator.build_payment_schedule(
                    Decimal("200"), 3, start, cache
                )
                self.assertEqual(expected, [p["due_date"].isoformat() for p in plan])

    def test_adjustment_preserves_dates_ids_and_original_payments(self):
        payments = [
            Payment(
                id="first",
                amount=Decimal("50"),
                due_date=datetime.date(2026, 11, 5),
                instalment_number=1,
            ),
            Payment(
                id="second",
                amount=Decimal("50"),
                due_date=datetime.date(2026, 12, 5),
                instalment_number=2,
            ),
        ]
        for total, expected in [("75", ["25", "50"]), ("125", ["62.50", "62.50"])]:
            with self.subTest(total=total):
                adjusted = AssociationDepositInstalmentCalculator.adjust_open_payments(
                    Decimal(total), 4, payments, allow_increase=True
                )
                self.assertEqual(
                    [Decimal(value) for value in expected],
                    [p["amount"] for p in adjusted],
                )
                self.assertEqual(["first", "second"], [p["id"] for p in adjusted])
                self.assertEqual(
                    [p.due_date for p in payments], [p["due_date"] for p in adjusted]
                )
                self.assertEqual([1, 2], [p["instalment_number"] for p in adjusted])
        remaining = AssociationDepositInstalmentCalculator.adjust_open_payments(
            Decimal("25"), 4, payments, False
        )
        self.assertEqual(
            [(payments[1].pk, Decimal("25"), payments[1].due_date)],
            [(p["id"], p["amount"], p["due_date"]) for p in remaining],
        )
        self.assertEqual(
            [],
            AssociationDepositInstalmentCalculator.adjust_open_payments(
                Decimal("0"), 4, payments, False
            ),
        )
        with self.assertRaises(ValidationError):
            AssociationDepositInstalmentCalculator.adjust_open_payments(
                Decimal("125"), 4, payments, False
            )
        with self.assertRaises(ValidationError):
            AssociationDepositInstalmentCalculator.adjust_open_payments(
                Decimal("75"), 1, payments, True
            )
        single = AssociationDepositInstalmentCalculator.adjust_open_payments(
            Decimal("75"), 1, payments[:1], False
        )
        self.assertEqual(Decimal("75"), single[0]["amount"])
        self.assertEqual([Decimal("50"), Decimal("50")], [p.amount for p in payments])

    def test_invalid_schedule_fails_before_due_date_allocation(self):
        with patch.object(
            PaymentDueDateCalculator, "get_first_due_date_on_or_after"
        ) as calculate_date:
            for amount, count in [
                ("200", 13),
                ("0.03", 4),
                ("0.001", 1),
                ("0", 1),
                ("-1", 4),
            ]:
                with self.subTest(amount=amount, count=count), self.assertRaises(
                    ValidationError
                ):
                    AssociationDepositInstalmentCalculator.build_payment_schedule(
                        Decimal(amount), count, datetime.date(2026, 11, 6), {}
                    )
            calculate_date.assert_not_called()
