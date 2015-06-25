# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post_office', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='email',
            name='backend_alias',
            field=models.CharField(default=b'', max_length=64, blank=True),
        ),
    ]
