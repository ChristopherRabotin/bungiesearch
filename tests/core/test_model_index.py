from datetime import datetime

from bungiesearch.fields import DateField, StringField
from bungiesearch.indices import ModelIndex
from django.test import TestCase
import pytz

from core.models import Article


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


class ModelIndexTestCase(TestCase):
    def setUp(self):
        self.art_1 = {'title': 'Title one',
                     'description': 'Description of article 1.',
                     'link': 'http://example.com/article_1',
                     'published': pytz.UTC.localize(datetime(year=2020, month=9, day=15)),
                     'updated': pytz.UTC.localize(datetime(year=2014, month=9, day=10)),
                     'tweet_count': 20,
                     'source_hash': 159159159159,
                     'missing_data': '',
                     'positive_feedback': 50,
                     'negative_feedback': 5,
                     }
        Article.objects.create(**self.art_1)

        self.art_2 = dict((k, v) for k, v in self.art_1.iteritems())
        self.art_2['link'] += '/page2'
        self.art_2['title'] = 'Title two'
        self.art_2['published'] = pytz.UTC.localize(datetime(year=2010, month=9, day=15))
        Article.objects.create(**self.art_2)

    def test_model_index_generation(self):
        '''
        Check that the mapping is the expected one.
        '''
        expected = {'properties': {'updated': {'type': 'date', 'null_value': '2013-07-01'},
                                   'description': {'type': 'string', 'boost': 1.35, 'analyzer': 'snowball'},
                                   'created': {'type': 'date'},
                                   'title': {'type': 'string', 'boost': 1.75, 'analyzer': 'snowball'},
                                   'authors': {'type': 'string', 'analyzer': 'snowball'},
                                   'meta_data': {'type': 'string', 'analyzer': 'snowball'},
                                   'link': {'type': 'string', 'analyzer': 'snowball'},
                                   'effectived_date': {'type': 'date'},
                                   'tweet_count': {'type': 'integer'},
                                   'id': {'type': 'integer'},
                                   'published': {'type': 'date'}}
                    }
        self.assertEqual(ArticleIndex().get_mapping(), expected, 'Got an unexpected mapping.')

    def test_get_model(self):
        '''
        Check model mapping.
        '''
        self.assertEqual(ArticleIndex().get_model(), Article, 'Model was not Article.')

    def test_serialize_object(self):
        expected = {'Title one': {'updated': pytz.UTC.localize(datetime.strptime('2014-09-10', '%Y-%m-%d')),
                                  'published': pytz.UTC.localize(datetime.strptime('2020-09-15', '%Y-%m-%d')),
                                  'description': 'Description of article 1.',
                                  'title': 'Title one',
                                  'authors': '',
                                  'meta_data': 'http://example.com/article_1 20',
                                  'link': 'http://example.com/article_1',
                                  'tweet_count': 20,
                                  'id': 1,
                                  },
                    'Title two': {'updated': pytz.UTC.localize(datetime.strptime('2014-09-10', '%Y-%m-%d')),
                                  'published': pytz.UTC.localize(datetime.strptime('2010-09-15', '%Y-%m-%d')),
                                  'description': 'Description of article 1.',
                                  'title': 'Title two',
                                  'authors': '',
                                  'meta_data': 'http://example.com/article_1/page2 20',
                                  'link': 'http://example.com/article_1/page2',
                                  'tweet_count': 20,
                                  'id': 2,
                                  }
                    }

        for obj in Article.objects.all():
            for key, value in ArticleIndex().serialize_object(obj).iteritems():
                if key in expected[obj.title]:
                    self.assertEqual(expected[obj.title][key], value, 'Got {} expected {} for key {} in {}.'.format(value, expected[obj.title][key], key, obj.title))
