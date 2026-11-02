from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0140_link_payments_to_coop_share_transactions"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="coopsharetransaction",
            name="payment",
        ),
    ]
