from _collections import defaultdict
from elasticsearch_dsl.search import Search
from importlib import import_module
import logging

from bungiesearch.indices import ModelIndex
import bungiesearch.managers
from django.conf import settings
from elasticsearch.client import Elasticsearch
from six import string_types


class Bungiesearch(Search):
    '''
    This object is used to read Django settings and initialize the elasticsearch connection.
    '''
    DEFAULT_TIMEOUT = 5
    BUNGIE = settings.BUNGIESEARCH

    # The following code loads each model index_name module (as defined in the settings) and stores
    # index_name name to model index_name, and index_name name to model. Settings shouldn't change between
    # subsequent calls to Search(), which is why this is static code.

    _cached_es_instances = {}
    # Let's go through the settings in order to map each defined Model/ModelIndex to the elasticsearch index_name.
    _index_to_model_idx, _index_to_model, _model_name_to_model_idx = defaultdict(list), defaultdict(list), {}
    for index_name, idx_module in BUNGIE['INDICES'].iteritems():
        index_module = import_module(idx_module)
        for index_obj in index_module.__dict__.itervalues():
            try:
                if issubclass(index_obj, ModelIndex) and index_obj != ModelIndex:
                    index_instance = index_obj()
                    _index_to_model_idx[index_name].append(index_instance)
                    _index_to_model[index_name].append(index_instance.get_model())
                    _model_name_to_model_idx[index_instance.get_model().__name__] = index_instance
            except TypeError:
                pass # Oops, just attempted to get subclasses of a non-class.

    # Create reverse maps in order to have O(1) access.
    _model_to_index, _model_name_to_index = {}, {}
    for index_name, models in _index_to_model.iteritems():
        for model in models:
            _model_to_index[model] = index_name
            _model_name_to_index[model.__name__] = index_name

    @classmethod
    def _build_key(cls, urls, timeout, **settings):
        # Order the settings by key and then turn it into a string with
        # repr. There are a lot of edge cases here, but the worst that
        # happens is that the key is different and so you get a new
        # Elasticsearch. We'll probably have to tweak this.
        settings = sorted(settings.items(), key=lambda item: item[0])
        settings = repr([(k, v) for k, v in settings])
        # elasticsearch allows URLs to be a string, so we make sure to
        # account for that when converting whatever it is into a tuple.
        if isinstance(urls, string_types):
            urls = (urls,)
        else:
            urls = tuple(urls)
        # Generate a tuple of all the bits and return that as the key
        # because that's hashable.
        key = (urls, timeout, settings)
        return key

    @classmethod
    def get_index(cls, model, via_class=False):
        '''
        Returns the index name (as a string) for the given model as a class or a string.
        :param model: model name or model class if via_class set to True.
        :param via_class: set to True if parameter model is a class.
        :raise KeyError: If the provided model does not have any index associated.
        '''
        try:
            return cls._model_to_index[model] if via_class else cls._model_name_to_index[model]
        except KeyError:
            raise KeyError('Could not find any index defined for {}. Is the model in one of the model index modules of BUNGIESEARCH["INDICES"]?'.format(model))

    @classmethod
    def get_model_index(cls, model):
        '''
        Returns the model index for the given model as a string.
        :param model: model name or model class if via_class set to True.
        :raise KeyError: If the provided model does not have any index associated.
        '''
        try:
            return cls._model_name_to_model_idx[model]
        except KeyError:
            raise KeyError('Could not find any model index defined for model named {}.'.format(model))

    @classmethod
    def get_indices(cls):
        '''
        Returns the list of indices defined in the settings.
        '''
        return cls._index_to_model_idx.keys()

    @classmethod
    def get_models(cls, index, as_class=False):
        '''
        Returns the list of models defined for this index.
        :param index: index name.
        :param as_class: set to True to return the model as a model object instead of as a string.
        '''
        try:
            return cls._index_to_model[index] if as_class else [model.__name__ for model in cls._index_to_model[index]]
        except KeyError:
            raise KeyError('Could not find any index named {}. Is this index defined in BUNGIESEARCH["INDICES"]?'.format(index))

    @classmethod
    def get_model_indices(cls, index):
        '''
        Returns the list of model indices (i.e. ModelIndex objects) defined for this index.
        :param index: index name.
        '''
        try:
            return cls._index_to_model_idx[index]
        except KeyError:
            raise KeyError('Could not find any index named {}. Is this index defined in BUNGIESEARCH["INDICES"]?'.format(index))

    def __init__(self, urls=None, timeout=None, force_new=False, raw_results=False, **kwargs):
        '''
        Creates a new ElasticSearch DSL object. Grabs the ElasticSearch connection from the pool
        if it has already been initialized. Otherwise, creates a new one.

        If no parameters are passed, everything is determined from the Django settings.

        :param urls: A list of URLs, or a single string of URL (without leading `http://`), or None to read from settings.
        :param idx: A list of indices or a single string representing an index_name name. Is optional. Will be merged with `idx_alias`.
        :param idx_alias: A list of index_name aliases or a single string representing an index_name alias, as defined in the settings. Will be merged with `index_name`.
        :param timeout: Timeout used in the connection.
        :param force_new: Set to `True` to force a new elasticsearch connection. Otherwise will aggressively use any connection with the exact same settings.
        :param **kwargs: Additional settings to pass to the low level elasticsearch client and to elasticsearch-sal-py.search.Search.
        '''

        urls = urls or Bungiesearch.BUNGIE['URLS']
        if not timeout:
            timeout = getattr(Bungiesearch.BUNGIE, 'TIMEOUT', Bungiesearch.DEFAULT_TIMEOUT)

        search_keys = ['using', 'index', 'doc_type', 'extra']
        search_settings = dict((k, v) for k, v in kwargs.iteritems() if k in search_keys)
        es_settings = dict((k, v) for k, v in kwargs.iteritems() if k not in search_keys)
        
        # Building a caching key to cache the es_instance for later use (and retrieved a previously cached es_instance).
        cache_key = Bungiesearch._build_key(urls, timeout, **es_settings)
        es_instance = None
        if not force_new:
            if cache_key in Bungiesearch._cached_es_instances:
                es_instance = Bungiesearch._cached_es_instances[cache_key]

        if not es_instance:
            es_instance = Elasticsearch(urls, timeout=timeout, **es_settings)
            Bungiesearch._cached_es_instances[cache_key] = es_instance

        if 'using' not in search_settings:
            search_settings['using'] = es_instance

        super(Bungiesearch, self).__init__(**search_settings)

        # Creating instance attributes.
        self._only = [] # Stores the exact fields to fetch from the database when mapping.
        self.results = [] # Store the mapped and unmapped results.
        self._raw_results_only = raw_results

    def _clone(self):
        '''
        Must clone additional fields to those cloned by elasticsearch-dsl-py.
        '''
        instance = super(Bungiesearch, self)._clone()
        instance._raw_results_only = self._raw_results_only
        return instance

    def get_es_instance(self):
        '''
        Returns the low level elasticsearch instance to perform low level operations.
        '''
        return self._using

    def execute(self, return_results=True):
        '''
        Executes the query and attempts to create model objects from results.
        '''
        if self.results:
            return self.results if return_results else None

        self.raw_results = super(Bungiesearch, self).execute()
        if self._raw_results_only:
            self.results = self.raw_results
        else:
            # Let's iterate over the results and determine the appropriate mapping.
            model_results = defaultdict(list)
            # Initializing the list to the number of returned results. This allows us to restore each item in its position.
            self.results = [None] * len(self.raw_results.hits)
            found_results = {}
            for pos, result in enumerate(self.raw_results):
                model_name = result._meta.doc_type
                if model_name not in self._model_name_to_index or self._model_name_to_index[model_name] != result._meta.index:
                    logging.warn('Returned object of type {} ({}) is not defined in the settings, or is not associated to the same index as in the settings.'.format(model_name, result))
                    self.results[pos] = result
                else:
                    model_results[model_name].append(result.id)
                    found_results['{}.{}'.format(model_name, result.id)] = pos

            # Now that we have model ids per model name, let's fetch everything at once.
            for model_name, ids in model_results.iteritems():
                model_idx = self._model_name_to_model_idx[model_name]
                model_obj = model_idx.get_model()
                items = model_obj.objects.filter(pk__in=ids)
                if self._only:
                    if self._only == '__model':
                        desired_fields = model_idx.fields_to_fetch
                    elif self._only == '__fields':
                        desired_fields = self._fields
                    else:
                        desired_fields = self._only
                    
                    if desired_fields: # Prevents setting the database fetch to __fields but not having specified any field to elasticsearch.
                        items = items.only(*[field for field in model_obj._meta.get_all_field_names() if field in desired_fields])
                # Let's reposition each item in the results.
                for item in items:
                    self.results[found_results['{}.{}'.format(model_name, item.pk)]] = item

        if return_results:
            return self.results

    def only(self, *fields):
        '''
        Restricts the fields to be fetched when mapping. Set to `__model` to fetch all fields define in the ModelIndex.
        '''
        if len(fields) == 1 and fields[0] == '__model':
            self._only = '__model'
        else:
            self._only = fields

    def __iter__(self):
        '''
        Allows iterating on the response.
        '''
        self.execute()
        return iter(self.results)

    def __len__(self):
        '''
        Return elasticsearch-dsl-py count.
        '''
        return self.count()

    def __getitem__(self, key):
        '''
        Overwriting the step in slice. It is used to set the results either as elasticsearch-dsl-py response object, or
        attempt to fetch the Django model instance.
        :warning: Getting an item will execute this search. Any search operation or field setting *must* be done prior to getting an item.
        '''
        if isinstance(key, slice) and key.step is not None:
            self._raw_results_only = key.step
            key.step = None
            single_item = key.start - key.stop == -1
            print key.start, key.stop, key.step
        else:
            single_item = True
        results = super(Bungiesearch, self).__getitem__(key).execute()
        if single_item:
            return results[0]
        return results