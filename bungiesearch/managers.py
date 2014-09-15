from django.db import models

class BungiesearchManager(models.Manager):
    '''
    A Django manager for integrated search into models.
    '''
    @property
    def search(self):
        from bungiesearch import Bungiesearch
        return Bungiesearch().index(Bungiesearch.get_index(self.model, via_class=True))