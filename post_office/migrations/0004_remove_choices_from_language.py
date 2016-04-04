# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('post_office', '0003_longer_subject'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(default='', help_text='Render template in alternative language', max_length=12, blank=True),
        ),
    ]
