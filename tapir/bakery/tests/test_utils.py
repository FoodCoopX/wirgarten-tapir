from django.test import TestCase
from rest_framework import status
from rest_framework.response import Response

from tapir.bakery.utils import (
    is_valid_iso_week,
    parse_week_params,
    str_to_bool,
)


class TestIsValidIsoWeek(TestCase):
    def test_week53_onlyInYearsThatHaveIt(self):
        self.assertTrue(is_valid_iso_week(2026, 53))
        self.assertFalse(is_valid_iso_week(2027, 53))

    def test_outOfRange_isInvalid(self):
        for year, week in ((2026, 0), (2026, 54), (0, 1), (10**20, 1)):
            with self.subTest(year=year, week=week):
                self.assertFalse(is_valid_iso_week(year, week))

    def test_weekWhoseSundayIsBeyondTheLastDate_isInvalid(self):
        # Its Monday is 27.12.9999; its Sunday would be in the year 10000.
        self.assertFalse(is_valid_iso_week(9999, 52))
        self.assertTrue(is_valid_iso_week(9999, 51))


class TestStrToBool(TestCase):
    def test_true_values(self):
        for val in ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]:
            self.assertTrue(str_to_bool(val), f"Expected True for '{val}'")

    def test_false_values(self):
        for val in ["false", "False", "0", "no", "No", "anything", ""]:
            self.assertFalse(str_to_bool(val), f"Expected False for '{val}'")

    def test_none_returns_none(self):
        self.assertIsNone(str_to_bool(None))


class TestParseWeekParams(TestCase):
    def test_validParams_returnsTuple(self):
        params = {"year": "2026", "delivery_week": "11"}
        result = parse_week_params(params)
        self.assertEqual(result, (2026, 11, None))

    def test_validParamsWithDay_returnsTupleWithDay(self):
        params = {"year": "2026", "delivery_week": "11", "delivery_day": "3"}
        result = parse_week_params(params)
        self.assertEqual(result, (2026, 11, 3))

    def test_missingYear_returnsErrorResponse(self):
        params = {"delivery_week": "11"}
        result = parse_week_params(params)
        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missingWeek_returnsErrorResponse(self):
        params = {"year": "2026"}
        result = parse_week_params(params)
        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bothMissing_returnsErrorResponse(self):
        params = {}
        result = parse_week_params(params)
        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonNumericYear_returnsErrorResponse(self):
        params = {"year": "abc", "delivery_week": "11"}
        result = parse_week_params(params)
        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonNumericWeek_returnsErrorResponse(self):
        params = {"year": "2026", "delivery_week": "abc"}
        result = parse_week_params(params)
        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weekNotInTheYear_returnsErrorResponse(self):
        params = {"year": "2027", "delivery_week": "53"}
        result = parse_week_params(params)
        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dayOutOfRange_returnsErrorResponse(self):
        params = {"year": "2026", "delivery_week": "11", "delivery_day": "7"}
        result = parse_week_params(params)
        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonNumericDay_returnsErrorResponse(self):
        params = {"year": "2026", "delivery_week": "11", "delivery_day": "abc"}
        result = parse_week_params(params)
        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dayNone_returnsNoneForDay(self):
        params = {"year": "2026", "delivery_week": "11", "delivery_day": None}
        result = parse_week_params(params)
        self.assertEqual(result, (2026, 11, None))
