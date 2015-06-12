from django.db.models import Manager, signals
import logging

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

    def __init__(self, **kwargs):
        super(BungiesearchManager, self).__init__(**kwargs)

        from . import Bungiesearch
        from .signals import post_save_connector, pre_delete_connector
        settings = Bungiesearch.BUNGIE
        if 'SIGNALS' in settings:
            signals.post_save.connect(post_save_connector, sender=self.model)
            signals.pre_delete.connect(pre_delete_connector, sender=self.model)
        Bungiesearch._managed_models.append(self.model)

    def __getattr__(self, alias):
        '''
        Shortcut for search aliases. As explained in the docs (https://docs.python.org/2/reference/datamodel.html#object.__getattr__),
        this is only called as a last resort in case the attribute is not found.
        This function will check whether the given model is allowed to use the proposed alias and will raise an attribute error if not.
        '''
        return self.search.hook_alias(alias, self.model)