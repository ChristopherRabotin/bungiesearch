from bungiesearch.fields import DateField, StringField
from bungiesearch.indices import ModelIndex

from core.models import Article, User, NoUpdatedField


class ArticleIndex(ModelIndex):
    effective_date = DateField(eval_as='obj.created if obj.created and obj.published > obj.created else obj.published')
    meta_data = StringField(eval_as='" ".join([fld for fld in [obj.link, str(obj.tweet_count), obj.raw] if fld])')

    class Meta:
        model = Article
        updated_field = 'updated'
        exclude = ('raw', 'missing_data', 'negative_feedback', 'positive_feedback', 'popularity_index', 'source_hash')
        hotfixes = {'updated': {'null_value': '2013-07-01'},
                    'title': {'boost': 1.75},
                    'description': {'boost': 1.35},
                    'full_text': {'boost': 1.125}}
        default = True


class UserIndex(ModelIndex):
    effective_date = DateField(eval_as='obj.created if obj.created and obj.updated > obj.created else obj.updated')

    class Meta:
        model = User
        id_field = 'user_id'
        updated_field = 'updated'
        default = True


class NoUpdatedFieldIndex(ModelIndex):
    class Meta:
        model = NoUpdatedField
        exclude = ('description', )
        optimize_queries = True
        indexing_query = NoUpdatedField.objects.defer(*exclude).select_related().all()
