# Generated by Django 2.2.11 on 2020-05-10 08:59

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ('post_office', '0008_attachment_headers'),
    ]

    operations = [
        migrations.AddField(
            model_name='email',
            name='number_of_retries',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='email',
            name='status',
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(0, 'sent'), (1, 'failed'), (2, 'queued'), (3, 'requeued')],
                db_index=True,
                null=True,
                verbose_name='Status',
            ),
        ),
        migrations.AddField(
            model_name='email',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Expires timestamp for email'),
        ),
    ]
