from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("jasmin_integration", "0004_copy_to_jasmin_tenant"),
    ]

    operations = [
        migrations.DeleteModel(name="JasminTenantSettings"),
        migrations.DeleteModel(name="JasminTenant"),
    ]
