from django.db import models

from tapir.wirgarten.models import ProductType, GrowingPeriod


class NoticePeriod(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    growing_period = models.ForeignKey(GrowingPeriod, on_delete=models.CASCADE)
    duration_in_months = models.IntegerField()
