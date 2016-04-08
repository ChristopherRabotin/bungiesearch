from bungiesearch.fields import DateField, NumberField, StringField
from bungiesearch.indices import ModelIndex
from core.models import Article, NoUpdatedField, User

from .analysis import edge_ngram_analyzer


class ArticleIndex(ModelIndex):
    effective_date = DateField(eval_as='obj.created if obj.created and obj.published > obj.created else obj.published')
    meta_data = StringField(eval_as='" ".join([fld for fld in [obj.link, str(obj.tweet_count), obj.raw] if fld])')
    text = StringField(template='article.txt', analyzer=edge_ngram_analyzer)

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
    about = StringField(model_attr='about', analyzer=edge_ngram_analyzer)
    int_about = NumberField(coretype='integer')

    def prepare_int_about(self, obj):
        try:
            int_about = int(obj.about)
        except ValueError:
            int_about = 1

        return int_about

    class Meta:
        model = User
        id_field = 'user_id'
        updated_field = 'updated'
        hotfixes = {'updated': {'null_value': '2013-07-01'},
                    'about': {'boost': 1.35}}
        default = True


class NoUpdatedFieldIndex(ModelIndex):
    class Meta:
        model = NoUpdatedField
        exclude = ('field_description',)
        optimize_queries = True
        indexing_query = NoUpdatedField.objects.defer(*exclude).select_related().all()
