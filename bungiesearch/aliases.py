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

    def get_model(self):
        if self.model:
            return self.model
        if self.search_instance._doc_type and len(self.search_instance._doc_type) == 1:
            idxes = self.search_instance._model_name_to_model_idx[self.search_instance._doc_type[0]]
            first_mdl = idxes[0].get_model()
            if all(mdlidx.get_model() == first_mdl for mdlidx in idxes[1:]):
                return first_mdl
            raise ValueError('SearchAlias {} is associated to more than one index, and the model is differs between indices!')
        raise ValueError('Instance associated to zero doc types or more than one.')
