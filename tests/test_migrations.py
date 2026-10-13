import importlib
import unittest

from django.apps import apps
from django.db import DataError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext, override_settings

from post_office.models import Attachment, Email


@unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL legacy JSON migration')
class LegacyJSONMigrationTest(TestCase):
    def test_legacy_columns_follow_search_path_and_preserve_data(self):
        migration = importlib.import_module('post_office.migrations.0015_convert_legacy_json_columns')
        email = Email.objects.create(
            from_email='from@example.com', to=['to@example.com'], headers={'X-Test': 'legacy'}, context={'name': 'user'}
        )
        empty = Email.objects.create(from_email='from@example.com', to=['to@example.com'])
        attachment = Attachment.objects.create(name='test.bin', file='test.bin', headers={'Content-ID': '<legacy>'})
        with connection.schema_editor() as editor:
            editor.execute('SET CONSTRAINTS ALL IMMEDIATE')
            # A fresh database is already jsonb and must remain unchanged.
            migration.convert_text_to_jsonb(apps, editor)
            for model_name, field_name in migration.JSON_FIELDS:
                model = apps.get_model('post_office', model_name)
                table = editor.quote_name(model._meta.db_table)
                column = editor.quote_name(model._meta.get_field(field_name).column)
                editor.execute(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE text USING {column}::text')
            editor.execute('UPDATE post_office_email SET headers = %s, context = %s WHERE id = %s', ['', '', empty.pk])
            # The tables live in public, behind an existing empty schema.
            editor.execute('CREATE SCHEMA post_office_migration_test')
            editor.execute('SET LOCAL search_path = post_office_migration_test, public')
            with CaptureQueriesContext(connection) as queries:
                migration.convert_text_to_jsonb(apps, editor)
            alterations = [query['sql'] for query in queries if query['sql'].startswith('ALTER TABLE')]
            self.assertEqual(len(alterations), 2)
            self.assertEqual(alterations[0].count('ALTER COLUMN'), 2)
            with CaptureQueriesContext(connection) as queries:
                migration.convert_text_to_jsonb(apps, editor)
            self.assertFalse(any(query['sql'].startswith('ALTER TABLE') for query in queries))
            for model_name, field_name in migration.JSON_FIELDS:
                model = apps.get_model('post_office', model_name)
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT pg_typeof(%s)::text FROM %s LIMIT 1'
                        % (editor.quote_name(field_name), editor.quote_name(model._meta.db_table))
                    )
                    self.assertEqual(cursor.fetchone()[0], 'jsonb')
        email.refresh_from_db()
        attachment.refresh_from_db()
        empty.refresh_from_db()
        self.assertEqual(email.headers, {'X-Test': 'legacy'})
        self.assertEqual(email.context, {'name': 'user'})
        self.assertEqual(attachment.headers, {'Content-ID': '<legacy>'})
        self.assertIsNone(empty.headers)
        self.assertIsNone(empty.context)

    def test_invalid_json_rolls_back_all_conversions(self):
        migration = importlib.import_module('post_office.migrations.0015_convert_legacy_json_columns')
        email = Email.objects.create(from_email='from@example.com', to=['to@example.com'], headers={'X-Test': 'legacy'})
        attachment = Attachment.objects.create(name='test.bin', file='test.bin', headers={})
        with connection.schema_editor() as editor:
            editor.execute('SET CONSTRAINTS ALL IMMEDIATE')
            for model_name, field_name in migration.JSON_FIELDS:
                model = apps.get_model('post_office', model_name)
                table = editor.quote_name(model._meta.db_table)
                column = editor.quote_name(field_name)
                editor.execute(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE text USING {column}::text')
            editor.execute(
                'UPDATE post_office_attachment SET headers = %s WHERE id = %s', ['invalid JSON', attachment.pk]
            )
        with self.assertRaisesMessage(DataError, 'post_office_attachment.headers') as caught:
            with connection.schema_editor() as editor:
                migration.convert_text_to_jsonb(apps, editor)
        self.assertIsInstance(caught.exception.__cause__, DataError)
        with connection.cursor() as cursor:
            for model_name, field_name in migration.JSON_FIELDS:
                model = apps.get_model('post_office', model_name)
                cursor.execute(
                    'SELECT pg_typeof(%s)::text FROM %s LIMIT 1'
                    % (connection.ops.quote_name(field_name), connection.ops.quote_name(model._meta.db_table))
                )
                self.assertEqual(cursor.fetchone()[0], 'text')
            cursor.execute('SELECT headers FROM post_office_attachment WHERE id = %s', [attachment.pk])
            self.assertEqual(cursor.fetchone()[0], 'invalid JSON')
            cursor.execute('SELECT headers FROM post_office_email WHERE id = %s', [email.pk])
            self.assertEqual(cursor.fetchone()[0], '{"X-Test": "legacy"}')

    @override_settings(POST_OFFICE={'CONTEXT_FIELD_CLASS': 'django.db.models.TextField'})
    def test_custom_context_storage_is_preserved(self):
        migration = importlib.import_module('post_office.migrations.0015_convert_legacy_json_columns')
        email = Email.objects.create(from_email='from@example.com', to=['to@example.com'], headers={'X-Test': 'legacy'})
        with connection.schema_editor() as editor:
            editor.execute('SET CONSTRAINTS ALL IMMEDIATE')
            editor.execute('ALTER TABLE post_office_email ALTER COLUMN context TYPE text USING context::text')
            editor.execute('ALTER TABLE post_office_email ALTER COLUMN headers TYPE text USING headers::text')
            editor.execute(
                'UPDATE post_office_email SET context = %s WHERE id = %s', ['non-JSON serialized data', email.pk]
            )
            migration.convert_text_to_jsonb(apps, editor)
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT context, pg_typeof(context)::text, pg_typeof(headers)::text FROM post_office_email WHERE id = %s',
                [email.pk],
            )
            self.assertEqual(cursor.fetchone(), ('non-JSON serialized data', 'text', 'jsonb'))
