import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0153_subscription_price_mode"),
        ("bidding_round", "0004_bid_admin_confirmed_bid_entered_by_admin_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderfeedback",
            name="bidding_round",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="bidding_round.biddinground",
            ),
        ),
    ]
