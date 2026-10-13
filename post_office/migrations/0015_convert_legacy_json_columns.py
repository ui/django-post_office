from django.conf import settings
from django.db import DataError, migrations, models
from django.utils.module_loading import import_string

# Before 3.7.0 these fields used the jsonfield package, stored as text. The old
# migrations were then rewritten to models.JSONField instead of adding one, so
# PostgreSQL databases created before 3.7.0 still have text columns and JSON
# lookups on them fail (#514). Convert them; anything else is left unchanged.
JSON_FIELDS = [('Email', 'headers'), ('Email', 'context'), ('Attachment', 'headers')]


def convert_text_to_jsonb(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return
    # Custom serializers can intentionally store non-JSON data in text columns.
    context_class = import_string(
        getattr(settings, 'POST_OFFICE', {}).get('CONTEXT_FIELD_CLASS', 'django.db.models.JSONField')
    )
    alterations = {}
    for model_name, field_name in JSON_FIELDS:
        if (model_name, field_name) == ('Email', 'context') and not issubclass(context_class, models.JSONField):
            continue
        model = apps.get_model('post_office', model_name)
        table = model._meta.db_table
        column = model._meta.get_field(field_name).column
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_catalog.format_type(atttypid, atttypmod) '
                'FROM pg_catalog.pg_attribute '
                'WHERE attrelid = pg_catalog.to_regclass(%s) AND attname = %s AND NOT attisdropped',
                [schema_editor.quote_name(table), column],
            )
            row = cursor.fetchone()
        if row and row[0] == 'text':
            quoted = schema_editor.quote_name(column)
            alterations.setdefault(table, []).append(
                (column, f"ALTER COLUMN {quoted} TYPE jsonb USING NULLIF({quoted}, '')::jsonb")
            )
    # Convert a table's legacy columns together so PostgreSQL rewrites it only once.
    for table, columns in alterations.items():
        try:
            schema_editor.execute(
                f'ALTER TABLE {schema_editor.quote_name(table)} ' + ', '.join(sql for _, sql in columns)
            )
        except DataError as exc:
            names = ', '.join(f'{table}.{column}' for column, _ in columns)
            raise DataError(
                f'Unable to convert legacy JSON columns {names} to jsonb. '
                f'Repair invalid JSON values before retrying the migration. Original error: {exc}'
            ) from exc


class Migration(migrations.Migration):
    dependencies = [
        ('post_office', '0014_alter_email_recipient_delivery_status_and_more'),
    ]

    operations = [
        migrations.RunPython(convert_text_to_jsonb, migrations.RunPython.noop),
    ]
