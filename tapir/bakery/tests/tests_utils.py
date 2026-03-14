from unittest.mock import MagicMock

from django.db.models.deletion import PROTECT
from django.test import TestCase
from rest_framework import status
from rest_framework.response import Response

from tapir.bakery.utils import (
    _normalize_model_names,
    can_delete_instance,
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


class TestNormalizeModelNames(TestCase):
    def test_strings_returned_as_set(self):
        result = _normalize_model_names(["Foo", "Bar"])
        self.assertEqual(result, {"Foo", "Bar"})

    def test_model_classes_converted_to_names(self):
        mock_class = type("MyModel", (), {})
        result = _normalize_model_names([mock_class])
        self.assertEqual(result, {"MyModel"})

    def test_mixed_strings_and_classes(self):
        mock_class = type("ClassModel", (), {})
        result = _normalize_model_names(["StringModel", mock_class])
        self.assertEqual(result, {"StringModel", "ClassModel"})

    def test_empty_list(self):
        self.assertEqual(_normalize_model_names([]), set())


class TestCanDeleteInstance(TestCase):
    def _make_instance(self, related_objects):
        instance = MagicMock()
        instance._meta.related_objects = related_objects
        return instance

    def _make_related_object(self, model_name, field_name, on_delete, count=0):
        related = MagicMock()
        related.related_model.__name__ = model_name
        related.field.name = field_name
        related.on_delete = on_delete
        accessor_name = f"{model_name.lower()}_set"
        related.get_accessor_name.return_value = accessor_name

        manager = MagicMock()
        manager.exists.return_value = count > 0
        manager.count.return_value = count

        return related, accessor_name, manager

    def test_noRelatedObjects_canDelete(self):
        instance = self._make_instance([])
        can_delete, info = can_delete_instance(instance)
        self.assertTrue(can_delete)
        self.assertEqual(info, {})

    def test_protectedRelationWithObjects_cannotDelete(self):
        related, accessor, manager = self._make_related_object(
            "Child", "parent", PROTECT, count=3
        )
        instance = self._make_instance([related])
        setattr(instance, accessor, manager)

        can_delete, info = can_delete_instance(instance)

        self.assertFalse(can_delete)
        self.assertIn("protected_relations", info)
        self.assertEqual(info["protected_relations"][0]["model"], "Child")
        self.assertEqual(info["protected_relations"][0]["count"], 3)

    def test_nonProtectedRelationWithObjects_cannotDelete(self):
        cascade = MagicMock()
        related, accessor, manager = self._make_related_object(
            "Child", "parent", cascade, count=1
        )
        instance = self._make_instance([related])
        setattr(instance, accessor, manager)

        can_delete, info = can_delete_instance(instance)

        self.assertFalse(can_delete)
        self.assertEqual(info["related_model"], "Child")

    def test_relatedObjectsExistButExcluded_canDelete(self):
        related, accessor, manager = self._make_related_object(
            "Child", "parent", PROTECT, count=5
        )
        instance = self._make_instance([related])
        setattr(instance, accessor, manager)

        can_delete, info = can_delete_instance(instance, exclude_models=["Child"])
        self.assertTrue(can_delete)

    def test_relatedObjectsZeroCount_canDelete(self):
        related, accessor, manager = self._make_related_object(
            "Child", "parent", PROTECT, count=0
        )
        instance = self._make_instance([related])
        setattr(instance, accessor, manager)

        can_delete, info = can_delete_instance(instance)
        self.assertTrue(can_delete)


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
