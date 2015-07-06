# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import post_office.validators
import post_office.fields


class Migration(migrations.Migration):

    dependencies = [
        ('post_office', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='emailtemplate',
            options={'verbose_name': 'Email Template', 'verbose_name_plural': 'Email Templates'},
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='default_template',
            field=models.ForeignKey(related_name='translated_templates', default=None, to='post_office.EmailTemplate', null=True),
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(default='', help_text='Render template in alternative language', max_length=12, blank=True, choices=[(b'en-us', b'English')]),
        ),
        migrations.AlterField(
            model_name='email',
            name='bcc',
            field=post_office.fields.CommaSeparatedEmailField(verbose_name='Bcc', blank=True),
        ),
        migrations.AlterField(
            model_name='email',
            name='cc',
            field=post_office.fields.CommaSeparatedEmailField(verbose_name='Cc', blank=True),
        ),
        migrations.AlterField(
            model_name='email',
            name='from_email',
            field=models.CharField(max_length=254, verbose_name='Email From', validators=[post_office.validators.validate_email_with_name]),
        ),
        migrations.AlterField(
            model_name='email',
            name='html_message',
            field=models.TextField(verbose_name='HTML Message', blank=True),
        ),
        migrations.AlterField(
            model_name='email',
            name='message',
            field=models.TextField(verbose_name='Message', blank=True),
        ),
        migrations.AlterField(
            model_name='email',
            name='subject',
            field=models.CharField(max_length=255, verbose_name='Subject', blank=True),
        ),
        migrations.AlterField(
            model_name='email',
            name='to',
            field=post_office.fields.CommaSeparatedEmailField(verbose_name='Email To', blank=True),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='content',
            field=models.TextField(blank=True, verbose_name='Content', validators=[post_office.validators.validate_template_syntax]),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='html_content',
            field=models.TextField(blank=True, verbose_name='HTML content', validators=[post_office.validators.validate_template_syntax]),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='subject',
            field=models.CharField(blank=True, max_length=255, verbose_name='Subject', validators=[post_office.validators.validate_template_syntax]),
        ),
        migrations.AlterUniqueTogether(
            name='emailtemplate',
            unique_together=set([('language', 'default_template')]),
        ),
    ]
