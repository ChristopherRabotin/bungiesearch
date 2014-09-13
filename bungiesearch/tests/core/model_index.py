from django.db import models
import pytest


class Article(models.Model):
    title = models.TextField(db_index=True)
    authors = models.TextField(blank=True)
    description = models.TextField(blank=True)
    link = models.URLField(max_length=510, unique=True, db_index=True)
    published = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(null=True)
    tweet_count = models.IntegerField()
    raw = JSONField()
    source_hash = models.BigIntegerField(null=True)
    missing_data = models.CharField(blank=True, max_length=255)
    positive_feedback = models.PositiveIntegerField(null=True, blank=True, default=0)
    negative_feedback = models.PositiveIntegerField(null=True, blank=True, default=0)
    popularity_index = models.IntegerField(default=0)

class ArticleIndex(ModelIndex):
    effectived_date = DateField(eval_as='obj.created if obj.created and obj.published > obj.created else obj.published')
    meta_data = StringField(eval_as='" ".join([fld for fld in [obj.link, obj.tweet_count, obj.raw] if fld])')

    class Meta:
        model = Article
        exclude = ('raw', 'missing_data', 'negative_feedback', 'positive_feedback', 'popularity_index', 'source_hash')
        hotfixes = {'updated': {'null_value': '2013-07-01'},
                    'title': {'boost': 1.75},
                    'description': {'boost': 1.35},
                    'full_text': {'boost': 1.125}}

import pdb;pdb.set_trace()