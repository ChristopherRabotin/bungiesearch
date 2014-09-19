
class SearchAlias(object):
    '''
    Introspects a model to generate an indexable mapping and methods to extract objects.
    Supports custom fields, including Python code, and all elasticsearch field types (apart from binary type).
    
    ModelIndex does efficient querying by only fetching from the database fields which are to be indexed.
    
    How to create an index?

    1. Create a class which inherits from ModelIndex.
    2. Define custom indexed fields as class attributes. Values must be instances AbstractField. Important info in 3b.
    3. Define a `Meta` subclass, which must contain at least `model` as a class attribute.
        a. Optional class attributes: `fields`, `excludes` and `additional_fields`.
        b. If custom indexed field requires model attributes which are not in the difference between `fields` and `excludes`, these must be defined in `additional_fields`.
    '''
    def __init__(self):
        # Introspect the model, adding/removing fields as needed.
        # Adds/Excludes should happen only if the fields are not already
        # defined in `self.fields`.
        self._classname = type(self).__name__
        try:
            _meta = getattr(self, 'Meta')
        except AttributeError:
            raise AttributeError('SearchAlias {} does not contain a Meta class.'.format(self._classname))

        self._applicable_models = getattr(_meta, 'models', None)
        self._alias_name = getattr(_meta, '_alias_name', self._classname.lower())
        self.search_instance = None
        self.model = None

    def _clone(self):
        s = self.__class__()
        s._classname = self._classname
        s._applicable_models = self._applicable_models
        s._alias_name = self._alias_name
        return s

    def prepare(self, search_instance, model_obj):
        s = self._clone()
        s.search_instance = search_instance
        s.model = model_obj
        return s

    def alias_for(self, **kwargs):
        raise NotImplementedError('{} does not provide an implementation for alias_for.'.format(self._classname))
