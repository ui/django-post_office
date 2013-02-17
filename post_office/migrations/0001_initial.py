# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Email'
        db.create_table('post_office_email', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('from_email', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('to', self.gf('django.db.models.fields.EmailField')(max_length=254)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('message', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('html_message', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('status', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True, null=True, blank=True)),
            ('priority', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 17, 0, 0), db_index=True)),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, db_index=True, blank=True)),
        ))
        db.send_create_signal('post_office', ['Email'])

        # Adding model 'Log'
        db.create_table('post_office_log', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.related.ForeignKey')(related_name='logs', to=orm['post_office.Email'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 17, 0, 0), db_index=True)),
            ('status', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True)),
            ('message', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('post_office', ['Log'])

        # Adding model 'EmailTemplate'
        db.create_table('post_office_emailtemplate', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('html_content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 17, 0, 0))),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 17, 0, 0))),
        ))
        db.send_create_signal('post_office', ['EmailTemplate'])


    def backwards(self, orm):
        # Deleting model 'Email'
        db.delete_table('post_office_email')

        # Deleting model 'Log'
        db.delete_table('post_office_log')

        # Deleting model 'EmailTemplate'
        db.delete_table('post_office_emailtemplate')


    models = {
        'post_office.email': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Email'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 17, 0, 0)', 'db_index': 'True'}),
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
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 17, 0, 0)'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 17, 0, 0)'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'post_office.log': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Log'},
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 17, 0, 0)', 'db_index': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['post_office.Email']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['post_office']