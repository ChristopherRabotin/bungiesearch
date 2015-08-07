import logging

from django.db.models import Manager


class BungiesearchManager(Manager):
    '''
    A Django manager for integrated search into models.
    '''
    @property
    def search(self):
        from bungiesearch import Bungiesearch
        return Bungiesearch().index(*Bungiesearch.get_index(self.model, via_class=True)).doc_type(self.model.__name__)

    def search_index(self, index):
        from bungiesearch import Bungiesearch
        if index not in Bungiesearch.get_index(self.model, via_class=True):
            logging.warning('Model/doctype {} is not present on index {}: search may return no results.'.format(self.model.__name__, index))
        return Bungiesearch().index(index).doc_type(self.model.__name__)

    def custom_search(self, index, doc_type):
        '''
        Performs a search on a custom elasticsearch index and mapping. Will not attempt to map result objects.
        '''
        from bungiesearch import Bungiesearch
        return Bungiesearch(raw_results=True).index(index).doc_type(doc_type)

    def contribute_to_class(self, cls, name):
        '''
        Sets up the signal processor. Since self.model is not available
        in the constructor, we perform this operation here.
        '''
        super(BungiesearchManager, self).contribute_to_class(cls, name)

        from . import Bungiesearch
        from .signals import get_signal_processor
        settings = Bungiesearch.BUNGIE
        if 'SIGNALS' in settings:
            self.signal_processor = get_signal_processor()
            self.signal_processor.setup(self.model)

    def __getattr__(self, alias):
        '''
        Shortcut for search aliases. As explained in the docs (https://docs.python.org/2/reference/datamodel.html#object.__getattr__),
        this is only called as a last resort in case the attribute is not found.
        This function will check whether the given model is allowed to use the proposed alias and will raise an attribute error if not.
        '''
        return self.search.hook_alias(alias, self.model)
