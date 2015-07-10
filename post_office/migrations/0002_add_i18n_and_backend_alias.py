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
            model_name='email',
            name='backend_alias',
            field=models.CharField(default='', max_length=64, blank=True),
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='default_template',
            field=models.ForeignKey(related_name='translated_templates', default=None, to='post_office.EmailTemplate', null=True),
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(default='', help_text='Render template in alternative language', max_length=12, blank=True, choices=[(b'af', b'Afrikaans'), (b'ar', b'Arabic'), (b'ast', b'Asturian'), (b'az', b'Azerbaijani'), (b'bg', b'Bulgarian'), (b'be', b'Belarusian'), (b'bn', b'Bengali'), (b'br', b'Breton'), (b'bs', b'Bosnian'), (b'ca', b'Catalan'), (b'cs', b'Czech'), (b'cy', b'Welsh'), (b'da', b'Danish'), (b'de', b'German'), (b'el', b'Greek'), (b'en', b'English'), (b'en-au', b'Australian English'), (b'en-gb', b'British English'), (b'eo', b'Esperanto'), (b'es', b'Spanish'), (b'es-ar', b'Argentinian Spanish'), (b'es-mx', b'Mexican Spanish'), (b'es-ni', b'Nicaraguan Spanish'), (b'es-ve', b'Venezuelan Spanish'), (b'et', b'Estonian'), (b'eu', b'Basque'), (b'fa', b'Persian'), (b'fi', b'Finnish'), (b'fr', b'French'), (b'fy', b'Frisian'), (b'ga', b'Irish'), (b'gl', b'Galician'), (b'he', b'Hebrew'), (b'hi', b'Hindi'), (b'hr', b'Croatian'), (b'hu', b'Hungarian'), (b'ia', b'Interlingua'), (b'id', b'Indonesian'), (b'io', b'Ido'), (b'is', b'Icelandic'), (b'it', b'Italian'), (b'ja', b'Japanese'), (b'ka', b'Georgian'), (b'kk', b'Kazakh'), (b'km', b'Khmer'), (b'kn', b'Kannada'), (b'ko', b'Korean'), (b'lb', b'Luxembourgish'), (b'lt', b'Lithuanian'), (b'lv', b'Latvian'), (b'mk', b'Macedonian'), (b'ml', b'Malayalam'), (b'mn', b'Mongolian'), (b'mr', b'Marathi'), (b'my', b'Burmese'), (b'nb', b'Norwegian Bokmal'), (b'ne', b'Nepali'), (b'nl', b'Dutch'), (b'nn', b'Norwegian Nynorsk'), (b'os', b'Ossetic'), (b'pa', b'Punjabi'), (b'pl', b'Polish'), (b'pt', b'Portuguese'), (b'pt-br', b'Brazilian Portuguese'), (b'ro', b'Romanian'), (b'ru', b'Russian'), (b'sk', b'Slovak'), (b'sl', b'Slovenian'), (b'sq', b'Albanian'), (b'sr', b'Serbian'), (b'sr-latn', b'Serbian Latin'), (b'sv', b'Swedish'), (b'sw', b'Swahili'), (b'ta', b'Tamil'), (b'te', b'Telugu'), (b'th', b'Thai'), (b'tr', b'Turkish'), (b'tt', b'Tatar'), (b'udm', b'Udmurt'), (b'uk', b'Ukrainian'), (b'ur', b'Urdu'), (b'vi', b'Vietnamese'), (b'zh-cn', b'Simplified Chinese'), (b'zh-hans', b'Simplified Chinese'), (b'zh-hant', b'Traditional Chinese'), (b'zh-tw', b'Traditional Chinese')]),
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
