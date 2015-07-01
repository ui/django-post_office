# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import post_office.fields
import post_office.validators


class Migration(migrations.Migration):

    dependencies = [
        ('post_office', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TranslatedEmailTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subject', models.CharField(blank=True, max_length=255, verbose_name='Subject', validators=[post_office.validators.validate_template_syntax])),
                ('content', models.TextField(blank=True, verbose_name='Content', validators=[post_office.validators.validate_template_syntax])),
                ('html_content', models.TextField(blank=True, verbose_name='HTML content', validators=[post_office.validators.validate_template_syntax])),
                ('language', models.CharField(default=b'en-us', help_text='Render template in alternative language', max_length=12, choices=[(b'en-us', b'English')])),
                ('default_template', models.ForeignKey(related_name='translated_template', to='post_office.EmailTemplate')),
            ],
            options={
                'verbose_name': 'Translated Email',
                'verbose_name_plural': 'Translated Emails',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='translatedemailtemplate',
            unique_together=set([('language', 'default_template')]),
        ),
        migrations.AlterModelOptions(
            name='emailtemplate',
            options={'verbose_name': 'Email Template', 'verbose_name_plural': 'Email Templates'},
        ),
        migrations.AddField(
            model_name='email',
            name='language',
            field=models.CharField(help_text='Language in which the given template shall be rendered.', max_length=12, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='email',
            name='bcc',
            field=post_office.fields.CommaSeparatedEmailField(verbose_name='Bcc', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='email',
            name='cc',
            field=post_office.fields.CommaSeparatedEmailField(verbose_name='Cc', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='email',
            name='from_email',
            field=models.CharField(max_length=254, verbose_name='Email From', validators=[post_office.validators.validate_email_with_name]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='email',
            name='html_message',
            field=models.TextField(verbose_name='HTML Message', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='email',
            name='message',
            field=models.TextField(verbose_name='Message', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='email',
            name='subject',
            field=models.CharField(max_length=255, verbose_name='Subject', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='email',
            name='to',
            field=post_office.fields.CommaSeparatedEmailField(verbose_name='Email To', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='content',
            field=models.TextField(blank=True, verbose_name='Content', validators=[post_office.validators.validate_template_syntax]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='html_content',
            field=models.TextField(blank=True, verbose_name='HTML content', validators=[post_office.validators.validate_template_syntax]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='subject',
            field=models.CharField(blank=True, max_length=255, verbose_name='Subject', validators=[post_office.validators.validate_template_syntax]),
            preserve_default=True,
        ),
    ]
