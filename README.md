# Purpose
Bungiesearch is a Django wrapper for [elasticsearch-dsl-py](https://github.com/elasticsearch/elasticsearch-dsl-py).

# Features
Bungiesearch is in active development, so this section may be out of date.

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
* Django Manager (coming soon)
	* Seemless integration into models: `MyModel.search.query("match", _all="something to search")`.

# Documentation
## Settings
You must defined `BUNGIESEARCH` in your Django settings in order for bungiesearch to know elasticsearch URL(s) and which index name contains mappings for each ModelIndex.

```
BUNGIESEARCH = {
                'URLS': ['localhost'], # No leading http:// or the elasticsearch client will complain.
                'INDICES': {'main_index': 'myproject.myapp.myindices'} # Must be a module path.
                }
```

## ModelIndex
A `ModelIndex` defines mapping and object extraction for indexing of a given Django model.

Any Django model to be managed by bungiesearch must have a defined ModelIndex subclass. This subclass must contain the `model` attribute, which must be set to the model this represents.
 

## Example
### Django Model
Here's the model we'll use throughout this example.

```
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
```

### ModelIndex

The following ModelIndex will generate a mapping containing all fields from `Article`, minus those defined in `ArticleIndex.Meta.exclude`. When the mapping is generated, each field will the most appropriate [elasticsearch core type](http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/mapping-core-types.html), with default attributes (as defined in bungiesearch/fields.py).

These default attributes can be overwritten with `ArticleIndex.Meta.hotfixes`: each dictionary key must be field defined either in the model or in the ModelIndex subclass (`ArticleIndex` in this case).

```
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
```
