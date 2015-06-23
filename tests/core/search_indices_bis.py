from bungiesearch.fields import DateField, StringField
from bungiesearch.indices import ModelIndex

from core.models import Article, User, ManangedButEmpty


class ArticleIndex(ModelIndex):
    effective_date = DateField(eval_as='obj.created if obj.created and obj.published > obj.created else obj.published')
    meta_data = StringField(eval_as='" ".join([fld for fld in [obj.link, str(obj.tweet_count), obj.raw] if fld])')
    more_fields = StringField(eval_as='"some value"')

    class Meta:
        model = Article
        updated_field = 'updated'
        exclude = ('raw', 'missing_data', 'negative_feedback', 'positive_feedback', 'popularity_index', 'source_hash')
        hotfixes = {'updated': {'null_value': '2013-07-01'},
                    'title': {'boost': 1.75},
                    'description': {'boost': 1.35},
                    'full_text': {'boost': 1.125}}
        default = False


class UserIndex(ModelIndex):
    effective_date = DateField(eval_as='obj.created if obj.created and obj.published > obj.created else obj.published')
    meta_data = StringField(eval_as='" ".join([fld for fld in [obj.link, str(obj.tweet_count), obj.raw] if fld])')
    more_fields = StringField(eval_as='"some value"')

    class Meta:
        model = User
        id_field = 'user_id'
        updated_field = 'updated'
        exclude = ('raw', 'missing_data', 'negative_feedback', 'positive_feedback', 'popularity_index', 'source_hash')
        hotfixes = {'updated': {'null_value': '2013-07-01'},
                    'title': {'boost': 1.75},
                    'description': {'boost': 1.35},
                    'full_text': {'boost': 1.125}}
        default = False


class EmptyIndex(ModelIndex):
    def matches_indexing_condition(self, item):
        return False

    class Meta:
        model = ManangedButEmpty
        exclude = ('description',)
        optimize_queries = True

