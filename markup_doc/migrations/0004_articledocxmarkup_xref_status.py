from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('markup_doc', '0003_articledocxmarkup_marked_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='articledocxmarkup',
            name='xref_status',
            field=models.JSONField(blank=True, null=True, verbose_name='XRef Status'),
        ),
    ]