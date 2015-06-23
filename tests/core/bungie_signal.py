from _collections import defaultdict

from bungiesearch import Bungiesearch
from bungiesearch.utils import update_index, delete_index_item
from django.db.models import signals


__items_to_be_indexed__ = defaultdict(list)
class BungieTestSignalProcessor(object):

    def handle_save(self, sender, instance, **kwargs):
        try:
            Bungiesearch.get_index(sender, via_class=True)
        except KeyError:
            return # This model is not managed by Bungiesearch.

        try:
            buffer_size = Bungiesearch.BUNGIE['SIGNALS']['BUFFER_SIZE']
        except KeyError:
            buffer_size = 100

        __items_to_be_indexed__[sender].append(instance)

        if len(__items_to_be_indexed__[sender]) >= buffer_size:
            update_index(__items_to_be_indexed__[sender], sender.__name__, buffer_size)
            # Let's now empty this buffer or we'll end up reindexing every item which was previously buffered.
            __items_to_be_indexed__[sender] = []
        
        raise RuntimeWarning('Handle save called.')

    def handle_delete(self, sender, instance, **kwargs):
        try:
            Bungiesearch.get_index(sender, via_class=True)
        except KeyError:
            return # This model is not managed by Bungiesearch.

        delete_index_item(instance, sender.__name__)
        raise RuntimeWarning('Handle delete called.')

    def setup(self, model):
        signals.post_save.connect(self.handle_save, sender=model)
        signals.pre_delete.connect(self.handle_delete, sender=model)

    def teardown(self, model):
        signals.pre_delete.disconnect(self.handle_delete, sender=model)
        signals.post_save.disconnect(self.handle_save, sender=model)
