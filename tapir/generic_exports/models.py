from django.contrib.postgres.fields import ArrayField
from django.db import models


class CsvExport(models.Model):
    export_segment_id = models.CharField(max_length=512)
    name = models.CharField(max_length=512)
    description = models.TextField()
    separator = models.CharField(max_length=1)
    file_name = models.CharField(max_length=512)
    column_ids = ArrayField(base_field=models.CharField(max_length=512), default=list)
    email_recipients = ArrayField(base_field=models.EmailField(), default=list)
    # TODO : schedule for automated exports
