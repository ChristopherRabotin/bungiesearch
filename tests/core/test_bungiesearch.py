from datetime import datetime

from django.test import TestCase
import pytz

from core.models import Article, Unrelated
from core.search_indices import ArticleIndex
from bungiesearch.management.commands import search_index
from time import sleep


class ModelIndexTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        # Let's start by creating the index and mapping.
        # If we create an object before the index, the index 
        # will be created automatically, and we want to test the command.
        search_index.Command().run_from_argv(['tests', 'empty_arg', '--create'])
        
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
                                   'effective_date': {'type': 'date'},
                                   'tweet_count': {'type': 'integer'},
                                   'id': {'type': 'integer'},
                                   '_id': {'type': 'integer'}, # This is the elastic search index.
                                   'published': {'type': 'date'}}
                    }
        self.assertEqual(ArticleIndex().get_mapping(), expected, 'Got an unexpected mapping.')

    def test_fetch_item(self):
        '''
        Test searching and mapping.
        '''
        self.assertEqual(Article.objects.search.query('match', _all='Description')[0], Article.objects.get(title='Title one'), 'Searching for "Description" did not return just the first Article.')
        self.assertEqual(Article.objects.search.query('match', _all='second article')[0], Article.objects.get(title='Title two'), 'Searching for "second article" did not return the second Article.')
    
    def test_iteration(self):
        '''
        Tests iteration on Bungiesearch items.
        '''
        lazy_search = Article.objects.search.query('match', title='title')
        db_items = list(Article.objects.all())
        self.assertTrue(all([result in db_items for result in lazy_search]), 'Searching for title "title" did not return all articles.')
        self.assertTrue(all([result in db_items for result in lazy_search[:]]), 'Searching for title "title" did not return all articles when using empty slice.')
        self.assertEqual(len(lazy_search[:1]), 1, 'Get item with start=None and stop=1 did not return one item.')
        self.assertEqual(len(lazy_search[:2]), 2, 'Get item with start=None and stop=2 did not return two item.')
    
    def test_no_results(self):
        '''
        Test empty results.
        '''
        self.assertEqual(list(Article.objects.search.query('match', _all='nothing')), [], 'Searching for "nothing" did not return an empty list on iterator call.')
        self.assertEqual(Article.objects.search.query('match', _all='nothing')[:10], [], 'Searching for "nothing" did not return an empty list on get item call.')


    def test_custom_search(self):
        '''
        Test searching on custom index and doc_type.
        '''
        search = Article.objects.custom_search(index='bungiesearch_demo', doc_type='Article')
        es_art1 = search.query('match', _all='Description')[0]
        db_art1 = Article.objects.get(title='Title one')
        es_art2 = search.query('match', _all='second article')[0]
        db_art2 = Article.objects.get(title='Title two')
        self.assertTrue(all([es_art1.id == db_art1.id, es_art1.title == db_art1.title, es_art1.description == db_art1.description]), 'Searching for "Description" did not return the first Article.')
        self.assertTrue(all([es_art2.id == db_art2.id, es_art2.title == db_art2.title, es_art2.description == db_art2.description]), 'Searching for "second article" did not return the second Article.')

    def test_get_model(self):
        '''
        Test model mapping.
        '''
        self.assertEqual(ArticleIndex().get_model(), Article, 'Model was not Article.')

    def test_cloning(self):
        '''
        Tests that Bungiesearch remains lazy with specific function which should return clones.
        '''
        inst = Article.objects.search.query('match', _all='Description')
        self.assertIsInstance(inst.only('_id'), inst.__class__, 'Calling `only` does not return a clone of itself.')

    def test_search_alias_exceptions(self):
        '''
        Tests that invalid aliases raise exceptions.
        '''
        self.assertRaises(AttributeError, getattr, Article.objects, 'bsearch_no_such_alias')
        self.assertRaises(NotImplementedError, Article.objects.bsearch_invalidalias)

    def test_search_aliases(self):
        '''
        Tests search alias errors and functionality.
        '''
        title_alias = Article.objects.bsearch_title_search('title')
        db_items = list(Article.objects.all())
        self.assertEqual(title_alias.to_dict(), {'query': {'match': {'title': 'title'}}}, 'Title alias search did not return the expected JSON query.')
        self.assertTrue(all([result in db_items for result in title_alias]), 'Alias searching for title "title" did not return all articles.')
        self.assertTrue(all([result in db_items for result in title_alias[:]]), 'Alias searching for title "title" did not return all articles when using empty slice.')
        self.assertEqual(len(title_alias[:1]), 1, 'Get item on an alias search with start=None and stop=1 did not return one item.')
        self.assertEqual(len(title_alias[:2]), 2, 'Get item on an alias search with start=None and stop=2 did not return two item.')
        self.assertEqual(title_alias.to_dict(), Article.objects.bsearch_title('title').to_dict(), 'Alias applicable to all models does not return the same JSON request body as the model specific one.')

    def test_post_save(self):
        art = {'title': 'Title three',
                 'description': 'Postsave',
                 'link': 'http://example.com/sparrho',
                 'published': pytz.UTC.localize(datetime(year=2020, month=9, day=15)),
                 'updated': pytz.UTC.localize(datetime(year=2014, month=9, day=10)),
                 'tweet_count': 20,
                 'source_hash': 159159159159,
                 'missing_data': '',
                 'positive_feedback': 50,
                 'negative_feedback': 5,
                 }
        obj = Article.objects.create(**art)
        print "Sleeping two seconds for Elasticsearch to index new item."
        sleep(2) # Without this we query elasticsearch before it has analyzed the newly committed changes, so it doesn't return any result.
        find_three = len(Article.objects.search.query('match', title='three'))
        self.assertEqual(find_three, 1, 'Searching for "three" in title did not return exactly one item (got {}).'.format(find_three))
        # Let's now delete this object to test the post delete signal.
        obj.delete()
        print "Sleeping two seconds for Elasticsearch to update its index after deleting an item."
        sleep(2) # Without this we query elasticsearch before it has analyzed the newly committed changes, so it doesn't return any result.

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
    
    def test_manager_interference(self):
        '''
        This tests that saving an object which is not managed by Bungiesearch won't try to update the index for that model.
        '''
        Unrelated.objects.create(title='test', description='blah')