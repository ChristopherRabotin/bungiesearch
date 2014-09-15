from core.models import Article
from bungiesearch.fields import DateField, StringField
from bungiesearch.indices import ModelIndex


class ArticleIndex(ModelIndex):
    effectived_date = DateField(eval_as='obj.created if obj.created and obj.published > obj.created else obj.published')
    meta_data = StringField(eval_as='" ".join([fld for fld in [obj.link, str(obj.tweet_count), obj.raw] if fld])')

    class Meta:
        model = Article
        exclude = ('raw', 'missing_data', 'negative_feedback', 'positive_feedback', 'popularity_index', 'source_hash')
        hotfixes = {'updated': {'null_value': '2013-07-01'},
                    'title': {'boost': 1.75},
                    'description': {'boost': 1.35},
                    'full_text': {'boost': 1.125}}
