from bungiesearch.managers import BungiesearchManager
from django.db import models


class Article(models.Model):
    title = models.TextField(db_index=True)
    authors = models.TextField(blank=True)
    description = models.TextField(blank=True)
    text_field = models.TextField(null=True)
    link = models.URLField(max_length=510, unique=True, db_index=True)
    published = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(null=True)
    tweet_count = models.IntegerField()
    raw = models.BinaryField(null=True)
    source_hash = models.BigIntegerField(null=True)
    missing_data = models.CharField(blank=True, max_length=255)
    positive_feedback = models.PositiveIntegerField(null=True, blank=True, default=0)
    negative_feedback = models.PositiveIntegerField(null=True, blank=True, default=0)
    popularity_index = models.IntegerField(default=0)

    objects = BungiesearchManager()

    class Meta:
        app_label = 'core'

class User(models.Model):
    name = models.TextField(db_index=True)
    user_id = models.TextField(blank=True, primary_key=True)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(null=True)

    objects = BungiesearchManager()

    class Meta:
        app_label = 'core'


class NoUpdatedField(models.Model):
    title = models.TextField(db_index=True)
    description = models.TextField(blank=True)

    objects = BungiesearchManager()

    class Meta:
        app_label = 'core'

class ManangedButEmpty(models.Model):
    title = models.TextField(db_index=True)
    description = models.TextField(blank=True)

    objects = BungiesearchManager()

    class Meta:
        app_label = 'core'

class Unmanaged(models.Model):
    title = models.TextField(db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        app_label = 'core'
