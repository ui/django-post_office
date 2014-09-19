# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'EmailTemplate.last_updated'
        db.alter_column('post_office_emailtemplate', 'last_updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # Changing field 'EmailTemplate.created'
        db.alter_column('post_office_emailtemplate', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # Changing field 'Log.date'
        db.alter_column('post_office_log', 'date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # Changing field 'Email.created'
        db.alter_column('post_office_email', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

    def backwards(self, orm):

        # Changing field 'EmailTemplate.last_updated'
        db.alter_column('post_office_emailtemplate', 'last_updated', self.gf('django.db.models.fields.DateTimeField')())

        # Changing field 'EmailTemplate.created'
        db.alter_column('post_office_emailtemplate', 'created', self.gf('django.db.models.fields.DateTimeField')())

        # Changing field 'Log.date'
        db.alter_column('post_office_log', 'date', self.gf('django.db.models.fields.DateTimeField')())

        # Changing field 'Email.created'
        db.alter_column('post_office_email', 'created', self.gf('django.db.models.fields.DateTimeField')())

    models = {
        'post_office.email': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Email'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'html_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'priority': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'to': ('django.db.models.fields.EmailField', [], {'max_length': '254'})
        },
        'post_office.emailtemplate': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['post_office.Email']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']