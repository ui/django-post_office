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
            field=models.ForeignKey(related_name='translated_templates', default=None, to='post_office.EmailTemplate', null=True, on_delete=models.deletion.SET_NULL),
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(default='', help_text='Render template in alternative language', max_length=12, blank=True, choices=[('af', 'Afrikaans'), ('ar', 'Arabic'), ('ast', 'Asturian'), ('az', 'Azerbaijani'), ('bg', 'Bulgarian'), ('be', 'Belarusian'), ('bn', 'Bengali'), ('br', 'Breton'), ('bs', 'Bosnian'), ('ca', 'Catalan'), ('cs', 'Czech'), ('cy', 'Welsh'), ('da', 'Danish'), ('de', 'German'), ('el', 'Greek'), ('en', 'English'), ('en-au', 'Australian English'), ('en-gb', 'British English'), ('eo', 'Esperanto'), ('es', 'Spanish'), ('es-ar', 'Argentinian Spanish'), ('es-mx', 'Mexican Spanish'), ('es-ni', 'Nicaraguan Spanish'), ('es-ve', 'Venezuelan Spanish'), ('et', 'Estonian'), ('eu', 'Basque'), ('fa', 'Persian'), ('fi', 'Finnish'), ('fr', 'French'), ('fy', 'Frisian'), ('ga', 'Irish'), ('gl', 'Galician'), ('he', 'Hebrew'), ('hi', 'Hindi'), ('hr', 'Croatian'), ('hu', 'Hungarian'), ('ia', 'Interlingua'), ('id', 'Indonesian'), ('io', 'Ido'), ('is', 'Icelandic'), ('it', 'Italian'), ('ja', 'Japanese'), ('ka', 'Georgian'), ('kk', 'Kazakh'), ('km', 'Khmer'), ('kn', 'Kannada'), ('ko', 'Korean'), ('lb', 'Luxembourgish'), ('lt', 'Lithuanian'), ('lv', 'Latvian'), ('mk', 'Macedonian'), ('ml', 'Malayalam'), ('mn', 'Mongolian'), ('mr', 'Marathi'), ('my', 'Burmese'), ('nb', 'Norwegian Bokmal'), ('ne', 'Nepali'), ('nl', 'Dutch'), ('nn', 'Norwegian Nynorsk'), ('os', 'Ossetic'), ('pa', 'Punjabi'), ('pl', 'Polish'), ('pt', 'Portuguese'), ('pt-br', 'Brazilian Portuguese'), ('ro', 'Romanian'), ('ru', 'Russian'), ('sk', 'Slovak'), ('sl', 'Slovenian'), ('sq', 'Albanian'), ('sr', 'Serbian'), ('sr-latn', 'Serbian Latin'), ('sv', 'Swedish'), ('sw', 'Swahili'), ('ta', 'Tamil'), ('te', 'Telugu'), ('th', 'Thai'), ('tr', 'Turkish'), ('tt', 'Tatar'), ('udm', 'Udmurt'), ('uk', 'Ukrainian'), ('ur', 'Urdu'), ('vi', 'Vietnamese'), ('zh-cn', 'Simplified Chinese'), ('zh-hans', 'Simplified Chinese'), ('zh-hant', 'Traditional Chinese'), ('zh-tw', 'Traditional Chinese')]),
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
