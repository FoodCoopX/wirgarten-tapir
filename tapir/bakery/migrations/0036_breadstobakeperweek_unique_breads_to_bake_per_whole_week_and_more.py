from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "bakery",
            "0035_remove_breadsperpickuplocationperweek_bakery_brea_pickup__ba208a_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="breadstobakeperweek",
            constraint=models.UniqueConstraint(
                condition=models.Q(("delivery_day__isnull", True)),
                fields=("year", "delivery_week", "bread"),
                name="unique_breads_to_bake_per_whole_week",
            ),
        ),
        migrations.AddConstraint(
            model_name="stovesession",
            constraint=models.UniqueConstraint(
                condition=models.Q(("delivery_day__isnull", True)),
                fields=("year", "delivery_week", "session_number", "layer_number"),
                name="unique_stove_session_per_whole_week",
            ),
        ),
    ]
