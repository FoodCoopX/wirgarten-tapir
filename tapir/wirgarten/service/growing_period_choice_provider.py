import datetime

from tapir.wirgarten.models import GrowingPeriod


class GrowingPeriodChoiceProvider:
    @staticmethod
    def get_available_growing_periods(end_date_after: datetime.date):
        return GrowingPeriod.objects.filter(
            end_date__gte=end_date_after, is_available_in_bestell_wizard=True
        ).order_by("start_date")
