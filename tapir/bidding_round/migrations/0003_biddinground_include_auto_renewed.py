from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bidding_round", "0002_bidding_round_procedure_and_bid_levels"),
    ]

    operations = [
        migrations.AddField(
            model_name="biddinground",
            name="include_auto_renewed",
            field=models.BooleanField(default=True),
        ),
    ]
