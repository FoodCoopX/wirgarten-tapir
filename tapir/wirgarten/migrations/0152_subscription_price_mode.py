from django.db import migrations, models


def set_price_mode(apps, schema_editor):
    Subscription = apps.get_model("wirgarten", "Subscription")
    Subscription.objects.filter(price_override__isnull=True).update(
        price_mode="standard"
    )
    Subscription.objects.filter(price_override=0).update(price_mode="free")
    Subscription.objects.filter(price_override__isnull=False).exclude(
        price_override=0
    ).update(price_mode="custom")


class Migration(migrations.Migration):
    dependencies = [
        ("wirgarten", "0151_payment_calculation_explanation_remove_edited"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="price_mode",
            field=models.CharField(
                choices=[
                    ("standard", "Standardbetrag"),
                    ("custom", "Personalisierter Betrag"),
                    ("free", "Beitragsbefreit"),
                    ("bidding_round_bid", "Bietrunde: Gebot"),
                    ("bidding_round_auto_renewed", "Bietrunde: Auto-Verlängert"),
                ],
                default="standard",
                max_length=32,
            ),
        ),
        migrations.RunPython(set_price_mode, migrations.RunPython.noop),
    ]
