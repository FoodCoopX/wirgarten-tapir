from django.test import TestCase
from rest_framework import status
from rest_framework.response import Response

from tapir.bakery.utils import (
    parse_week_params,
    str_to_bool,
)


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

    def test_nonNumericDay_returnsErrorResponse(self):
        params = {"year": "2026", "delivery_week": "11", "delivery_day": "abc"}
        result = parse_week_params(params)
        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dayNone_returnsNoneForDay(self):
        params = {"year": "2026", "delivery_week": "11", "delivery_day": None}
        result = parse_week_params(params)
        self.assertEqual(result, (2026, 11, None))
