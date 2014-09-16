from datetime import datetime

from django.test import TestCase
import pytz

from core.models import Article
from core.search_indices import ArticleIndex
from bungiesearch.management.commands import search_index
from time import sleep


class ModelIndexTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        art_1 = {'title': 'Title one',
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
        Article.objects.create(**art_1)

        art_2 = dict((k, v) for k, v in art_1.iteritems())
        art_2['link'] += '/page2'
        art_2['title'] = 'Title two'
        art_2['description'] = 'This is a second article.'
        art_2['published'] = pytz.UTC.localize(datetime(year=2010, month=9, day=15))
        Article.objects.create(**art_2)

        # Let's now create the index.
        search_index.Command().run_from_argv(['tests', 'empty_arg', '--create'])
        search_index.Command().run_from_argv(['tests', 'empty_arg', '--update'])
        print "Sleeping two seconds for Elasticsearch to index."
        sleep(2) # Without this we query elasticsearch before it has analyzed the newly committed changes, so it doesn't return any result.

    @classmethod
    def tearDownClass(cls):
        search_index.Command().run_from_argv(['tests', 'empty_arg', '--delete', '--guilty-as-charged'])

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

    def test_fetch_item(self):
        '''
        Test searching and mapping.
        '''
        self.assertEqual(Article.objects.search.query('match', _all='Description')[0], Article.objects.get(title='Title one'), 'Searching for "Description" did not return just the first Article.')
        self.assertEqual(Article.objects.search.query('match', _all='second article')[0], Article.objects.get(title='Title two'), 'Searching for "Description" did not return just the second Article.')
        db_items = list(Article.objects.all())
        self.assertTrue(all([result in db_items for result in Article.objects.search.query('match', title='title')]), 'Searching for title "title" did not return all articles.')

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
                                  'description': 'This is a second article.',
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
