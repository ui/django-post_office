# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'EmailTemplate.language'
        db.add_column(u'post_office_emailtemplate', 'language',
                      self.gf('django.db.models.fields.CharField')(default=u'', max_length=12, blank=True),
                      keep_default=False)

        # Adding field 'EmailTemplate.default_template'
        db.add_column(u'post_office_emailtemplate', 'default_template',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name=u'translated_templates', null=True, to=orm['post_office.EmailTemplate']),
                      keep_default=False)

        # Adding unique constraint on 'EmailTemplate', fields ['language', 'default_template']
        db.create_unique(u'post_office_emailtemplate', ['language', 'default_template_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'EmailTemplate', fields ['language', 'default_template']
        db.delete_unique(u'post_office_emailtemplate', ['language', 'default_template_id'])

        # Deleting field 'EmailTemplate.language'
        db.delete_column(u'post_office_emailtemplate', 'language')

        # Deleting field 'EmailTemplate.default_template'
        db.delete_column(u'post_office_emailtemplate', 'default_template_id')


    models = {
        u'post_office.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'emails': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "u'attachments'", 'symmetrical': 'False', 'to': u"orm['post_office.Email']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'post_office.email': {
            'Meta': {'object_name': 'Email'},
            'bcc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'cc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'context': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'headers': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'scheduled_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['post_office.EmailTemplate']", 'null': 'True', 'blank': 'True'}),
            'to': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'post_office.emailtemplate': {
            'Meta': {'unique_together': "((u'language', u'default_template'),)", 'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_template': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "u'translated_templates'", 'null': 'True', 'to': u"orm['post_office.EmailTemplate']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '12', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'post_office.log': {
            'Meta': {'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'logs'", 'to': u"orm['post_office.Email']"}),
            'exception_type': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        }
    }

    complete_apps = ['post_office']