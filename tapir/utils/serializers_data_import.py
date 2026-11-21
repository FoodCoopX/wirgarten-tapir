from rest_framework import serializers

from tapir.utils.services.data_import_service import IMPORT_TYPES


class ImportTypeSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    template_url = serializers.URLField()


class SemanticFieldSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    kind = serializers.CharField()
    required = serializers.BooleanField()
    allows_default = serializers.BooleanField()
    required_unless_product_columns = serializers.BooleanField(
        required=False, default=False
    )


class ColumnSerializer(serializers.Serializer):
    index = serializers.IntegerField()
    header = serializers.CharField(allow_blank=True)
    selected_key = serializers.CharField(allow_blank=True)


class CommaSeparatedListField(serializers.ListField):
    # The generated TS client sends arrays in multipart forms as one comma-separated value.
    def to_internal_value(self, data):
        if isinstance(data, str):
            data = [data]
        if isinstance(data, list):
            data = [
                part.strip()
                for item in data
                for part in (item.split(",") if isinstance(item, str) else [item])
                if not isinstance(part, str) or part.strip()
            ]
        return super().to_internal_value(data)


class UploadRequestSerializer(serializers.Serializer):
    file = serializers.FileField()
    import_types = CommaSeparatedListField(
        child=serializers.ChoiceField(choices=list(IMPORT_TYPES)), allow_empty=False
    )
    update_existing = serializers.BooleanField(required=False, default=False)


class DefaultValueSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.CharField(allow_blank=True)


class DataImportPickupLocationSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class DistinctValueSerializer(serializers.Serializer):
    value = serializers.CharField()
    count = serializers.IntegerField()


class DistinctColumnValuesSerializer(serializers.Serializer):
    header = serializers.CharField()
    values = DistinctValueSerializer(many=True)
    capped = serializers.BooleanField()


class PickupLocationMappingSerializer(serializers.Serializer):
    value = serializers.CharField()
    target = serializers.CharField()


class UploadResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    filename = serializers.CharField()
    selected_type_names = serializers.ListField(child=serializers.CharField())
    columns = ColumnSerializer(many=True)
    semantic_fields = SemanticFieldSerializer(many=True)
    preview_rows = serializers.ListField(
        child=serializers.ListField(child=serializers.CharField(allow_blank=True))
    )
    total_rows = serializers.IntegerField()
    suggested_defaults = DefaultValueSerializer(many=True)
    pickup_locations = DataImportPickupLocationSerializer(many=True)
    distinct_values = DistinctColumnValuesSerializer(many=True)


class MappingItemSerializer(serializers.Serializer):
    column_index = serializers.IntegerField(min_value=0)
    key = serializers.CharField(allow_blank=True)


class MappingOptionsSerializer(serializers.Serializer):
    account_owner_from_name = serializers.BooleanField(required=False, default=True)
    sepa_consent_from_contract_start = serializers.BooleanField(
        required=False, default=True
    )


class MappingRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    mapping = MappingItemSerializer(many=True)
    defaults = DefaultValueSerializer(many=True, required=False)
    pickup_location_mapping = PickupLocationMappingSerializer(many=True, required=False)
    options = MappingOptionsSerializer(required=False)
    update_existing = serializers.BooleanField(required=False)


class DataImportCellEditRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    row_index = serializers.IntegerField()
    header = serializers.CharField()
    value = serializers.CharField(allow_blank=True)


class CellSerializer(serializers.Serializer):
    old_value = serializers.CharField(required=False, allow_blank=True)
    value = serializers.CharField(allow_blank=True)
    state = serializers.CharField()
    editable = serializers.BooleanField(required=False)
    edited = serializers.BooleanField(required=False)
    original_value = serializers.CharField(required=False, allow_blank=True)


class ReviewRowSerializer(serializers.Serializer):
    index = serializers.IntegerField()
    line = serializers.IntegerField()
    valid = serializers.BooleanField()
    status = serializers.ChoiceField(
        choices=["new", "changed", "unchanged", "existing", "invalid"]
    )
    editable = serializers.BooleanField()
    cells = CellSerializer(many=True)
    messages = serializers.ListField(child=serializers.CharField())


class ReviewResponseSerializer(serializers.Serializer):
    headers = serializers.ListField(child=serializers.CharField())
    rows = ReviewRowSerializer(many=True)
    valid_count = serializers.IntegerField()
    invalid_count = serializers.IntegerField()
    status_counts = serializers.DictField(
        child=serializers.IntegerField(), required=False
    )
    mapping_errors = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class MappingErrorResponseSerializer(serializers.Serializer):
    mapping_errors = serializers.ListField(child=serializers.CharField())


class ApplyRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    row_indices = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True
    )


class ApplyResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    message = serializers.CharField()


class ActivationResponseSerializer(serializers.Serializer):
    members_without_login = serializers.IntegerField(required=False)
    sent = serializers.IntegerField(required=False)
    errors = serializers.ListField(child=serializers.CharField(), required=False)
