# Generated by Django 3.2.10 on 2021-12-12 02:17

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('post_office', '0011_models_help_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailtemplate',
            name='example_context',
            field=jsonfield.fields.JSONField(blank=True, null=True, verbose_name='Context'),
        ),
    ]
