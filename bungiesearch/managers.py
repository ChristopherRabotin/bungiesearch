from django.db import models

class BungiesearchManager(models.Manager):
    '''
    A Django manager for integrated search into models.
    '''
    @property
    def search(self):
        from bungiesearch import Bungiesearch
        return Bungiesearch().index(Bungiesearch.get_index(self.model, via_class=True)).doc_type(self.model.__name__)
    
    def custom_search(self, index, doc_type):
        '''
        Performs a search on a custom elasticsearch index and mapping. Will not attempt to map result objects.
        '''
        from bungiesearch import Bungiesearch
        return Bungiesearch(raw_results=True).index(index).doc_type(doc_type)
    
    def __init__(self, **kwargs):
        super(BungiesearchManager, self).__init__(**kwargs)
        