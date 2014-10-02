
class SearchAlias(object):
    '''
    Defines search aliases for specific models. Essentially works like Django Managers but for Bungiesearch.
    These work for both managers and bungiesearch instances. See the docs (and if they aren't clear, open an issue). 
    '''
    def __init__(self):
        # Introspect the model, adding/removing fields as needed.
        # Adds/Excludes should happen only if the fields are not already
        # defined in `self.fields`.
        self._classname = type(self).__name__
        try:
            _meta = getattr(self, 'Meta')
        except AttributeError:
            self._applicable_models = []
            self.alias_name = self._classname.lower()
        else:
            self._applicable_models = getattr(_meta, 'models', None)
            self.alias_name = getattr(_meta, 'alias_name', self._classname.lower())
        self.search_instance = None
        self.model = None

    def _clone(self):
        s = self.__class__()
        s._classname = self._classname
        s._applicable_models = self._applicable_models
        s.alias_name = self.alias_name
        return s

    def prepare(self, search_instance, model_obj):
        s = self._clone()
        s.search_instance = search_instance
        s.model = model_obj
        return s

    def alias_for(self, **kwargs):
        raise NotImplementedError('{} does not provide an implementation for alias_for.'.format(self._classname))
