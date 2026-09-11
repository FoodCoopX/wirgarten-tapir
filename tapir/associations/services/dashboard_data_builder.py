import datetime
from typing import Callable

import distinctipy

from tapir.associations.models import AssociationMembershipType
from tapir.utils.shortcuts import get_first_of_next_month


class DashboardDataBuilder:
    @classmethod
    def build_dashboard_data(
        cls,
        start_date: datetime.date,
        end_date: datetime.date,
        count_function: Callable[[datetime.date, AssociationMembershipType], int],
    ):
        membership_types = AssociationMembershipType.objects.order_by("name")
        labels = []
        colors = distinctipy.get_colors(
            len(membership_types) + 1, rng=123456, pastel_factor=0.5
        )
        datasets = {
            membership_type: {
                "name": membership_type.name,
                "color": distinctipy.get_hex(colors[index]),
            }
            for index, membership_type in enumerate(membership_types)
        }

        current_date = start_date.replace(day=1)
        while current_date < end_date:
            labels.append(current_date.strftime("%m.%Y"))
            current_date = get_first_of_next_month(current_date)

        for membership_type in membership_types:
            datasets[membership_type]["values"] = cls._build_dataset_values(
                membership_type=membership_type,
                start_date=start_date,
                end_date=end_date,
                count_function=count_function,
            )

        datasets = list(datasets.values())

        if len(membership_types) > 1:
            totals = [0 for _ in labels]
            for dataset in datasets:
                for index, value in enumerate(dataset["values"]):
                    totals[index] += value

            datasets.append(
                {
                    "name": "Gesamt",
                    "color": distinctipy.get_hex(colors[-1]),
                    "values": totals,
                }
            )

        return labels, datasets

    @classmethod
    def _build_dataset_values(
        cls,
        membership_type: AssociationMembershipType,
        start_date: datetime.date,
        end_date: datetime.date,
        count_function: Callable[[datetime.date, AssociationMembershipType], int],
    ):
        current_date = start_date.replace(day=1)
        values = []
        while current_date < end_date:
            values.append(count_function(current_date, membership_type))
            current_date = get_first_of_next_month(current_date)

        return values
