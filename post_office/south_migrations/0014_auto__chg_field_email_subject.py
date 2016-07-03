# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Email.subject'
        db.alter_column('post_office_email', 'subject', self.gf('django.db.models.fields.CharField')(max_length=989))

    def backwards(self, orm):

        # Changing field 'Email.subject'
        db.alter_column('post_office_email', 'subject', self.gf('django.db.models.fields.CharField')(max_length=255))

    models = {
        'post_office.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'emails': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'attachments'", 'to': "orm['post_office.Email']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'post_office.email': {
            'Meta': {'object_name': 'Email'},
            'backend_alias': ('django.db.models.fields.CharField', [], {'max_length': '64', 'default': "''", 'blank': 'True'}),
            'bcc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'cc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'context': ('jsonfield.fields.JSONField', [], {'blank': 'True', 'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'blank': 'True', 'auto_now_add': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'headers': ('jsonfield.fields.JSONField', [], {'blank': 'True', 'null': 'True'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'blank': 'True', 'auto_now': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'blank': 'True', 'null': 'True'}),
            'scheduled_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'blank': 'True', 'null': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'blank': 'True', 'null': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '989', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'to': "orm['post_office.EmailTemplate']", 'null': 'True'}),
            'to': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'post_office.emailtemplate': {
            'Meta': {'object_name': 'EmailTemplate', 'unique_together': "(('language', 'default_template'),)"},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'default_template': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'translated_templates'", 'to': "orm['post_office.EmailTemplate']", 'null': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '12', 'default': "''", 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'post_office.log': {
            'Meta': {'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['post_office.Email']"}),
            'exception_type': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        }
    }

    complete_apps = ['post_office']