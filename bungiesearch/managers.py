from django.conf import settings as dj_settings
from django.db.models import Manager

from .logger import logger


class BungiesearchManager(Manager):
    model = None

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
            logger.warning('Model/doctype {} is not present on index {}: search may return no results.'.format(self.model.__name__, index))
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
        # Don't treat "private" attrs as possible aliases. This prevents an infinite recursion bug.
        # Similarly, if Bungiesearch is installed but not enabled, raise the expected error
        if alias[0] == '_' or not dj_settings.BUNGIESEARCH:
            raise AttributeError("'{}' object has no attribute '{}'".format(type(self), alias))

        return self.search.hook_alias(alias, self.model)
