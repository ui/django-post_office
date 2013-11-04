# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Attachment'
        db.create_table(u'post_office_attachment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attachments', to=orm['post_office.Email'])),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'post_office', ['Attachment'])


    def backwards(self, orm):
        # Deleting model 'Attachment'
        db.delete_table(u'post_office_attachment')


    models = {
        u'post_office.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': u"orm['post_office.Email']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'post_office.email': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Email'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'headers': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'scheduled_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        u'post_office.emailtemplate': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': u"orm['post_office.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']