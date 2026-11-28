from django_drf_filepond.models import TemporaryUpload, StoredUpload
from rest_framework import serializers
from rest_framework.fields import CharField


class TemporaryUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemporaryUpload
        fields = "__all__"

    file_name = CharField(source="file.name")


class StoredUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredUpload
        fields = "__all__"

    file_name = CharField(source="file.name")
