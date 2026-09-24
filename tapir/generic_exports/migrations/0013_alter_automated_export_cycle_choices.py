from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("generic_exports", "0012_automatedcsvexportresult_created_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="csvexport",
            name="automated_export_cycle",
            field=models.CharField(
                choices=[
                    ("yearly", "Jährlich"),
                    ("monthly", "Monatlich"),
                    ("weekly", "Wöchentlich"),
                    ("daily", "Täglich"),
                    (
                        "after_pickup_location_change_deadline",
                        "Nach letztmöglicher Änderung der Verteilstation",
                    ),
                    ("never", "Nie"),
                ],
                max_length=512,
            ),
        ),
        migrations.AlterField(
            model_name="pdfexport",
            name="automated_export_cycle",
            field=models.CharField(
                choices=[
                    ("yearly", "Jährlich"),
                    ("monthly", "Monatlich"),
                    ("weekly", "Wöchentlich"),
                    ("daily", "Täglich"),
                    (
                        "after_pickup_location_change_deadline",
                        "Nach letztmöglicher Änderung der Verteilstation",
                    ),
                    ("never", "Nie"),
                ],
                max_length=512,
            ),
        ),
    ]
