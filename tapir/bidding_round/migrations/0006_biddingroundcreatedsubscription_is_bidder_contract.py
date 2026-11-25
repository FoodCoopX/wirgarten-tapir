from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "bidding_round",
            "0004_bid_admin_confirmed_bid_entered_by_admin_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="biddingroundcreatedsubscription",
            name="is_bidder_contract",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="biddingroundcreatedsubscription",
            name="original_quantity",
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="biddingroundcreatedsubscription",
            name="was_reused",
            field=models.BooleanField(default=False),
        ),
    ]
