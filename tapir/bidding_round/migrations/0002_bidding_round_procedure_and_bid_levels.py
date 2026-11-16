from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bidding_round", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="biddinground",
            name="bidding_procedure",
            field=models.CharField(
                choices=[
                    ("simple", "Einfaches Verfahren"),
                    ("bid_range", "Gebotsspanne"),
                ],
                default="simple",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="biddinground",
            name="bid_levels",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="bid",
            name="amount_1",
            field=models.DecimalField(decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="bid",
            name="amount_2",
            field=models.DecimalField(decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="bid",
            name="amount_3",
            field=models.DecimalField(decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddConstraint(
            model_name="biddinground",
            constraint=models.CheckConstraint(
                condition=models.Q(("bid_levels__gte", 1), ("bid_levels__lte", 3)),
                name="bidding_round_bid_levels_between_1_and_3",
            ),
        ),
        migrations.AddConstraint(
            model_name="biddinground",
            constraint=models.CheckConstraint(
                condition=(
                    ~models.Q(("bidding_procedure", "bid_range"))
                    | models.Q(("bid_levels", 2))
                ),
                name="bidding_round_bid_range_requires_two_levels",
            ),
        ),
    ]
