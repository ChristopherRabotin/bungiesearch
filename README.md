# Purpose
Bungiesearch is a Django wrapper for [elasticsearch-dsl-py](https://github.com/elasticsearch/elasticsearch-dsl-py).
It inherits from elasticsearch-dsl-py's `Search` class, so all the fabulous features developed by the elasticsearch-dsl-py team are also available in Bungiesearch.
In addition, just like `Search`, Bungiesearch is a lazy searching class, meaning you can call functions in a row, or do something like the following.

```python
lazy = Article.objects.search.query('match', _all='Description')
print len(lazy) # Prints the number of hits.
for item in lazy[5:10]:
    print item
```

# Features
* Core Python friendly
	* Iteration (`[x for x in lazy_search])
	* Get items (`lazy_search[10]`)
	* Number of hits via `len` (`len(lazy_search)`)

* Index management
	* Creating and deleting an index.
	* Creating, updating and deleting doctypes and their mappings.
	* Update index doctypes.
* Django Model Mapping
	* Very easy mapping (no lies).
	* Automatic model mapping (and supports undefined models by returning a `Result` instance of `elasticsearch-dsl-py`).
	* Efficient database fetching:
		* One fetch for all items of a given model.
		* Fetches only desired fields.
* Django Manager
	* Easy model integration: `MyModel.search.query("match", _all="something to search")`.
	* Search aliases (search shortcuts with as many parameters as wanted): `Tweet.object.bungie_title_search("bungie")` or `Article.object.bungie_title_search("bungie")`, where `bungie_title_search` is uniquely defined.
* Django signals
	* Connect to post save and pre delete signals for the elasticsearch index to correctly reflect the database.

## Feature examples
See section "Full example" at the bottom of page to see the code needed to perform these following examples.
### Query a word (or list thereof) on a managed model.

`Article.objects.search.query('match', _all='Description')`

### Use a search alias.

`Article.objects.bsearch_title_search('title')`

### Iterate over search results

```python
# Will print the Django model instance.
for result in Article.objects.search.query('match', _all='Description'):
    print result
```

### Fetch a single item

```python
`Article.objects.search.query('match', _all='Description')[0]`
```

### Get the number of returned items
```python
`print len(Article.objects.search.query('match', _all='Description'))`
```

### Get a specific number of items with an offset.
This is actually elasticseach-dsl-py functionality, but it's demonstrated here because we can iterate over the results via Bungiesearch.
```python
for item in Article.objects.bsearch_title_search('title').only('pk').fields('_id')[5:7]:
    print item
```

### Deferred model instantiation
```python
# Will print the Django model instance's primary key. Will only fetch the `pk` field from the database.
for result in Article.objects.search.query('match', _all='Description').only('pk'):
    print result.pk
```

### Elasticsearch limited field fetching
```python
# Will print the Django model instance. However, elasticsearch's response only has the `_id` field.
for result in Article.objects.search.query('match', _all='Description').fields('_id'):
    print result
```

### Lazy objects
```python
lazy = Article.objects.bsearch_title_search('title')
print len(lazy)
for item in lazy.filter('range', effective_date={'lte': '2014-09-22'}):
    print item

```
# Documentation

## ModelIndex
A `ModelIndex` defines mapping and object extraction for indexing of a given Django model.

Any Django model to be managed by bungiesearch must have a defined ModelIndex subclass. This subclass must contain a subclass called `Meta` which must have a `model` attribute (sets the model which it represents).

### Class attributes
As detailed below, the doc type mapping will contain fields from the model it related to. However, one may often need to index fields which correspond to either a concatenation of fields of the model or some logical operation.

Bungiesearch makes this very easy: simply define a class attribute as whichever core type, and set to the `eval_as` constructor parameter to a one line Python statement. The object is referenced as `obj` (not `self` nor `object`, just `obj`).

#### Example
This is a partial example as the Meta subclass is not defined, yet mandatory (cf. below).
```python
from bungiesearch.fields import DateField, StringField
from bungiesearch.indices import ModelIndex

class ArticleIndex(ModelIndex):
    effective_date = DateField(eval_as='obj.created if obj.created and obj.published > obj.created else obj.published')
    meta_data = StringField(eval_as='" ".join([fld for fld in [obj.link, str(obj.tweet_count), obj.raw] if fld])')
```

Here, both `effective_date` and `meta_data` will be part of the doc type mapping, but won't be reversed mapped since those fields do not exist in the model.

This can also be used to index foreign keys:
```python
some_field_name = StringField(eval_as='",".join([item for item in obj.some_foreign_relation.values_list("some_field", flat=True)]) if obj.some_foreign_relation else ""')
```

### Meta subclass attributes
**Note**: in the following, any variable defined a being a `list` could also be a `tuple`.
##### model
Required: defines the Django model for which this ModelIndex is applicable.

##### fields
Optional: list of fields (or columns) which must be fetched when serializing the object for elasticsearch, or when reverse mapping the object from elasticsearch back to a Django Model instance.
By default, all fields will be fetched. Setting this *will* restrict which fields can be fetched and may lead to errors when serializing the object. It is recommended to use the `exclude` attribute instead (cf. below).

##### exclude
Optional: list of fields (or columns) which must not be fetched when serializing or deserializing the object.

##### hotfixes
Optional: a dictionary whose keys are index fields and whose values are dictionaries which define [core type attributes](http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/mapping-core-types.html).
By default, there aren't any special settings, apart for String fields, where the [analyzer](http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/analysis-analyzers.html) is set to [`snowball`](http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/analysis-snowball-analyzer.html) (`{'analyzer': 'snowball'}`).

##### additional_fields
Optional: additional fields to fetch for mapping, may it be for `eval_as` fields or when returning the object from the database.

##### id_field
Optional: the model field to use as a unique ID for elasticsearch's metadata `_id`. Defaults to `id` (also called [`pk`](https://docs.djangoproject.com/en/dev/topics/db/models/#automatic-primary-key-fields)).

## Settings
You must defined `BUNGIESEARCH` in your Django settings in order for bungiesearch to know elasticsearch URL(s) and which index name contains mappings for each ModelIndex.

```python
BUNGIESEARCH = {
                'URLS': ['localhost'], # No leading http:// or the elasticsearch client will complain.
                'INDICES': {'main_index': 'myproject.myapp.myindices'} # Must be a module path.
                'ALIASES': ['myproject.myapp.search_aliases'],
                'ALIAS_PREFIX': 'bsearch',
                'SIGNALS': {'BUFFER_SIZE': 1},
                'TIMEOUT': 5
                }
```

### URLS
Required: must be a list of URLs which host elasticsearch instance(s). This is directly sent to elasticsearch-dsl-py, so any issue with multiple URLs should be refered to them.

### INDICES
Required: must be a dictionary where each key is the name of an elasticsearch index and each value is a path to a Python module containing classes which inherit from `bungiesearch.indices.ModelIndex` (cf. below).

### ALIASES
Optional: list of Python modules containing classes which inherit from `bungiesearch.aliases.SearchAlias`.

### ALIAS_PREFIX
Optional: allows you to define the prefix used for search aliases. Defaults to `bungie_`. Set to an empty string to not have any alias at all.

For example, if a search alias is called `title_search`, then it is accessed via `model_obj.objects.bungie_title_search`. The purpose is to not accidently overwrite Django's default manager functions with search aliases.

### SIGNALS
Optional: if it exists, it must be a dictionary (even empty), and will connect to the `post save` and `pre delete` model functions of *all* models using `bungiesearch.managers.BungiesearchManager` as a manager.

If `SIGNALS` is not defined in the settings, *none* of the models managed by BungiesearchManager will automatically update the index when a new item is created or deleted.

#### BUFFER_SIZE
Optional: an integer representing the number of items to buffer before making a bulk index update, defaults to `100`.

**WARNING**: if your application is shut down before the buffer is emptied, then any buffered instance *will not* be indexed on elasticsearch.
Hence, a possibly better implementation is wrapping `post_save_connector` and `pre_delete_connector` from `bungiesearch.signals` in a celery task. It is not implemented as such here in order to not require `celery`.

### TIMEOUT
Optional: Elasticsearch connection timeout in seconds. Defaults to `5`.

# Backend code example
This example is from the `test` folder. It may be partially out-dated, so please refer to the `test` folder for the latest version.

Here's the code which is applicable to the previous examples.
### Django Model

```python
from django.db import models
from bungiesearch.managers import BungiesearchManager

class Article(models.Model):
    title = models.TextField(db_index=True)
    authors = models.TextField(blank=True)
    description = models.TextField(blank=True)
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
```

### ModelIndex

The following ModelIndex will generate a mapping containing all fields from `Article`, minus those defined in `ArticleIndex.Meta.exclude`. When the mapping is generated, each field will the most appropriate [elasticsearch core type](http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/mapping-core-types.html), with default attributes (as defined in bungiesearch.fields).

These default attributes can be overwritten with `ArticleIndex.Meta.hotfixes`: each dictionary key must be field defined either in the model or in the ModelIndex subclass (`ArticleIndex` in this case).

```python
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

```

### SearchAlias
Defines a search alias for one or more models (in this case only for `core.models.Article`).
```python
from core.models import Article
from bungiesearch.aliases import SearchAlias


class SearchTitle(SearchAlias):
    def alias_for(self, title):
        return self.search_instance.query('match', title=title)

    class Meta:
        models = (Article,)
        _alias_name = 'title_search'

class InvalidAlias(SearchAlias):
    def alias_for_does_not_exist(self, title):
        return title

    class Meta:
        models = (Article,)
```

### Django settings
```python
BUNGIESEARCH = {
                'URLS': [os.getenv('ELASTIC_SEARCH_URL')],
                'INDICES': {'bungiesearch_demo': 'core.search_indices'},
                'ALIASES': ['core.search_aliases'],
                'ALIAS_PREFIX': 'bsearch',
                'SIGNALS': {'BUFFER_SIZE': 1}
                }
```

# Testing
All Bungiesearch tests are in `tests/core/test_bungiesearch.py`.
You can run the tests by creating a Python virtual environment, installing the requirements from `tests/requirements.txt`, installing the package (`pip install .`) and running `python tests/manage.py test`.
Make sure to update `tests/settings.py` to use your own elasticsearch URLs, or update the ELASTIC_SEARCH_URL environment variable.