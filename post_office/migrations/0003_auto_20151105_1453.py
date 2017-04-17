# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('post_office', '0002_add_i18n_and_backend_alias'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(choices=[('en-us', 'English')], max_length=12, help_text='Render template in alternative language', blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='name',
            field=models.CharField(max_length=255, help_text="e.g: 'welcome_email'"),
        ),
    ]
