from _collections import defaultdict
from elasticsearch_dsl.search import Search
from importlib import import_module
import logging

from bungiesearch.indices import ModelIndex
from bungiesearch.aliases import SearchAlias
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
    _model_to_index, _model_name_to_index, _model_name_to_model_idx = defaultdict(list), defaultdict(list), defaultdict(list)
    _index_to_model, _idx_name_to_mdl_to_mdlidx = defaultdict(list), defaultdict(dict)
    _model_name_to_default_index, _alias_hooks = {}, {}
    _managed_models = []
    __loaded_indices__ = False

    @classmethod
    def __load_settings__(cls):
        if cls.__loaded_indices__:
            return
        cls.__loaded_indices__ = True

        # Loading indices.
        for index_name, module_str in cls.BUNGIE['INDICES'].iteritems():
            index_module = import_module(module_str)
            for index_obj in index_module.__dict__.itervalues():
                try:
                    if issubclass(index_obj, ModelIndex) and index_obj != ModelIndex:
                        index_instance = index_obj()
                        assoc_model = index_instance.get_model()
                        cls._index_to_model[index_name].append(assoc_model)
                        cls._model_name_to_model_idx[assoc_model.__name__].append(index_instance)
                        cls._idx_name_to_mdl_to_mdlidx[index_name][assoc_model.__name__] = index_instance
                        if index_instance.is_default:
                            if assoc_model.__name__ in cls._model_name_to_default_index:
                                raise AttributeError('ModelIndex {} on index {} is marked as default, but {} was already set as default.'.format(index_instance, index_name, cls._model_name_to_default_index[assoc_model.__name__]))
                            cls._model_name_to_default_index[assoc_model.__name__] = index_instance
                except TypeError:
                    pass # Oops, just attempted to get subclasses of a non-class.

        # Create reverse maps in order to have O(1) access.
        for index_name, models in cls._index_to_model.iteritems():
            for model in models:
                cls._model_to_index[model].append(index_name)
                cls._model_name_to_index[model.__name__].append(index_name)

        # Loading aliases.
        for alias_prefix, module_str in cls.BUNGIE.get('ALIASES', {}).iteritems():
            if alias_prefix is None:
                alias_prefix = 'bungie'
            if alias_prefix != '':
                alias_prefix += '_'
            alias_module = import_module(module_str)
            for alias_obj in alias_module.__dict__.itervalues():
                try:
                    if issubclass(alias_obj, SearchAlias) and alias_obj != SearchAlias:
                        alias_instance = alias_obj()
                        cls._alias_hooks[alias_prefix + alias_instance.alias_name] = alias_instance
                except TypeError:
                    pass # Oops, just attempted to get subclasses of a non-class.

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
            raise KeyError('Could not find any index defined for model {}. Is the model in one of the model index modules of BUNGIESEARCH["INDICES"]?'.format(model))

    @classmethod
    def get_model_index(cls, model, default=True):
        '''
        Returns the default model index for the given model, or the list of indices if default is False.
        :param model: model name as a string.
        :raise KeyError: If the provided model does not have any index associated.
        '''
        try:
            if default:
                return cls._model_name_to_default_index[model]
            return cls._model_name_to_model_idx[model]
        except KeyError:
            raise KeyError('Could not find any model index defined for model {}.'.format(model))

    @classmethod
    def get_indices(cls):
        '''
        Returns the list of indices defined in the settings.
        '''
        return cls._idx_name_to_mdl_to_mdlidx.keys()

    @classmethod
    def get_models(cls, index, as_class=False):
        '''
        Returns the list of models defined for this index.
        :param index: index name.
        :param as_class: set to True to return the model as a model object instead of as a string.
        '''
        try:
            return cls._index_to_model[index] if as_class else cls._idx_name_to_mdl_to_mdlidx[index].keys()
        except KeyError:
            raise KeyError('Could not find any index named {}. Is this index defined in BUNGIESEARCH["INDICES"]?'.format(index))

    @classmethod
    def get_model_indices(cls, index):
        '''
        Returns the list of model indices (i.e. ModelIndex objects) defined for this index.
        :param index: index name.
        '''
        try:
            return cls._idx_name_to_mdl_to_mdlidx[index].values()
        except KeyError:
            raise KeyError('Could not find any index named {}. Is this index defined in BUNGIESEARCH["INDICES"]?'.format(index))

    @classmethod
    def map_raw_results(cls, raw_results, instance=None):
        '''
        Maps raw results to database model objects.
        :param raw_results: list raw results as returned from elasticsearch-dsl-py.
        :param instance: Bungiesearch instance if you want to make use of `.only()` or `optmize_queries` as defined in the ModelIndex.
        :return: list of mapped results in the *same* order as returned by elasticsearch.
        '''
        # Let's iterate over the results and determine the appropriate mapping.
        model_results = defaultdict(list)
        # Initializing the list to the number of returned results. This allows us to restore each item in its position.
        if hasattr(raw_results, 'hits'):
            results = [None] * len(raw_results.hits)
        else:
            results = [None] * len(raw_results)
        found_results = {}
        for pos, result in enumerate(raw_results):
            model_name = result.meta.doc_type
            if model_name not in Bungiesearch._model_name_to_index or result.meta.index not in Bungiesearch._model_name_to_index[model_name]:
                logging.warning('Returned object of type {} ({}) is not defined in the settings, or is not associated to the same index as in the settings.'.format(model_name, result))
                results[pos] = result
            else:
                meta = Bungiesearch.get_model_index(model_name).Meta
                id_field = getattr(meta, 'id_field', 'id') 
                result_id = getattr(result, str(id_field))
                model_results['{}.{}'.format(result.meta.index, model_name)].append(result_id)
                found_results['{1.meta.index}.{0}.{2}'.format(model_name, result, result_id)] = (pos, result.meta)

        # Now that we have model ids per model name, let's fetch everything at once.
        for ref_name, ids in model_results.iteritems():
            index_name, model_name = ref_name.split('.')
            model_idx = Bungiesearch._idx_name_to_mdl_to_mdlidx[index_name][model_name]
            model_obj = model_idx.get_model()
            items = model_obj.objects.filter(pk__in=ids)
            if instance:
                if instance._only == '__model' or model_idx.optimize_queries:
                    desired_fields = model_idx.fields_to_fetch
                elif instance._only == '__fields':
                    desired_fields = instance._fields
                else:
                    desired_fields = instance._only

                if desired_fields: # Prevents setting the database fetch to __fields but not having specified any field to elasticsearch.
                    items = items.only(*[field for field in model_obj._meta.get_all_field_names() if field in desired_fields])
            # Let's reposition each item in the results and set the _bungiesearch meta information.
            for item in items:
                pos, meta = found_results['{}.{}.{}'.format(index_name, model_name, item.pk)]
                item._searchmeta = meta
                results[pos] = item

        return results

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

        Bungiesearch.__load_settings__()

        urls = urls or Bungiesearch.BUNGIE['URLS']
        if not timeout:
            timeout = getattr(Bungiesearch.BUNGIE, 'TIMEOUT', Bungiesearch.DEFAULT_TIMEOUT)

        search_keys = ['using', 'index', 'doc_type', 'extra']
        search_settings, es_settings = {}, {}
        for k, v in kwargs.iteritems():
            if k in search_keys:
                search_settings[k] = v
            else:
                es_settings[k] = v

        if not es_settings:
            # If there aren't any provided elasticsearch settings, let's see if it's defined in the settings.
            es_settings = Bungiesearch.BUNGIE.get('ES_SETTINGS', {})

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

    def execute_raw(self):
        self.raw_results = super(Bungiesearch, self).execute()

    def execute(self, return_results=True):
        '''
        Executes the query and attempts to create model objects from results.
        '''
        if self.results:
            return self.results if return_results else None

        self.execute_raw()

        if self._raw_results_only:
            self.results = self.raw_results
        else:
            self.map_results()

        if return_results:
            return self.results

    def map_results(self):
        '''
        Maps raw results and store them.
        '''
        self.results = Bungiesearch.map_raw_results(self.raw_results, self)

    def only(self, *fields):
        '''
        Restricts the fields to be fetched when mapping. Set to `__model` to fetch all fields define in the ModelIndex.
        '''
        s = self._clone()
        if len(fields) == 1 and fields[0] == '__model':
            s._only = '__model'
        else:
            s._only = fields
        return s

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
        if isinstance(key, slice):
            if key.step is not None:
                self._raw_results_only = key.step
                if key.start is not None and key.stop is not None:
                    single_item = key.start - key.stop == -1
                elif key.start is None and key.stop == 1:
                    single_item = True
                else:
                    single_item = False
                key = slice(key.start, key.stop)
            else:
                single_item = False
        else:
            single_item = True
        results = super(Bungiesearch, self).__getitem__(key).execute()
        if single_item:
            try:
                return results[0]
            except IndexError:
                return []
        return results

    def hook_alias(self, alias, model_obj=None):
        '''
        Returns the alias function, if it exists and if it can be applied to this model.
        '''
        try:
            search_alias = self._alias_hooks[alias]
        except KeyError:
            raise AttributeError('Could not find search alias named {}. Is this alias defined in BUNGIESEARCH["ALIASES"]?'.format(alias))
        else:
            if search_alias._applicable_models and \
                ((model_obj and model_obj not in search_alias._applicable_models) or \
                 not any([app_model_obj.__name__ in self._doc_type for app_model_obj in search_alias._applicable_models])):
                    raise ValueError('Search alias {} is not applicable to model/doc_types {}.'.format(alias, model_obj if model_obj else self._doc_type))
            return search_alias.prepare(self, model_obj).alias_for

    def __getattr__(self, alias):
        '''
        Shortcut for search aliases. As explained in the docs (https://docs.python.org/2/reference/datamodel.html#object.__getattr__),
        this is only called as a last resort in case the attribute is not found.
        '''
        return self.hook_alias(alias)
