from typing import Any, Dict, List, Optional, Set, Tuple

from django.db.models import Model
from django.db.models.deletion import PROTECT


def str_to_bool(value: Optional[str]) -> Optional[bool]:
    """
    Convert string representation of boolean to actual boolean.

    Args:
        value: String value to convert (e.g., 'true', '1', 'yes')

    Returns:
        Boolean value or None if input is None

    Examples:
        >>> str_to_bool('true')
        True
        >>> str_to_bool('1')
        True
        >>> str_to_bool('yes')
        True
        >>> str_to_bool('false')
        False
        >>> str_to_bool(None)
        None
    """
    if value is None:
        return None
    return value.lower() in ["true", "1", "yes"]


def can_delete_instance(
    instance: Model, exclude_models: Optional[List] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if a model instance can be deleted without any related objects.

    Returns False if there are ANY related objects, regardless of on_delete behavior.
    This is a fast check that doesn't hit the database for actual deletion.

    Args:
        instance: The model instance to check
        exclude_models: List of model names (strings) or model classes to exclude from the check

    Returns:
        Tuple of (can_delete: bool, info: dict with details)

    Example:
        >>> can_delete, info = can_delete_instance(my_model_instance)
        >>> if not can_delete:
        ...     print(info['message'])
    """
    exclude_model_names = _normalize_model_names(exclude_models or [])
    protected_relations = []

    for related_object in instance._meta.related_objects:
        model_name = related_object.related_model.__name__

        # Skip if this model is in the exclude list
        if model_name in exclude_model_names:
            continue

        related_manager = _get_related_manager(instance, related_object)
        if related_manager is None:
            continue

        # Use exists() instead of count() - much more efficient
        if related_manager.exists():
            count = related_manager.count()

            # If it's a PROTECT relation, we know it will block deletion
            if related_object.on_delete == PROTECT:
                protected_relations.append(
                    {
                        "model": model_name,
                        "field": related_object.field.name,
                        "count": count,
                    }
                )
            else:
                # For non-PROTECT relations, still block if we're checking for ANY relations
                return False, {
                    "message": "Cannot delete: has related objects",
                    "related_model": model_name,
                    "count": count,
                    "on_delete": str(related_object.on_delete),
                }

    # If we found protected relations, return them
    if protected_relations:
        return False, {
            "message": "Cannot delete: has protected relations",
            "protected_relations": protected_relations,
        }

    # If no related objects found, we can delete
    return True, {}


def _normalize_model_names(models: List) -> Set[str]:
    """
    Convert a list of model references to a set of model name strings.

    Args:
        models: List of model names (strings) or model classes

    Returns:
        Set of model name strings
    """
    model_names = set()
    for model in models:
        if isinstance(model, str):
            model_names.add(model)
        else:
            model_names.add(model.__name__)
    return model_names


def _get_related_manager(instance: Model, related_object: Any) -> Optional[Any]:
    """
    Safely get the related manager for a related object.

    Args:
        instance: The model instance
        related_object: The related object descriptor

    Returns:
        Related manager or None if not accessible
    """
    try:
        return getattr(instance, related_object.get_accessor_name())
    except AttributeError:
        return None


def parse_week_params(query_params) -> tuple[int, int, int | None]:
    """Parse year, delivery_week, and optional delivery_day from query params.
    Raises ValueError if required params are missing or invalid."""
    year = query_params.get("year")
    delivery_week = query_params.get("delivery_week")
    delivery_day_param = query_params.get("delivery_day")

    if not year or not delivery_week:
        raise ValueError("Missing required parameters: year, delivery_week")

    return (
        int(year),
        int(delivery_week),
        int(delivery_day_param) if delivery_day_param else None,
    )
